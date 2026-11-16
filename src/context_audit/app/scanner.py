"""Interactive scanner services; separate from frozen experiment execution."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from context_audit.app.compilers import compatible_compilers
from context_audit.app.config import ApplicationError, ANALYSIS_TIMEOUT
from context_audit.app.services import check_source, analyze_upload
from context_audit.app.slither_runner import process_environment
from context_audit.verdict_consistency import VERSION


@dataclass(frozen=True)
class ScannerSettings:
    model: str
    max_rounds: int = 3
    max_candidates: int = 3
    max_batches: int = 6
    max_verification_tokens: int = 60000
    provider: str = "openai"
    max_fragments: int = 20
    max_source_tokens: int = 16000
    max_input_tokens: int = 24000
    max_output_tokens: int = 2000

    @classmethod
    def for_profile(cls, model, profile, *, provider="openai"):
        from context_audit.verification_profiles import limits_for
        limits = limits_for(profile)
        return cls(model=model, provider=provider, max_rounds=limits.max_rounds,
            max_candidates=limits.max_candidates, max_fragments=limits.max_fragments,
            max_source_tokens=limits.max_source_tokens, max_input_tokens=limits.max_input_tokens,
            max_output_tokens=limits.max_output_tokens, max_verification_tokens=limits.max_total_tokens)

    def observed_token_cap(self, discovery_batches):
        from context_audit.codex_transport import INPUT_OVERHEAD_RESERVE
        # Discovery and verification share one observed transport ceiling.
        # Verification has its own existing budget; account for discovery too.
        return self.max_verification_tokens + discovery_batches * (INPUT_OVERHEAD_RESERVE + self.max_input_tokens + 8000)

    def validate(self, *, api_key=None):
        if not self.model.strip():
            raise ApplicationError('Enter a model ID before starting the LLM scan.')
        if self.provider not in ('openai','codex'):
            raise ApplicationError('Choose the API or Codex subscription backend.')
        if self.provider == 'openai' and not (api_key or os.environ.get('OPENAI_API_KEY')):
            raise ApplicationError('OPENAI_API_KEY is missing. Local scanning and preparation still work without a key.')
        for name, low, high in (('max_rounds', 1, 6), ('max_candidates', 1, 10),
                                ('max_batches', 1, 12), ('max_verification_tokens', 4000, 1000000),
                                ('max_fragments', 0, 64), ('max_source_tokens', 1, 64000),
                                ('max_input_tokens', 1, 128000), ('max_output_tokens', 1, 16000)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ApplicationError(f'Invalid {name.replace("_", " ")}. Choose a value between {low} and {high}.')


def _worker(upload, action, *, settings=None, preparation=None, api_key=None):
    check_source(upload)
    versions = compatible_compilers(upload.source)
    if not versions:
        raise ApplicationError('No compatible Solidity compiler is installed for this source.')
    request = {'action': action, 'source': str(upload.source_path), 'source_sha256': upload.digest}
    if settings:
        request['settings'] = asdict(settings)
        request['prepared_identity'] = preparation['source_identity']
    # Each invocation owns a fresh directory; no research paths or implicit resume.
    request['output'] = str(upload.source_path.parent / ('scan-' + uuid4().hex))
    environment = process_environment(versions[0], settings.model if settings else None)
    if api_key:
        environment['OPENAI_API_KEY'] = api_key
    environment.setdefault('VIRTUAL_ENV', str(Path(sys.executable).parent.parent))
    call_seconds = 190 if settings and settings.provider == 'codex' else 65
    ceiling = ANALYSIS_TIMEOUT + call_seconds * (settings.max_batches + settings.max_candidates * settings.max_rounds) if settings else ANALYSIS_TIMEOUT
    try:
        result = subprocess.run([sys.executable, '-m', 'context_audit.app.scanner_worker'],
            input=json.dumps(request), env=environment, cwd=upload.source_path.parent,
            capture_output=True, text=True, timeout=ceiling)
        response = json.loads(result.stdout)
    except subprocess.TimeoutExpired as exc:
        raise ApplicationError('The scan timed out. No retry was made. An interrupted LLM scan may have used tokens.') from exc
    except (OSError, ValueError) as exc:
        raise ApplicationError('The scanner could not return a result. No automatic retry was made.') from exc
    if result.returncode or response.get('error'):
        raise ApplicationError(response.get('error', 'The scan worker failed.'))
    return response


def prepare_upload(upload):
    """Compile/index locally in an isolated worker; never create a model client."""
    return _worker(upload, 'prepare')


def scan_direct(upload, preparation, settings, *, api_key=None):
    settings.validate(api_key=api_key)
    check_source(upload)
    if preparation.get('source_sha256') != upload.digest:
        raise ApplicationError('The source changed. Prepare the current contract before scanning.')
    if preparation['batch_count'] > settings.max_batches:
        raise ApplicationError('This contract exceeds the discovery request limit. Increase the limit or scan a smaller self-contained source.')
    if not preparation['function_count']:
        raise ApplicationError('The source has no analyzable functions.')
    return _worker(upload, 'scan', settings=settings, preparation=preparation, api_key=api_key)


def _base(upload, kind, compiler, model=None):
    return {'schema_version': 1, 'analysis_kind': kind, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': upload.digest, 'source': upload.source, 'compiler': compiler, 'model': model,
        'consistency_version': VERSION if model else None,
        'limitations': ['Findings require review. No findings does not prove that the contract is secure.',
                        'Static warnings and LLM assessments are different forms of evidence.',
                        'This scanner does not execute exploits.']}


def scan_static(upload, compiler):
    analysis = analyze_upload(upload, compiler)
    report = _base(upload, 'local_static', compiler)
    report.update(status='completed', findings=[{
        'id': f.id, 'function': f.function_signature or f.contract or 'File-level warning',
        'type': f.detector, 'severity': f.impact.lower(), 'status': 'static_warning', 'verdict': None,
        'explanation': f.description, 'lines': list(f.lines), 'evidence': [], 'errors': [],
    } for f in analysis.findings], coverage=[],
        counts={'static_warnings': len(analysis.findings)},
        usage={'api_calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'unknown_usage_calls': 0})
    return report


def direct_report(upload, response, settings):
    raw = response['report']
    report = _base(upload, 'direct_llm_v2', response['compiler'], settings.model)
    counts = raw['coverage_counts']
    partial = bool(counts['processing_failures'] or counts['skipped_candidates'] or counts['pending_candidates']
                   or counts['unevaluable'] or counts['pending'] or raw['discovery_errors'])
    findings = []
    for issue in raw['issues']:
        r = issue['result']
        c = r['candidate']
        evidence = {}
        for round_info in r['rounds']:
            request = json.loads(round_info['messages'][1]['content'])
            evidence.update({f['id']: f for f in [request['target'], *request['provided_context']]})
        findings.append({'id': issue['issue_id'], 'function': c['primary_function'],
            'contract': c['contract'], 'type': c['suspected_type'], 'severity': r['severity'],
            'status': r['status'], 'verdict': r['verdict'], 'explanation': r['explanation'],
            'hypothesis': c['reason'], 'flow': r.get('execution_flow', []),
            'incomplete_evidence': r['incomplete_evidence'],
            'lines': sorted({line for loc in r['source_locations'].values() for line in loc.get('lines', [])}),
            'evidence': [evidence[fid] for fid in r['evidence_ids'] if fid in evidence],
            'rounds': r['round_count'], 'retrieved_fragments': r['retrieved_fragments'],
            'errors': [e['code'] for e in r['errors']],
            'consistency': r.get('consistency_validation'),
            'original_model_verdict': r.get('original_model_verdict')})
    report.update(provider=settings.provider, status='partial' if partial else 'completed', findings=findings, counts=counts,
        coverage=response['coverage'], usage={**raw['efficiency']['total'],
            'unknown_usage_calls': raw['efficiency']['unknown_usage_calls']},
        discovery_errors=raw['discovery_errors'], efficiency=raw['efficiency'], settings=asdict(settings))
    if settings.provider == 'codex':
        report['usage']['model_turns'] = report['usage']['api_calls']
        report['usage']['api_calls'] = 0
        report['subscription_transport'] = response.get('subscription_transport')
        report['billing_note'] = 'Uses existing ChatGPT/Codex allowance. No API-key calls or paid fallback. Tokens include Codex context overhead.'
    return report


def report_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False)


def report_html(report):
    """Self-contained, escaped report for a teacher or reviewer; no remote assets."""
    esc = lambda text: html.escape(str(text))
    cards = []
    for f in report['findings']:
        state = f['verdict'] or f['status']
        cards.append('<article><h2>' + esc(f['function']) + '</h2><p class="tag">' + esc(state.replace('_', ' '))
            + ' · ' + esc(f['severity'] or 'unspecified severity') + '</p><h3>' + esc(f['type']) + '</h3><p>'
            + esc(f['explanation'] or f.get('hypothesis', '')) + '</p>'
            + ('<p>Errors: ' + esc(', '.join(f['errors'])) + '</p>' if f['errors'] else '')
            + ''.join('<pre><code>' + esc(e['source']) + '</code></pre>' for e in f['evidence']) + '</article>')
    kind = 'Local static analysis' if report['analysis_kind'] == 'local_static' else 'Direct LLM scanner · v2'
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart contract scan report</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#14213d;background:#f4f6fa;margin:0}main{max-width:1000px;margin:auto;padding:40px 24px}article,section{background:white;border:1px solid #dce3ee;border-radius:12px;padding:24px;margin:20px 0}h1{font-size:36px;line-height:1.15}h2{font-size:22px;overflow-wrap:anywhere}.tag{font-weight:700;color:#1d4ed8}pre{padding:16px;background:#f1f5f9;overflow:auto;font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}small{color:#475569}dl{display:grid;grid-template-columns:180px 1fr;gap:8px}dd{margin:0;overflow-wrap:anywhere}</style><main>''' + \
        '<small>CONTEXT AUDIT · SCAN REPORT</small><h1>Smart contract analysis</h1><p>' + esc(kind) + '</p><section><dl>' + \
        ''.join('<dt>' + esc(k) + '</dt><dd>' + esc(v) + '</dd>' for k, v in (
            ('Status', report['status']), ('Compiler', report['compiler']), ('Model', report['model'] or 'No model requests'),
            ('Created', report['created_utc']), ('Source SHA-256', report['source_sha256']),
            ('API-key requests', report['usage']['api_calls']), ('Codex model turns', report['usage'].get('model_turns', 0)), ('Reported tokens', report['usage']['total_tokens']))) + \
        '</dl></section>' + (''.join(cards) or '<section>No findings were reported. This does not prove security.</section>') + \
        '<section><h2>Coverage and counts</h2><pre>' + esc(json.dumps(report['counts'], indent=2)) + '</pre></section>' + \
        '<section><h2>Limitations</h2><ul>' + ''.join('<li>' + esc(s) + '</li>' for s in report['limitations']) + \
        '</ul></section><section><h2>Analyzed source</h2><pre><code>' + esc(report['source']) + '</code></pre></section></main></html>'
