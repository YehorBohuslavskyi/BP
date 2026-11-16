"""Saved-response reproduction and prompt/source-set enforcement. All calls mocked."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from context_audit import direct_discovery as d,direct_verification as v
from context_audit import v2_candidate_continuation as continuation
from context_audit.v2_artifacts import digest
from test_v2_verification_failures import envelope
from consistency_fixtures import with_basis

PARENT=Path('experiments/mode-b-v2-dataset-2026-11-09/manifest.json')
ROOT=Path('runs/mode-b-v2-dataset-2026-11-09/development/ixo-authoriser')
MODEL='gpt-5.4-mini-2026-03-17'

class UnseenEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest=json.loads(PARENT.read_text());cls.case=next(c for c in manifest['cases'] if c['id']=='ixo-authoriser')
        cls.contracts,cls.catalog=d.prepare(Path(cls.case['source']))
        cls.sessions={}
        for p in (ROOT/'analysis/sessions').glob('*.json'):
            r=json.loads(p.read_text())['result'];cls.sessions[r['candidate']['model_candidate_id']]=r
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        from current_protocol_fixtures import continuation_fixture
        self.parent=continuation_fixture(self.root,PARENT,'ixo-authoriser',self.contracts,self.catalog,MODEL)
    def test_saved_failures_are_real_unsupplied_ids_and_still_rejected(self):
        expected={'cand-1':{'fragment-15fd53ee88bf2a9b4fd2','fragment-91517c7c74cd1cf140af','fragment-9837f46d928e8d36b510'},
                  'cand-2':{'fragment-91517c7c74cd1cf140af'}}
        for cid,unseen in expected.items():
            saved=self.sessions[cid];attempt=saved['rounds'][0];p=json.loads(attempt['messages'][1]['content'])
            self.assertEqual(p['provided_context'],[])
            self.assertEqual(set(attempt['response']['assessment']['evidence_ids'])-{p['target']['id']},unseen)
            self.assertTrue(unseen<={f['id'] for f in p['available_context']})
            result=v.verify_candidate(saved['candidate'],self.contracts,self.catalog,
                analyze_fn=lambda *a,**kw:{**copy.deepcopy(attempt['response']), 'assessment':with_basis(attempt['response']['assessment'],[p['target']])})
            self.assertEqual(result['status'],'processing_failed');self.assertIsNone(result['verdict'])
            self.assertEqual(result['errors'][0]['code'],'UNSEEN_EVIDENCE_ID')
            self.assertEqual(set(result['errors'][0]['diagnostic']['unsupplied_catalog_ids']),unseen)
            self.assertEqual(result['provided_context'],[])
    def test_primary_is_initially_only_evidence_and_deferred_source_is_not_preloaded(self):
        saved=self.sessions['cand-1'];c,row=v.validate_candidate(saved['candidate'],self.contracts,self.catalog)
        payload=v.payload_for(c,row,self.catalog);wire=json.loads(v.messages(payload,[])[1]['content'])
        self.assertEqual(wire['evidence_policy']['allowed_evidence_ids'],[c['primary_fragment_id']])
        self.assertEqual(wire['provided_context'],[])
        self.assertEqual(wire['evidence_policy']['discovery_requested_ids_not_yet_supplied'],c['requested_context_ids'])
        self.assertFalse(wire['evidence_policy']['available_context_is_source'])
    def test_source_becomes_evidence_only_after_successful_request_context(self):
        saved=self.sessions['cand-2'];fid=saved['candidate']['requested_context_ids'][0];calls=[]
        def mock(payload,supplied,**kw):
            wire=json.loads(v.messages(payload,supplied)[1]['content']);calls.append(wire)
            assessment=copy.deepcopy(saved['rounds'][0]['response']['assessment'])
            if not supplied:
                assessment.update(action='request_context',requested_ids=[fid],verdict=None,severity=None,
                                  evidence_ids=[],execution_flow=[],incomplete_evidence=['Modifier source required'])
            return {'assessment':with_basis(assessment,[payload['target'],*supplied]),'usage':{'input_tokens':10,'output_tokens':5,'total_tokens':15}}
        result=v.verify_candidate(saved['candidate'],self.contracts,self.catalog,analyze_fn=mock)
        self.assertEqual(result['status'],'completed')
        self.assertIn(fid,calls[1]['evidence_policy']['allowed_evidence_ids'])
        self.assertNotIn(fid,[f['id'] for f in calls[1]['available_context']])
        self.assertEqual(result['requests'][0]['supplied_ids'],[fid])
        self.assertEqual(result['round_count'],2)
    def test_deferred_fragment_does_not_count_as_supplied_under_zero_budget(self):
        saved=self.sessions['cand-2'];fid=saved['candidate']['requested_context_ids'][0]
        assessment=copy.deepcopy(saved['rounds'][0]['response']['assessment'])
        assessment.update(action='request_context',requested_ids=[fid],verdict=None,severity=None,evidence_ids=[],execution_flow=[],verdict_basis=None)
        result=v.verify_candidate(saved['candidate'],self.contracts,self.catalog,limits=v.Limits(max_fragments=0),
            analyze_fn=lambda *a,**kw:{'assessment':assessment,'usage':{}})
        self.assertEqual(result['status'],'budget_exhausted');self.assertIsNone(result['verdict'])
        self.assertEqual(result['provided_context'],[])
    def test_fabricated_ids_stay_invalid_and_raw_unknown_values_not_logged(self):
        saved=self.sessions['cand-2'];assessment=copy.deepcopy(saved['rounds'][0]['response']['assessment'])
        assessment['evidence_ids'].append('secret-value-not-a-fragment')
        assessment=with_basis(assessment,[self.catalog.get(saved['candidate']['primary_fragment_id'])])
        result=v.verify_candidate(saved['candidate'],self.contracts,self.catalog,
            analyze_fn=lambda *a,**kw:{'assessment':assessment,'usage':{}})
        diagnostic=result['errors'][0]['diagnostic']
        self.assertEqual(diagnostic['unknown_evidence_id_count'],1)
        self.assertNotIn('secret-value',json.dumps(diagnostic))
    def test_original_rejection_remains_valid(self):
        v.validate_saved_result(self.sessions['cand-3'],self.contracts,self.catalog,historical=True)
        self.assertTrue(v.replay_consistency(self.sessions['cand-3'],self.contracts,self.catalog)['consistency_validation']['passed'])
        self.assertEqual(self.sessions['cand-3']['verdict'],'rejected')
    def test_plan_only_two_failed_candidates_and_remaining_budget(self):
        plan=continuation.prepare(self.parent,'ixo-authoriser',self.root/'run')
        self.assertEqual(set(plan['retry_candidate_ids']),{'batch-0001:cand-1','batch-0001:cand-2'})
        self.assertEqual(plan['retained_candidate_ids'],['batch-0001:cand-3'])
        self.assertEqual(plan['budget']['max_generation_calls'],6)
        self.assertEqual(plan['budget']['max_discovery_calls'],0)
        self.assertEqual(plan['budget']['max_reserved_tokens'],40000)
    def test_continuation_mock_and_resume_do_not_rerun_rejection_or_discovery(self):
        plan=continuation.prepare(self.parent,'ixo-authoriser',self.root/'run');client=MagicMock()
        client.responses.input_tokens.count.return_value=SimpleNamespace(input_tokens=100)
        def generate(**kw):
            p=json.loads(kw['input'][1]['content']);cid=p['candidate']['candidate_id']
            self.assertIn(cid,plan['retry_candidate_ids'])
            return envelope(json.dumps(with_basis({'action':'final','requested_ids':[],'verdict':'inconclusive','severity':None,
                'explanation':'Mock source insufficient','evidence_ids':[p['target']['id']],'execution_flow':[],
                'incomplete_evidence':['Missing external source']},[p['target']])))
        client.responses.create.side_effect=generate
        with patch.dict(os.environ,{'OPENAI_MODEL':MODEL,'OPENAI_API_KEY':'offline-placeholder','OPENAI_BASE_URL':'https://api.openai.com/v1'}):
            report=continuation.execute(plan,client_factory=lambda **kw:client)
            self.assertEqual(client.responses.create.call_count,2)
            self.assertEqual(report['coverage_counts']['rejected_candidates'],1)
            self.assertEqual(report['actual_all_attempts_usage_including_history']['total_tokens'],9526+240)
            continuation.execute(plan,resume=True,client_factory=lambda **kw:self.fail('API on completed resume'))
            self.assertEqual(client.responses.create.call_count,2)
    def test_parent_checksum_mismatch_blocks_before_client(self):
        plan=continuation.prepare(self.parent,'ixo-authoriser',self.root/'run');plan['parent_manifest_sha256']='bad'
        with patch.dict(os.environ,{'OPENAI_MODEL':MODEL,'OPENAI_API_KEY':'offline-placeholder','OPENAI_BASE_URL':'https://api.openai.com/v1'}):
            with self.assertRaises(ValueError):continuation.execute(plan,client_factory=lambda **kw:self.fail('API before provenance validation'))

    def test_frozen_historical_parent_is_not_authorized_by_new_index(self):
        with self.assertRaisesRegex(ValueError,'PARENT_SOURCE_MISMATCH'):
            continuation.prepare(PARENT,'ixo-authoriser',self.root/'must-not-run')
