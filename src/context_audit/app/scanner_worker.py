"""Isolated interactive Mode B v2 jobs; never reuse frozen experiment outputs."""
import hashlib
import json
from pathlib import Path
import sys

from context_audit import direct_discovery as discovery, direct_verification as verification
from context_audit.app.scanner import ScannerSettings
from context_audit.direct_preparation import PreparationError
from context_audit.v2_artifacts import atomic_json
from context_audit.v2_pipeline import run_verification


def run_job(request, *, discover_fn=None, verify_fn=None):
    source = Path(request['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != request['source_sha256']:
        raise ValueError('SOURCE_CHANGED')
    action = request['action']
    if action not in ('prepare', 'scan'):
        raise ValueError('UNKNOWN_ACTION')
    settings = ScannerSettings(**request['settings']) if action == 'scan' else None
    if settings:
        settings.validate()
    contracts, catalog = discovery.prepare(source)
    batches, coverage = discovery.make_batches(contracts)
    prepared = {'source_sha256': request['source_sha256'], 'source_identity': catalog.source_identity,
        'compiler': catalog.preparation_metadata['compiler_used'], 'contracts': contracts,
        'function_count': len(coverage), 'batch_count': len(batches),
        'analyzable_functions': sum(r['included'] for r in coverage), 'coverage': coverage}
    if action == 'prepare':
        return prepared
    if request['prepared_identity'] != catalog.source_identity:
        raise ValueError('PREPARED_SOURCE_OR_PROTOCOL_CHANGED')
    if len(batches) > settings.max_batches:
        raise ValueError('DISCOVERY_REQUEST_LIMIT')
    if not batches:
        raise ValueError('NO_ANALYZABLE_FUNCTIONS')
    output = Path(request['output'])
    if output.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    output.mkdir(parents=True)
    if settings.provider == 'codex':
        from context_audit.codex_transport import CodexTransport
        transport = CodexTransport(output.parent/(output.name+'-codex'), settings.model,
            max_calls=len(batches)+settings.max_candidates*settings.max_rounds,
            max_tokens=settings.observed_token_cap(len(batches)))
        discover_fn, verify_fn = transport.discover, transport.verify
    found = discovery.run_discovery(contracts, catalog, execute=True, analyze_fn=discover_fn)
    atomic_json(output / 'discovery.json', found)
    limits = verification.Limits(max_rounds=settings.max_rounds, max_candidates=settings.max_candidates,
        max_total_tokens=settings.max_verification_tokens, max_output_tokens=settings.max_output_tokens,
        max_fragments=settings.max_fragments, max_source_tokens=settings.max_source_tokens,
        max_input_tokens=settings.max_input_tokens)
    report = run_verification(found, contracts, catalog, output, limits=limits, analyze_fn=verify_fn,
        input_token_estimator=getattr(transport,'estimate_input_tokens',None) if settings.provider=='codex' else None)
    return {'report': report, 'compiler': prepared['compiler'], 'coverage': found['coverage'],
        'subscription_transport': transport.state if settings.provider == 'codex' else None}


def main():
    try:
        result = run_job(json.load(sys.stdin))
    except PreparationError as exc:
        result = {'error': 'Source preparation failed: ' + exc.metadata['preparation_status'] + '. Check the source and installed Solidity compiler.'}
    except Exception as exc:
        # Never expose raw provider errors, source strings or environment values.
        result = {'error': 'Scanner stopped (' + type(exc).__name__ + '). Check source, configuration and limits. No automatic retry was made.'}
    print(json.dumps(result))
    return int('error' in result)


if __name__ == '__main__':
    raise SystemExit(main())
