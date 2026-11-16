"""Opt-in smoke transport: shared counted-input reservations and hard call caps.

No client is constructed until an explicitly approved runner starts execution.
The same Responses schemas/messages are used by normal v2 discovery/verification.
"""
import json
import os
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version

from openai import OpenAI
from context_audit import direct_discovery as discovery
from context_audit import direct_verification as verification
from context_audit.v2_artifacts import atomic_json, digest, file_hash, implementation_hash, validate_discovery
from context_audit.v2_errors import DiagnosticFailure, exception_metadata, safe_id
from context_audit.v2_response import response_format, parse_result
from context_audit.v2_pipeline import run_verification, markdown

DEFAULT_LIMITS = verification.Limits(max_candidates=2, max_rounds=3, max_fragments=4,
    max_source_tokens=4000, max_input_tokens=6000, max_output_tokens=2500, max_total_tokens=40000)
RETRY_LIMITS = verification.Limits(max_candidates=1, max_rounds=3, max_fragments=4,
    max_source_tokens=4000, max_input_tokens=6000, max_output_tokens=2500, max_total_tokens=18000)
RETRY_BUDGET = {'max_discovery_calls': 0, 'max_generation_calls': 3, 'max_count_calls': 3,
                'max_reserved_tokens': 18000, 'max_input_tokens_per_call': 6000}
BUDGET = {'max_discovery_calls': 1, 'max_generation_calls': 7, 'max_count_calls': 7,
          'max_reserved_tokens': 40000, 'max_input_tokens_per_call': 6000}


class SmokeStopped(DiagnosticFailure):
    """Safe category and allowlisted metadata; no exception message or body."""


class CountedTransport:
    def __init__(self, client, model, output, budget):
        self.client, self.model = client, model
        self.output = Path(output)
        self.state = {'model': model, 'budget': budget, 'generation_calls': 0, 'count_calls': 0,
                      'discovery_calls': 0, 'reserved_tokens': 0, 'stopped': False, 'events': []}
        self.save()

    def save(self):
        atomic_json(self.output / 'budget_ledger.json', self.state)

    def stop(self, code):
        self.state.update(stopped=True, stop_reason=code)
        self.save()
        raise SmokeStopped(code)

    def call(self, stage, messages, schema, max_output_tokens, *, candidate_id=None):
        state, budget = self.state, self.state['budget']
        if state['stopped']:
            raise SmokeStopped(state['stop_reason'])
        if state['generation_calls'] >= budget['max_generation_calls'] or state['count_calls'] >= budget['max_count_calls']:
            self.stop('CALL_BUDGET')
        if stage == 'discovery' and state['discovery_calls'] >= budget['max_discovery_calls']:
            self.stop('DISCOVERY_CALL_BUDGET')
        if state['reserved_tokens'] + max_output_tokens > budget['max_reserved_tokens']:
            self.stop('TOKEN_RESERVATION_BUDGET')
        body = {'model': self.model, 'input': messages,
                'text': response_format(schema), 'truncation': 'disabled'}
        event = {'stage': stage, 'candidate_id': safe_id(candidate_id),
                 'attempt': len(state['events']) + 1, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                 'request_sha256': digest(body),
                 'max_output_tokens': max_output_tokens, 'status': 'count_pending'}
        state['events'].append(event)
        state['count_calls'] += 1
        self.save()
        count_started = monotonic()
        try:
            count = self.client.responses.input_tokens.count(**body).input_tokens
        except BaseException as exc:
            event['count_elapsed_ms'] = round((monotonic() - count_started) * 1000, 3)
            event.update(status='count_failed_or_interrupted', error={**exception_metadata(exc), 'processing_stage': 'input_token_count',
                'candidate_id': safe_id(candidate_id), 'attempt': event['attempt']})
            state.update(stopped=True, stop_reason='COUNT_FAILED_OR_INTERRUPTED')
            self.save()
            raise SmokeStopped('COUNT_FAILED_OR_INTERRUPTED', event['error']) from None
        event['count_elapsed_ms'] = round((monotonic() - count_started) * 1000, 3)
        if type(count) is not int or count < 0:
            self.stop('INVALID_INPUT_COUNT')
        event['input_tokens_counted'] = count
        reservation = count + max_output_tokens
        if count > budget['max_input_tokens_per_call'] or state['reserved_tokens'] + reservation > budget['max_reserved_tokens']:
            event['status'] = 'blocked_before_generation'
            self.stop('TOKEN_RESERVATION_BUDGET')
        state['reserved_tokens'] += reservation  # Never refunded, even after failure.
        state['generation_calls'] += 1
        state['discovery_calls'] += stage == 'discovery'
        event.update(status='generation_pending', reserved_tokens=reservation)
        self.save()
        generation_started = monotonic()
        try:
            # Identical counted JSON schema, but retain envelope/usage BEFORE local parsing.
            response = self.client.responses.create(**body, max_output_tokens=max_output_tokens,
                store=False, service_tier='default')
        except BaseException as exc:
            event['generation_elapsed_ms'] = round((monotonic() - generation_started) * 1000, 3)
            error = {**exception_metadata(exc), 'processing_stage': 'generation_request',
                     'candidate_id': safe_id(candidate_id), 'attempt': event['attempt']}
            event.update(status='generation_outcome_unknown', error=error)
            state.update(stopped=True, stop_reason='GENERATION_FAILED_OR_INTERRUPTED')
            self.save()
            raise SmokeStopped('GENERATION_FAILED_OR_INTERRUPTED', error) from None
        event['generation_elapsed_ms'] = round((monotonic() - generation_started) * 1000, 3)
        result = parse_result(response, schema, candidate_id=candidate_id)
        usage = result['usage']
        event.update(status='received', response_id=result.get('response_id'), response_model=result.get('model'), usage=usage)
        valid_usage = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens', 'total_tokens'))
        if (not valid_usage or usage['input_tokens'] != count or usage['output_tokens'] > max_output_tokens or
                usage['total_tokens'] != usage['input_tokens'] + usage['output_tokens']):
            state.update(stopped=True, stop_reason='USAGE_OR_COUNT_MISMATCH')
        if result['status'] == 'response_parse_failed':
            result['diagnostic']['attempt'] = event['attempt']
            event.update(status='response_parse_failed', error=result['diagnostic'])
            state.update(stopped=True, stop_reason='RESPONSE_PARSE_FAILED')
        elif result['status'] != 'completed':
            state.update(stopped=True, stop_reason='INCOMPLETE_STRUCTURED_RESPONSE')
            event['status'] = 'returned'
        else:
            event['status'] = 'returned'
        self.save()
        return result

    def discover(self, batch):
        return self.call('discovery', discovery.messages(batch), discovery.DiscoveryResponse, 8000)

    def verify(self, payload, supplied, *, max_output_tokens):
        return self.call('verification', verification.messages(payload, supplied), verification.VerificationResponse, max_output_tokens, candidate_id=payload['candidate']['candidate_id'])


