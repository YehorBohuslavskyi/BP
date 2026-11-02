"""Compiler-mapping based recovery after individual IR failures, without APIs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from slither.core.declarations import Function
from context_audit.direct import prepare, run_function, safe_source
from context_audit.direct_evaluation import evaluate


class FunctionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.source=self.root/'C.sol'
        self.text='''pragma solidity ^0.4.25;
contract C {
 uint x=1;
 // SWC-107-Reentrancy: L5-6
 function broken() public { x=2; }
 function good() public view returns(uint) { return x; }
}'''
        self.source.write_text(self.text)

    def prepare_failure(self):
        original=Function.generate_slithir_and_analyze
        def analyze(function):
            if function.name=='broken':
                raise AttributeError('IR failure')
            return original(function)
        with patch.object(Function,'generate_slithir_and_analyze',analyze):
            return prepare(self.source)

    def test_isolated_ir_failure_and_partial_readiness(self):
        payloads,catalog=self.prepare_failure()
        modes={p['target']['signature']:p['target']['preparation_mode'] for p in payloads}
        self.assertEqual(modes,{'broken()':'SOURCE_FALLBACK','good()':'FULL_INDEX'})
        self.assertEqual(catalog.preparation_metadata['preparation_status'],'PARTIALLY_READY')
        self.assertEqual(catalog.preparation_metadata['FULL_INDEX'],1)
        self.assertEqual(catalog.preparation_metadata['SOURCE_FALLBACK'],1)
        self.assertEqual(self.source.read_text(),self.text)

    def test_fallback_metadata_and_multiround_isolation(self):
        payloads,catalog=self.prepare_failure()
        payload=next(p for p in payloads if p['target']['signature']=='broken()')
        self.assertNotIn('state_reads',payload['target'])
        self.assertNotIn('state_writes',payload['target'])
        self.assertTrue(payload['target']['lines'])
        self.assertEqual(payload['target']['visibility'],'public')
        responses=iter([{'action':'request_context','requested_ids':[p['id'] for p in payload['available_context']]}, {'action':'final','verdict':'no_vulnerability_found'}])
        result=run_function(payload,catalog,self.root/'r.json',analyze_fn=lambda *_:{'assessment':next(responses)})
        self.assertEqual(result['round_count'],2)
        self.assertFalse(result['errors'])
        journal=json.dumps(result['prompt_journal'])
        self.assertNotIn('SWC-107',journal); self.assertNotIn('Reentrancy',journal)
        self.assertNotIn('slitherConstructor',json.dumps(catalog.to_dict()))
        self.assertIn('function good()',journal)

    def test_unsafe_mapping_unevaluable(self):
        def safe(element):
            return element.name!='broken' and safe_source(element)
        with patch('context_audit.direct.safe_source',side_effect=safe):
            payloads,catalog=self.prepare_failure()
        self.assertEqual(len(payloads),1)
        self.assertEqual(catalog.preparation_metadata['UNEVALUABLE'],1)
        self.assertEqual(catalog.preparation_metadata['preparation_status'],'PARTIALLY_READY')

    def test_partial_file_evaluation_uses_actual_function(self):
        payloads,catalog=self.prepare_failure()
        results=[]
        for i,payload in enumerate(payloads):
            r=run_function(payload,catalog,self.root/f'{i}.json',analyze_fn=lambda *_:{'assessment':{'action':'final','verdict':'no_vulnerability_found'}})
            r['dataset_file']='C.sol';results.append(r)
        case={'file':'C.sol','preparation_status':'PARTIALLY_READY','labels':[{'function':'broken()','swc_id':'SWC-107'},{'function':'missing()','swc_id':'SWC-107'}]}
        report=evaluate([case],results)
        self.assertEqual([l['status'] for l in report['labels']],['MISSED','UNEVALUABLE'])
        self.assertEqual(report['labels'][0]['target_preparation_modes'],['SOURCE_FALLBACK'])
