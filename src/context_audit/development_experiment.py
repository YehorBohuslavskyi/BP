"""One-source, approval-bound development runs; no dataset labels enter this module."""
import json
import os
from pathlib import Path

from openai import OpenAI
from context_audit import direct, direct_discovery as discovery, direct_verification as verification
from context_audit.v2_artifacts import atomic_json, digest, file_hash, implementation_hash
from context_audit.v2_smoke import CountedTransport, code_identity, SmokeStopped
from context_audit.v2_pipeline import run_verification, markdown


def identity():
    return {**code_identity(), 'experiment': implementation_hash(['development_experiment']),
            'cli': file_hash(Path(__file__).resolve().parents[2] / 'scripts/run_development_experiment.py')}


def prepare(source, model, output, method, max_calls, max_tokens):
    if method not in ('b1', 'b2') or not model.strip() or max_calls < 1 or max_tokens < 1:
        raise ValueError('INVALID_PLAN_PARAMETERS')
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    contracts, catalog = discovery.prepare(Path(source).resolve())
    payloads, _ = direct.prepare(Path(source).resolve())
    batches, coverage = discovery.make_batches(contracts)
    if not batches or any(not r['included'] for r in coverage):
        raise ValueError('INCOMPLETE_STRUCTURAL_COVERAGE')
    budget = dict(max_discovery_calls=len(batches) if method == 'b2' else 0,
                  max_generation_calls=max_calls, max_count_calls=max_calls,
                  max_reserved_tokens=max_tokens, max_input_tokens_per_call=12000)
    limits = verification.Limits(max_candidates=3, max_rounds=3, max_fragments=8,
        max_source_tokens=8000, max_input_tokens=12000, max_output_tokens=4000, max_total_tokens=max_tokens)
    return {'version': 1, 'method': method, 'model': model, 'source': str(Path(source).resolve()),
            'output': str(output), 'configuration': identity(), 'source_identity': catalog.source_identity,
            'budget': budget, 'limits': limits.model_dump(), 'v1_rounds': 3,
            'v1_functions': len(payloads), 'v2_coverage': coverage, 'discovery_batches': len(batches),
            'preparation': catalog.preparation_metadata,
            'initial_prompt_estimated_tokens': {
                'b1': sum(len(json.dumps(direct.messages(p, []))) // 4 + 1 for p in payloads),
                'b2': sum(len(json.dumps(discovery.messages(b))) // 4 + 1 for b in batches)},
            'purpose': 'development comparison, not held-out evaluation'}


class JournalTransport:
    """Reuse completed requests only; pending requests and uncertain ledgers fail closed."""
    def __init__(self, output, plan, client_factory, resume=False):
        self.output, self.plan, self.factory = Path(output), plan, client_factory
        self.transport = None
        self.cache = self.output / 'requests'
        self.cache.mkdir(exist_ok=True)
        self.state = None
        if resume:
            checkpoint = json.loads((self.output / 'transport_checkpoint.json').read_text())
            state = json.loads((self.output / 'budget_ledger.json').read_text())
            if (checkpoint != {'plan_sha256': digest(plan), 'ledger_sha256': digest(state)} or
                    state['budget'] != plan['budget'] or state['model'] != plan['model']):
                raise ValueError('TRANSPORT_CHECKPOINT_MISMATCH')
            paths = list(self.cache.glob('*.json'))
            if len(paths) != len(state['events']):
                raise ValueError('REQUEST_JOURNAL_INCOMPLETE')
            for path in paths:
                entry = json.loads(path.read_text())
                if (entry.get('status') != 'complete' or entry.get('sha256') != digest(entry.get('data')) or
                        entry['data']['plan_sha256'] != digest(plan) or
                        path.stem != digest(entry['data']['request'])):
                    raise ValueError('UNCERTAIN_OR_INVALID_REQUEST_CHECKPOINT')
            self.state = state

    def checkpoint(self):
        atomic_json(self.output / 'transport_checkpoint.json',
                    {'plan_sha256': digest(self.plan), 'ledger_sha256': digest(self.transport.state)})

    def call(self, stage, messages, schema, output_tokens, candidate_id=None):
        request = {'stage': stage, 'messages': messages, 'schema': schema.model_json_schema(),
                   'output_tokens': output_tokens, 'candidate_id': candidate_id}
        key = digest(request)
        path = self.cache / (key + '.json')
        if path.exists():
            entry = json.loads(path.read_text())
            if (entry.get('status') != 'complete' or entry.get('sha256') != digest(entry.get('data')) or
                    entry['data']['request'] != request or entry['data']['plan_sha256'] != digest(self.plan)):
                raise ValueError('UNCERTAIN_OR_INVALID_REQUEST_CHECKPOINT')
            return entry['data']['response']
        if self.state and self.state['stopped']:
            raise SmokeStopped('SAVED_TRANSPORT_STOPPED_NO_REPLAY')
        if self.transport is None:
            client = self.factory(timeout=60, max_retries=0, base_url='https://api.openai.com/v1')
            if self.state is None:
                self.transport = CountedTransport(client, self.plan['model'], self.output, self.plan['budget'])
            else:
                self.transport = object.__new__(CountedTransport)
                self.transport.client, self.transport.model = client, self.plan['model']
                self.transport.output, self.transport.state = self.output, self.state
            self.checkpoint()
        atomic_json(path, {'status': 'pending', 'request_sha256': key})
        try:
            response = self.transport.call(stage, messages, schema, output_tokens, candidate_id=candidate_id)
            data = {'plan_sha256': digest(self.plan), 'request': request, 'response': response}
            atomic_json(path, {'status': 'complete', 'data': data, 'sha256': digest(data)})
            return response
        finally:
            self.checkpoint()


def execute(plan, *, resume=False, client_factory=None):
    if plan['configuration'] != identity():
        raise ValueError('IMPLEMENTATION_OR_SDK_CHANGED')
    if os.environ.get('OPENAI_MODEL') != plan['model'] or not os.environ.get('OPENAI_API_KEY'):
        raise ValueError('MODEL_OR_CREDENTIAL_NOT_CONFIGURED')
    if os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/') != 'https://api.openai.com/v1':
        raise ValueError('OFFICIAL_ENDPOINT_REQUIRED')
    contracts, catalog = discovery.prepare(Path(plan['source']))
    if catalog.source_identity != plan['source_identity']:
        raise ValueError('SOURCE_COMPILER_OR_SANITIZER_CHANGED')
    output = Path(plan['output'])
    manifest = {'plan': plan, 'plan_sha256': digest(plan)}
    if resume:
        if json.loads((output / 'experiment_manifest.json').read_text()) != manifest:
            raise ValueError('RESUME_MANIFEST_MISMATCH')
    else:
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / 'experiment_manifest.json', manifest)
    transport = JournalTransport(output, plan, client_factory or OpenAI, resume)
    analysis = output / 'analysis'
    if plan['method'] == 'b2':
        found = discovery.run_discovery(contracts, catalog, execute=True, analyze_fn=lambda batch:
            transport.call('discovery', discovery.messages(batch), discovery.DiscoveryResponse, 8000))
        atomic_json(analysis / 'discovery.json', found)
        (analysis / 'summary.md').write_text(discovery.markdown(found))
        report = run_verification(found, contracts, catalog, analysis,
            resume=resume and (analysis / 'verification_manifest.json').exists(),
            limits=verification.Limits(**plan['limits']), analyze_fn=lambda p, s, **kw:
                transport.call('verification', verification.messages(p, s), verification.VerificationResponse,
                               kw['max_output_tokens'], p['candidate']['candidate_id']))
        (analysis / 'report.md').write_text(markdown(report))
    else:
        payloads, cat = direct.prepare(Path(plan['source']))
        results = []
        for i, payload in enumerate(payloads):
            result = direct.run_function(payload, cat, analysis / 'sessions' / f'{i:04d}.json',
                max_rounds=plan['v1_rounds'], analyze_fn=lambda p, s:
                    transport.call('direct', direct.messages(p, s), direct.DirectResponse, 4000, p['target']['id']))
            results.append(result)
        report = {'mode': 'b1', 'sessions': results, 'contracts': direct.aggregate(results),
                  'eligible_functions': len(payloads), 'usage': {k: sum(r['usage'][k] for r in results)
                    for k in ('input_tokens', 'output_tokens', 'total_tokens')}}
        atomic_json(analysis / 'report.json', report)
    ledger_path = output / 'budget_ledger.json'
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        report['transport'] = {k: v for k, v in ledger.items() if k != 'events'}
    atomic_json(analysis / 'report.json', report)
    return report
