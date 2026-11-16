import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from context_audit import development_experiment as e
from context_audit import direct_discovery as d
from context_audit.v2_artifacts import atomic_json, digest
from context_audit.v2_smoke import SmokeStopped
from test_direct_discovery import prepared
from test_v2_verification_failures import envelope


class DevelopmentExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = MagicMock()
        self.factory = MagicMock(return_value=self.client)
        self.client.responses.input_tokens.count.return_value = SimpleNamespace(input_tokens=100)
        self.client.responses.create.return_value = envelope(json.dumps({'examined_functions': [], 'candidates': []}))
        self.plan = {'model': 'mock', 'budget': {'max_generation_calls': 2, 'max_count_calls': 2,
            'max_discovery_calls': 2, 'max_reserved_tokens': 1000, 'max_input_tokens_per_call': 200}}

    def call(self, t, message='one'):
        return t.call('discovery', [{'role': 'user', 'content': message}], d.DiscoveryResponse, 100)

    def test_journal_resume_reuses_without_client_or_usage_duplication(self):
        t = e.JournalTransport(self.root, self.plan, self.factory)
        first = self.call(t)
        resumed = e.JournalTransport(self.root, self.plan, self.factory, True)
        self.assertEqual(self.call(resumed), first)
        self.assertEqual(self.factory.call_count, 1)
        self.assertEqual(resumed.state['generation_calls'], 1)

    def test_resume_preserves_call_budget(self):
        t = e.JournalTransport(self.root, self.plan, self.factory)
        self.call(t)
        resumed = e.JournalTransport(self.root, self.plan, self.factory, True)
        self.call(resumed, 'two')
        with self.assertRaises(SmokeStopped): self.call(resumed, 'three')
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_resume_preserves_reserved_tokens(self):
        self.plan['budget']['max_reserved_tokens'] = 300
        self.call(e.JournalTransport(self.root, self.plan, self.factory))
        resumed = e.JournalTransport(self.root, self.plan, self.factory, True)
        with self.assertRaises(SmokeStopped): self.call(resumed, 'two')
        self.assertEqual(self.client.responses.create.call_count, 1)
        self.assertEqual(resumed.transport.state['reserved_tokens'], 200)

    def test_pending_request_cannot_be_replayed(self):
        self.client.responses.create.side_effect = KeyboardInterrupt()
        with self.assertRaises(SmokeStopped): self.call(e.JournalTransport(self.root, self.plan, self.factory))
        with self.assertRaises(ValueError): e.JournalTransport(self.root, self.plan, self.factory, True)
        self.assertEqual(self.client.responses.create.call_count, 1)

    def test_changed_plan_cannot_resume(self):
        self.call(e.JournalTransport(self.root, self.plan, self.factory))
        changed = copy.deepcopy(self.plan); changed['model'] = 'other'
        with self.assertRaises(ValueError): e.JournalTransport(self.root, changed, self.factory, True)

    def test_modified_ledger_cannot_reset_budget(self):
        self.call(e.JournalTransport(self.root, self.plan, self.factory))
        path = self.root / 'budget_ledger.json'
        state = json.loads(path.read_text()); state['generation_calls'] = 0; atomic_json(path, state)
        with self.assertRaises(ValueError): e.JournalTransport(self.root, self.plan, self.factory, True)

    def test_modified_cached_response_rejected(self):
        self.call(e.JournalTransport(self.root, self.plan, self.factory))
        path = next((self.root / 'requests').glob('*.json'))
        entry = json.loads(path.read_text()); entry['data']['response']['usage'] = {}; atomic_json(path, entry)
        with self.assertRaises(ValueError): e.JournalTransport(self.root, self.plan, self.factory, True)

    def test_input_cap_blocks_generation(self):
        self.plan['budget']['max_input_tokens_per_call'] = 99
        with self.assertRaises(SmokeStopped): self.call(e.JournalTransport(self.root, self.plan, self.factory))
        self.client.responses.create.assert_not_called()

    def test_prepare_no_api_and_no_ground_truth(self):
        source, _, _ = prepared(self.root)
        with patch.object(e, 'OpenAI', side_effect=AssertionError('OFFLINE')):
            plan = e.prepare(source, 'mock', self.root / 'run', 'b2', 10, 40000)
        self.assertNotIn('SWC-107', json.dumps(plan))
        self.assertTrue(all(r['included'] for r in plan['v2_coverage']))
        self.assertFalse(Path(plan['output']).exists())

    def test_configuration_mismatch_blocks_before_client(self):
        with self.assertRaises(ValueError): e.execute({'configuration': {}}, client_factory=self.factory)
        self.factory.assert_not_called()

    def test_b2_end_to_end_empty_discovery_and_resume(self):
        source, _, _ = prepared(self.root)
        plan = e.prepare(source, 'mock', self.root / 'run', 'b2', 10, 40000)
        def generate(**kw):
            batch = json.loads(kw['input'][1]['content'])
            # Use actual prompt format: its structural summary is the JSON payload.
            ids = [f['fragment_id'] for f in batch['functions']]
            return envelope(json.dumps({'examined_functions': [{'fragment_id': fid, 'reason': 'Mock review'} for fid in ids], 'candidates': []}))
        self.client.responses.create.side_effect = generate
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock', 'OPENAI_API_KEY': 'offline-placeholder', 'OPENAI_BASE_URL': 'https://api.openai.com/v1'}):
            report = e.execute(plan, client_factory=self.factory)
            self.assertEqual(report['coverage_counts']['examined'], len(plan['v2_coverage']))
            calls = self.client.responses.create.call_count
            again = e.execute(plan, resume=True, client_factory=self.factory)
            self.assertEqual(again['coverage_counts'], report['coverage_counts'])
            self.assertEqual(self.client.responses.create.call_count, calls)

    def test_b1_end_to_end_uses_existing_protocol(self):
        source, _, _ = prepared(self.root)
        plan = e.prepare(source, 'mock', self.root / 'run', 'b1', 10, 40000)
        self.client.responses.create.return_value = envelope(json.dumps({'action': 'final', 'requested_ids': [],
            'verdict': 'no_vulnerability_found', 'findings': [], 'explanation': 'Mock review'}))
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock', 'OPENAI_API_KEY': 'offline-placeholder', 'OPENAI_BASE_URL': 'https://api.openai.com/v1'}):
            report = e.execute(plan, client_factory=self.factory)
            self.assertEqual(len(report['sessions']), plan['v1_functions'])
            self.assertTrue(all(not s['errors'] for s in report['sessions']))
            calls = self.client.responses.create.call_count
            e.execute(plan, resume=True, client_factory=self.factory)
            self.assertEqual(self.client.responses.create.call_count, calls)

    def test_deleted_request_journal_cannot_replay(self):
        self.call(e.JournalTransport(self.root, self.plan, self.factory))
        next((self.root / 'requests').glob('*.json')).unlink()
        with self.assertRaises(ValueError): e.JournalTransport(self.root, self.plan, self.factory, True)
