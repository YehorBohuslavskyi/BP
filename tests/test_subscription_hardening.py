"""Context-bound wire and budget regression checks; no real model requests."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jsonschema
from pydantic import ValidationError
from context_audit import direct_verification as v
from context_audit.codex_transport import CodexTransport, CodexStopped, verification_wire, INPUT_OVERHEAD_RESERVE
from test_codex_transport import Probe
import test_direct_verification as fixtures
from test_direct_verification import request, final


class SourceRequestWireTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.VerificationTests('test_rejected')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.candidate,self.row=v.validate_candidate(self.fixture.candidate,self.fixture.contracts,self.fixture.catalog)
        self.payload=v.payload_for(self.candidate,self.row,self.fixture.catalog)

    def response(self,ids):
        return request(ids)['assessment']

    def test_unknown_or_already_supplied_ids_are_impossible_on_wire(self):
        context=v.safe_fragment(self.fixture.catalog.get(self.candidate['requested_context_ids'][0]))
        messages,Wire=verification_wire(self.payload,[context])
        for bad in ('fragment-typo',self.payload['target']['id'],context['id']):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                Wire.model_validate(self.response([bad]))
            with self.subTest(json_schema=bad), self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(self.response([bad]),Wire.model_json_schema())
        sent=json.loads(messages[1]['content'])
        self.assertNotIn(context['id'],[f['id'] for f in sent['available_context']])

    def test_valid_unseen_id_remains_requestable(self):
        messages,Wire=verification_wire(self.payload,[])
        fid=json.loads(messages[1]['content'])['available_context'][0]['id']
        result=self.response([fid])
        self.assertEqual(Wire.model_validate(result).requested_ids,[fid])
        jsonschema.validate(result,Wire.model_json_schema())

    def test_request_count_and_individual_source_cost_are_bounded(self):
        payload=copy.deepcopy(self.payload)
        payload['retrieval_budget']={'rounds_after_this':1,'max_new_fragments':1,'max_new_source_tokens':100000}
        _,Wire=verification_wire(payload,[])
        ids=[f['id'] for f in v.requestable_context(payload,[])][:2]
        self.assertEqual(len(ids),2)
        with self.assertRaises(ValidationError):Wire.model_validate(self.response(ids))
        payload['retrieval_budget']['max_new_source_tokens']=0
        sent,Wire=verification_wire(payload,[])
        self.assertEqual(json.loads(sent[1]['content'])['available_context'],[])
        with self.assertRaises(ValidationError):Wire.model_validate(self.response(ids[:1]))

    def test_last_round_requires_final_but_abstention_remains_possible(self):
        self.payload['retrieval_budget']={'rounds_after_this':0,'max_new_fragments':8,'max_new_source_tokens':8000}
        messages,Wire=verification_wire(self.payload,[])
        sent=json.loads(messages[1]['content'])
        self.assertNotIn('request_context',sent['response_protocol']['examples'])
        with self.assertRaises(ValidationError):
            Wire.model_validate(self.response([self.candidate['requested_context_ids'][0]]))
        result=final(self.payload,[],'inconclusive')['assessment']
        self.assertEqual(Wire.model_validate(result).verdict,'inconclusive')

    def test_evidence_and_claim_ids_are_limited_to_delivered_source(self):
        _,Wire=verification_wire(self.payload,[])
        result=final(self.payload,[],'confirmed')['assessment']
        self.assertEqual(Wire.model_validate(result).verdict,'confirmed')
        unseen=self.candidate['requested_context_ids'][0]
        result['verdict_basis']['evidence_claims'][0]['fragment_id']=unseen
        with self.assertRaises(ValidationError):Wire.model_validate(result)
        result=final(self.payload,[],'confirmed')['assessment'];result['evidence_ids']=[unseen]
        with self.assertRaises(ValidationError):Wire.model_validate(result)

    def test_core_still_rejects_bad_request_when_backend_ignores_schema(self):
        result=self.fixture.run_candidate(lambda p,s,**kw:request([p['target']['id']]))
        self.assertEqual(result['errors'][0]['code'],'REPEATED_CONTEXT_ID')
        self.assertIsNone(result['verdict'])

    def test_core_exports_remaining_capacity_and_forces_no_extra_retrieval_at_end(self):
        wires=[]
        def mock(p,s,**kw):
            wires.append(json.loads(v.messages(p,s)[1]['content']))
            return request(self.candidate['requested_context_ids'][:1]) if not s else final(p,s,'inconclusive')
        result=self.fixture.run_candidate(mock,limits=v.Limits(max_rounds=2,max_fragments=1))
        self.assertEqual(result['verdict'],'inconclusive')
        self.assertEqual(wires[0]['retrieval_budget']['rounds_after_this'],1)
        self.assertEqual(wires[1]['retrieval_budget']['rounds_after_this'],0)
        self.assertEqual(wires[1]['retrieval_budget']['max_new_fragments'],0)
        self.assertEqual(wires[1]['available_context'],[])

    def test_backend_overhead_can_stop_call_without_spending_or_verdict(self):
        with patch('context_audit.direct_verification.analyze') as live:
            result=v.verify_candidate(self.fixture.candidate,self.fixture.contracts,self.fixture.catalog,
                limits=v.Limits(max_total_tokens=60000),input_token_estimator=lambda _:60000)
        live.assert_not_called()
        self.assertEqual(result['round_count'],0)
        self.assertEqual(result['errors'][0]['code'],'TOKEN_BUDGET')
        self.assertIsNone(result['verdict'])

    def test_overhead_is_not_misclassified_as_scanner_payload_limit(self):
        result=self.fixture.run_candidate(input_token_estimator=lambda _:40000,limits=v.Limits(max_total_tokens=100000))
        self.assertEqual(result['verdict'],'confirmed')
        self.assertEqual(result['rounds'][0]['budget_estimate']['backend_input_tokens'],40000)
        self.assertEqual(result['usage']['total_tokens'],15)


class KnownUsageTests(unittest.TestCase):
    def test_completed_invalid_response_keeps_usage_and_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def fake_run(command,**kwargs):
                result=Path(command[command.index('--output-last-message')+1])
                result.write_text('{"ok":"invalid-boolean"}')
                events=[{'type':'thread.started','thread_id':'one'},
                    {'type':'turn.completed','usage':{'input_tokens':50000,'output_tokens':3}}]
                return SimpleNamespace(returncode=0,stdout='\n'.join(map(json.dumps,events)),stderr='')
            with patch('context_audit.codex_transport.resolve_paths',return_value=(root/'codex',root/'scratch')), \
                 patch('context_audit.codex_transport.login_status',return_value=True), \
                 patch('context_audit.codex_transport.subprocess.run',side_effect=fake_run) as run:
                transport=CodexTransport(root/'output')
                before=transport.estimate_input_tokens([])
                self.assertGreaterEqual(before,INPUT_OVERHEAD_RESERVE)
                result=transport.call('test',[],Probe,20)
                self.assertEqual(result['status'],'response_parse_failed')
                self.assertEqual(result['usage']['total_tokens'],50003)
                self.assertEqual(transport.state['observed_tokens'],50003)
                self.assertGreater(transport.estimate_input_tokens([]),before)
                with self.assertRaises(CodexStopped):transport.call('test',[],Probe,20)
                run.assert_called_once()
                saved=json.loads((root/'output/subscription-transport.json').read_text())
                self.assertEqual(saved['events'][0]['usage']['total_tokens'],50003)
                retained=json.loads((root/'output'/saved['events'][0]['request_artifact']).read_text())
                self.assertEqual(retained['request_sha256'],result['request_sha256'])
                self.assertEqual(retained['response_schema_sha256'],result['response_schema_sha256'])
                original=json.loads((root/'output/response-0001.json').read_text())
                self.assertIn('invalid-boolean',original['original_public_response_text'])