def code_identity():
    return {'modules': implementation_hash(['v2_smoke', 'v2_pipeline', 'v2_artifacts', 'direct_discovery', 'direct_verification', 'verdict_consistency', 'payload', 'v2_errors', 'v2_response', 'function_index']),
            'runner': file_hash(Path(__file__).resolve().parents[2] / 'scripts/run_v2_smoke.py'),
            'openai_sdk': version('openai')}


def prepare_plan(source, model, output, *, require_single_batch=True):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Smoke output must be a new directory')
    contracts, catalog = discovery.prepare(source)
    batches, coverage = discovery.make_batches(contracts)
    if require_single_batch and (len(batches) != 1 or any(not r['included'] for r in coverage)):
        raise ValueError('Smoke requires exactly one complete structural batch')
    if not model.strip():
        raise ValueError('Explicit proposed model required')
    return {'version': 1, 'purpose': 'development engineering smoke test; not accuracy benchmark',
            'source': str(source), 'source_identity': catalog.source_identity, 'output': str(output),
            'model': model, 'active_model_at_preflight': os.environ.get('OPENAI_MODEL'),
            'credential_present_at_preflight': bool(os.environ.get('OPENAI_API_KEY')),
            'configuration': code_identity(), 'limits': DEFAULT_LIMITS.model_dump(), 'budget': BUDGET,
            'discovery_batches': len(batches), 'coverage': coverage,
            'compiler_readiness': catalog.preparation_metadata,
            'discovery_prompt_estimated_tokens': sum(len(json.dumps(discovery.messages(b))) // 4 + 1 for b in batches),
            'status': 'AWAITING_USER_APPROVAL_AND_CONFIGURATION'}


def prepare_verification_plan(source, model, output, candidate_file):
    """Validate immutable discovery offline; create a NEW explicit attempt, not resume."""
    plan = prepare_plan(source, model, output, require_single_batch=False)
    candidate_file = Path(candidate_file).resolve()
    saved = json.loads(candidate_file.read_text())
    contracts, catalog = discovery.prepare(Path(source))
    validate_discovery(saved, contracts, catalog, expected_model=model)
    if saved.get('errors') or len(saved['candidates']) != 1:
        raise ValueError('Controlled retry requires one candidate and successful saved discovery')
    for candidate in saved['candidates']:
        verification.validate_candidate(candidate, contracts, catalog)
    plan.update(execution_mode='verification_only', candidate_file=str(candidate_file),
                candidate_file_sha256=file_hash(candidate_file), discovery_artifact_sha256=digest(saved),
                original_candidate_ids=[c['candidate_id'] for c in saved['candidates']],
                limits=RETRY_LIMITS.model_dump(), budget=dict(RETRY_BUDGET),
                discovery_batches=0, discovery_prompt_estimated_tokens=0,
                prior_attempt_policy='Unknown prior outcome retained; no session replay or resume. New execution requires explicit approval.')
    return plan


def execute_plan(plan, *, client_factory=None):
    """Call only after explicit user approval. No environment/credential mutation."""
    if plan.get('version') != 1 or plan.get('configuration') != code_identity():
        raise ValueError('Smoke implementation/SDK changed; regenerate and review plan')
    retry = plan.get('execution_mode') == 'verification_only'
    expected_budget, expected_limits = (RETRY_BUDGET, RETRY_LIMITS) if retry else (BUDGET, DEFAULT_LIMITS)
    if plan.get('budget') != expected_budget or plan.get('limits') != expected_limits.model_dump():
        raise ValueError('Smoke limits changed; regenerate and review plan')
    if os.environ.get('OPENAI_MODEL') != plan['model'] or not os.environ.get('OPENAI_API_KEY'):
        raise ValueError('Approved model and API credential must be configured in the environment')
    if os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/') != 'https://api.openai.com/v1':
        raise ValueError('Smoke pricing and token counting require the official OpenAI endpoint')
    output = Path(plan['output'])
    if output.exists():
        raise ValueError('Refusing to replay a smoke run or reuse its output')
    contracts, catalog = discovery.prepare(Path(plan['source']))
    if catalog.source_identity != plan['source_identity']:
        raise ValueError('Source, compiler or sanitizer changed since the reviewed plan')
    batches, coverage = discovery.make_batches(contracts)
    if not retry and (len(batches) != 1 or any(not r['included'] for r in coverage)):
        raise ValueError('Prepared coverage changed')
    found = None
    if retry:
        candidate_file = Path(plan['candidate_file'])
        if file_hash(candidate_file) != plan['candidate_file_sha256']:
            raise ValueError('Saved discovery file changed since approval')
        found = json.loads(candidate_file.read_text())
        if digest(found) != plan['discovery_artifact_sha256']:
            raise ValueError('Saved discovery checksum changed')
        validate_discovery(found, contracts, catalog)
        if [c['candidate_id'] for c in found['candidates']] != plan['original_candidate_ids']:
            raise ValueError('Candidate selection changed')
        for candidate in found['candidates']:
            verification.validate_candidate(candidate, contracts, catalog)
    output.mkdir(parents=True, exist_ok=False)
    # Use a sibling metadata directory so existing v2 output protections remain intact.
    analysis_output = output / 'analysis'
    atomic_json(output / 'smoke_manifest.json', {'plan': plan, 'plan_sha256': digest(plan), 'approved_execution': True})
    client = (client_factory or OpenAI)(timeout=60, max_retries=0, base_url='https://api.openai.com/v1')
    transport = CountedTransport(client, plan['model'], output, plan['budget'])
    if found is None:
        found = discovery.run_discovery(contracts, catalog, execute=True, analyze_fn=transport.discover)
    atomic_json(analysis_output / 'discovery.json', found)
    (analysis_output / 'summary.md').write_text(discovery.markdown(found))
    report = run_verification(found, contracts, catalog, analysis_output, limits=verification.Limits(**plan['limits']), analyze_fn=transport.verify)
    report['smoke_transport'] = {k: v for k, v in transport.state.items() if k != 'events'}
    report['smoke_plan_sha256'] = digest(plan)
    report['discovery_reused'] = retry
    report['smoke_transport']['note'] = 'Exact transport counts are authoritative; standard pipeline api_calls count analyzer attempts, including locally blocked attempts.'
    atomic_json(analysis_output / 'report.json', report)
    (analysis_output / 'report.md').write_text(markdown(report) + '\n## Smoke transport\n\n```json\n' + json.dumps(report['smoke_transport'], indent=2) + '\n```\n')
    return report
