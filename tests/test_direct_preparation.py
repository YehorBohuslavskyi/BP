"""Offline regression tests for annotation isolation and coverage accounting."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from context_audit.direct import prepare, run_function
from context_audit.direct_preparation import sanitize_source, staged_source, PreparationError
from context_audit.direct_evaluation import evaluate


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_annotation_sanitizer_preserves_comments_strings_and_offsets(self):
        source = '// Developer explanation\n// SWC-107-Reentrancy: L3-4\n/* SWC 114 Transaction Order Dependence: L5 */\n// Reentrancy: L7-8\nstring x = "SWC-107"; // ordinary\n'
        clean = sanitize_source(source)
        self.assertIn('// Developer explanation', clean)
        self.assertIn('// ordinary', clean)
        self.assertIn('"SWC-107"', clean)
        self.assertNotIn('Reentrancy', clean)
        self.assertNotIn('Transaction Order Dependence', clean)
        self.assertEqual(len(source.encode()), len(clean.encode()))
        self.assertEqual(source.count('\n'), clean.count('\n'))
        self.assertEqual(clean, sanitize_source(clean))

    def test_real_fragments_and_multiround_prompts(self):
        path = self.root/'C.sol'
        source = '''pragma solidity ^0.4.25;
// SWC-107-Reentrancy: L3-9
contract C {
 uint x = 1;
 // SWC 114 Transaction Order Dependence: L6-8
 function f() public { x = 2; }
 /* SWC-104-Unchecked Call Return Value: L8 */
 function g() public view returns(uint) { return x; }
}'''
        path.write_text(source)
        payloads, catalog = prepare(path)
        self.assertEqual(path.read_text(), source)
        self.assertFalse(any('slitherConstructor' in f['name'] for f in catalog.fragments.values()))
        self.assertEqual(len(payloads), 2)
        payload = payloads[0]
        responses = iter([{'action': 'request_context', 'requested_ids': [x['id'] for x in payload['available_context']]}, {'action': 'final', 'verdict': 'no_vulnerability_found'}])
        result = run_function(payload, catalog, self.root/'r.json', analyze_fn=lambda *_: {'assessment': next(responses)})
        self.assertEqual(result['round_count'], 2)
        serialized = json.dumps([catalog.to_dict(), result['prompt_journal']])
        for annotation in ('SWC-107', 'SWC 114', 'SWC-104', 'Reentrancy', 'Transaction Order Dependence', 'Unchecked Call Return Value', 'slitherConstructorVariables'):
            self.assertNotIn(annotation, serialized)

    def test_missing_compiler_explicit_and_global_state_unchanged(self):
        path = self.root/'C.sol'; path.write_text('pragma solidity 0.8.11; contract C {}')
        before = dict(os.environ)
        with patch('context_audit.direct_preparation.compatible_compilers', return_value=[]):
            with self.assertRaises(PreparationError) as caught:
                with staged_source(path):
                    self.fail('Should not stage with incompatible compiler')
        self.assertEqual(caught.exception.metadata['preparation_status'], 'COMPILER_VERSION_UNAVAILABLE')
        self.assertIsNone(caught.exception.metadata['compiler_used'])
        self.assertEqual(dict(os.environ), before)

    def test_missing_dependency(self):
        path=self.root/'C.sol'; path.write_text('pragma solidity ^0.4.25; import "@openzeppelin/contracts/Missing.sol"; contract C {}')
        with self.assertRaises(PreparationError) as caught:
            prepare(path)
        self.assertEqual(caught.exception.metadata['preparation_status'], 'MISSING_DEPENDENCY')

    def test_local_import_sanitized_and_compiles(self):
        (self.root/'D.sol').write_text('pragma solidity ^0.4.25; /* SWC-107-Reentrancy: L1 */ contract D { uint x; }')
        path=self.root/'C.sol'; path.write_text('pragma solidity ^0.4.25; import "./D.sol"; contract C is D { function f() public { x=1; } }')
        payloads, catalog=prepare(path)
        self.assertEqual(len(payloads), 1)
        self.assertNotIn('SWC', json.dumps(catalog.to_dict()))

    def test_preparation_coverage_cli(self):
        spec=importlib.util.spec_from_file_location('runner','scripts/run_dappscan_direct_detection.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        folder=self.root/'contracts'/'p';folder.mkdir(parents=True)
        (folder/'C.sol').write_text('pragma solidity 0.8.11; contract C {}')
        output=io.StringIO()
        with patch.object(runner,'prepare',side_effect=PreparationError('COMPILER_VERSION_UNAVAILABLE','Unavailable')), patch.object(runner,'run_function',side_effect=AssertionError('No API calls')), contextlib.redirect_stdout(output):
            runner.main(['--dataset-root',str(self.root),'--project','p','--prepare','--output',str(self.root/'out')])
        self.assertIn('Selected files: 1\nReady files: 0\nFailed preparation: 1\nFunction sessions: 0', output.getvalue())
        case=json.loads((self.root/'out'/'prepared_targets.json').read_text())['cases'][0]
        self.assertEqual(case['preparation_status'],'COMPILER_VERSION_UNAVAILABLE')
        self.assertEqual(case['session_count'],0)

    def test_unevaluable_coverage_and_recall(self):
        cases=[]
        for i,status in enumerate(['COMPILER_VERSION_UNAVAILABLE','MISSING_DEPENDENCY','COMPILATION_FAILED','READY','READY','READY']):
            cases.append({'file':str(i),'preparation_status':status,'labels':[{'swc_id':'SWC-107','function':'f()'}]})
        results=[]
        for i,verdict in [(3,'inconclusive'),(4,'no_vulnerability_found'),(5,'vulnerable')]:
            results.append({'dataset_file':str(i),'target':{'id':str(i),'signature':'f()'},'assessment':{'verdict':verdict,'findings':[{'swc_id':'SWC-107'}] if i==5 else []},'round_count':1,'requested_fragments':0,'usage':{'total_tokens':0}})
        with patch('context_audit.direct_evaluation.aggregate',return_value=[]):
            report=evaluate(cases,results)
        self.assertEqual([x['status'] for x in report['labels']],['UNEVALUABLE']*3+['INCONCLUSIVE','MISSED','DETECTED'])
        self.assertEqual(report['metrics']['recall'],1/3)
        self.assertEqual(report['metrics']['evaluation_coverage'],0.5)
        self.assertEqual(report['metrics']['evaluable_labels'],3)
