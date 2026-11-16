"""Deterministic offline split, provenance, GT and failure isolation tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from context_audit import large_benchmark as b
from context_audit.direct_preparation import PreparationError
from context_audit.v2_artifacts import digest
from context_audit.datasets.dappscan import DAppSCAN
from test_direct_discovery import prepared


def row(project,name,tokens):
    return {'file':project+'/'+name+'.sol','project':project,'_tokens':tuple(tokens),'token_sha256':digest(tuple(tokens))}

OPTIONS=dict(max_source_bytes=40000,max_functions=30,max_summary_functions=80,max_batches=4,
             max_per_project=3,timeout_seconds=10,development_percent=20,validation_percent=20,
             near_duplicate_threshold=.85,seed='test')

class SplittingTests(unittest.TestCase):
    def test_deterministic_groups_under_input_order(self):
        rows=[row('Audit-Alpha','One',['a']*10),row('Audit-Beta','Two',['b']*10)]
        g,_=b.grouped_splits(rows,set(),'fixed');other=copy.deepcopy(list(reversed(rows)))
        g2,_=b.grouped_splits(other,set(),'fixed')
        self.assertEqual(g,g2);self.assertEqual({r['file']:r['split'] for r in rows},{r['file']:r['split'] for r in other})
    def test_exact_source_duplicate_cannot_cross_split(self):
        rows=[row('Audit-Alpha','One',['a','b']),row('Audit-Beta','Two',['a','b'])]
        groups,links=b.grouped_splits(rows,{'Audit-Alpha'},'fixed')
        self.assertEqual({r['split'] for r in rows},{'development'})
        self.assertEqual(rows[0]['source_group'],rows[1]['source_group']);self.assertEqual(links[0]['similarity'],1)
    def test_near_source_variants_group_with_historical_project(self):
        a=tuple(str(i) for i in range(150));c=list(a);c[75]='changed'
        rows=[row('Audit-Alpha','One',a),row('Audit-Beta','Two',c)]
        _,links=b.grouped_splits(rows,{'Audit-Alpha'},'fixed')
        self.assertEqual({r['split'] for r in rows},{'development'})
        self.assertTrue(any(l['reason']=='near_source_tokens' for l in links))
    def test_normalized_project_versions_group_without_shared_source(self):
        rows=[row('Vendor-MyProtocol v1.0 signed','One',['a']),row('Other-MyProtocol v2.0','Two',['b'])]
        groups,_=b.grouped_splits(rows,{'Vendor-MyProtocol v1.0 signed'},'fixed')
        self.assertEqual(len(groups),1);self.assertEqual({r['split'] for r in rows},{'development'})
    def test_comments_ignored_but_string_whitespace_preserved(self):
        self.assertEqual(b.source_tokens('uint x; // SWC-104 label'),b.source_tokens('uint x;'))
        self.assertNotEqual(b.source_tokens('"a b"'),b.source_tokens('"ab"'))
    def test_history_scan_follows_real_source_paths_and_skips_audit_universe(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'manifest.json').write_text(json.dumps({'cases':[{'source':'/data/contracts/Audit-Alpha/code.sol'}]}))
            (root/'screening_universe.json').write_text(json.dumps({'file':'Audit-Beta/code.sol'}))
            history,evidence=b.history_projects([root],{'Audit-Alpha','Audit-Beta'})
            self.assertEqual(history,{'Audit-Alpha'});self.assertEqual(len(evidence),1)
    def test_unrelated_files_in_one_project_never_cross_split(self):
        rows=[row('Audit-Alpha','One',['a']),row('Audit-Alpha','Two',['b'])]
        b.grouped_splits(rows,set(),'fixed');self.assertEqual(rows[0]['split'],rows[1]['split'])

    def test_history_path_matching_preserves_original_reference_semantics(self):
        known={'Vendor-Alpha','Other-Beta (v2)','Audit-Žeta'}
        values=['Vendor-Alpha/x.sol','/root/Other-Beta (v2)/x.sol','text /Audit-Žeta/a.sol',
                'prefixVendor-Alpha/x.sol','Vendor-Alpha','/Vendor-Alpha/Other-Beta (v2)/x.sol']
        expected={p for p in known for value in values if value==p or value.startswith(p+'/') or '/'+p+'/' in value}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'manifest.json').write_text(json.dumps(values))
            actual,_=b.history_projects([root],known)
        self.assertEqual(actual,expected)

    def test_unapproved_large_preparation_proposal_is_not_historical_exposure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'manifest.json').write_text(json.dumps({'purpose':'Large Mode B v2 preparation proposal only; no live execution authorization',
                'approval_required':True,'cases':[{'source':'/data/contracts/Audit-Alpha/code.sol'}]}))
            history,evidence=b.history_projects([root],{'Audit-Alpha'})
        self.assertEqual(history,set());self.assertEqual(evidence,{})

class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def dataset(self):
        root=self.root/'data';source=root/'contracts/Audit-Alpha/code.sol';source.parent.mkdir(parents=True)
        source.write_text('pragma solidity ^0.8.0; contract A { function f() public {} }')
        report=root/'SWCsource/Audit-Alpha/code.json';report.parent.mkdir(parents=True)
        report.write_text(json.dumps({'filePath':'Audit-Alpha/code.sol','SWCs':[{'category':'SWC-104-Test','function':'f','lineNumber':'L1'}]}))
        return DAppSCAN(root),source
    def test_inventory_reuses_loader_and_is_complete(self):
        ds,_=self.dataset();rows,reports=b.inventory(ds)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['labels'],ds.labels('Audit-Alpha/code.sol'))
        self.assertEqual(len(reports),1);self.assertIn('source_sha256',rows[0])
    def test_size_limit_avoids_compiler_and_dependency_access(self):
        ds,_=self.dataset();rows,_=b.inventory(ds)
        with patch.object(b,'dependency_graph',side_effect=AssertionError('Not needed')):
            r=b.prepare_one(ds,rows[0],self.root,{**OPTIONS,'max_source_bytes':1})
        self.assertEqual(r['status'],'SOURCE_SIZE_LIMIT')
    def test_missing_dependency_recorded_without_download_or_worker(self):
        ds,_=self.dataset();rows,_=b.inventory(ds)
        with patch.object(b,'dependency_graph',side_effect=PreparationError('MISSING_DEPENDENCY','Missing local package')),patch.object(b.subprocess,'Popen') as process:
            r=b.prepare_one(ds,rows[0],self.root,OPTIONS)
        self.assertEqual(r['status'],'MISSING_DEPENDENCY');process.assert_not_called()
    def test_missing_compiler_recorded_without_substitution(self):
        ds,source=self.dataset();rows,_=b.inventory(ds)
        with patch.object(b,'compatible_compilers',return_value=[]),patch.object(b.subprocess,'Popen') as process:
            r=b.prepare_one(ds,rows[0],self.root,OPTIONS)
        self.assertEqual(r['status'],'COMPILER_VERSION_UNAVAILABLE');process.assert_not_called()
    def test_fatal_failure_leaves_no_final_or_staging_artifacts(self):
        ds,_=self.dataset();output=self.root/'final'
        with patch.object(b,'prepare_one',side_effect=RuntimeError('unexpected bug')):
            with self.assertRaises(RuntimeError):b.publish(ds.root,output,OPTIONS,[])
        self.assertFalse(output.exists());self.assertEqual(list(self.root.glob('.large-benchmark-staging-*')),[])
    def test_existing_output_never_overwritten(self):
        ds,_=self.dataset();output=self.root/'existing';output.mkdir();(output/'keep').write_text('original')
        with self.assertRaises(ValueError):b.publish(ds.root,output,OPTIONS,[])
        self.assertEqual((output/'keep').read_text(),'original')
    def test_worker_preserves_unknown_and_sanitizes_without_api(self):
        source,contracts,catalog=prepared(self.root)
        output=self.root/'result.json'
        with patch('openai.OpenAI.__init__',side_effect=AssertionError('No API')):
            b.worker(source,output,30,80,4,catalog.preparation_metadata['compiler_used'])
        result=json.loads(output.read_text())
        self.assertEqual(result['structural']['usage']['api_calls'],0)
        self.assertNotIn('SWC-107',json.dumps(result))
        self.assertEqual(result['source_identity'],catalog.source_identity)
    def test_resolved_overload_ambiguous_and_contradictory_gt(self):
        source,contracts,catalog=prepared(self.root)
        function=next(f for c in contracts if c['contract']=='Vault' for f in c['functions'] if f['signature']=='withdraw(uint256)')
        base={'function':'withdraw(uint256)','lines':function['lines'],'raw':{}}
        self.assertEqual(b.resolve_gt([base],contracts,catalog,source)[0]['status'],'RESOLVED')
        ambiguous={**base,'function':'withdraw','lines':[]}
        self.assertEqual(b.resolve_gt([ambiguous],contracts,catalog,source)[0]['status'],'AMBIGUOUS')
        contradiction={**base,'lines':[],'raw':{'lineNumber':'L900 - L901'}}
        self.assertEqual(b.resolve_gt([contradiction],contracts,catalog,source)[0]['status'],'CONTRADICTORY')

    def test_worker_preserves_source_fallback_unknown_relationships(self):
        from slither.core.declarations import Function
        source,contracts,catalog=prepared(self.root);original=Function.generate_slithir_and_analyze
        def fail(function):
            if function.name=='withdraw':raise ValueError('Mock unavailable IR')
            return original(function)
        output=self.root/'fallback.json'
        with patch.object(Function,'generate_slithir_and_analyze',fail):
            b.worker(source,output,30,80,4,catalog.preparation_metadata['compiler_used'])
        result=json.loads(output.read_text())
        functions=[f for c in result['contracts'] for f in c['functions'] if f['signature'].startswith('withdraw')]
        self.assertTrue(functions)
        self.assertTrue(all(f['preparation_mode']=='SOURCE_FALLBACK' and f['state_reads'] is None and f['internal_calls'] is None for f in functions))
    def test_worker_function_limit_is_reported_without_discarding_summary(self):
        source,contracts,catalog=prepared(self.root);output=self.root/'limited.json'
        b.worker(source,output,1,80,4,catalog.preparation_metadata['compiler_used'])
        result=json.loads(output.read_text());self.assertEqual(result['status'],'FUNCTION_LIMIT')
        self.assertTrue(result['structural']['coverage'])
    def test_atomic_publish_with_complete_exclusion_audit(self):
        ds,_=self.dataset();output=self.root/'audit'
        with patch.object(b,'prepare_one',return_value={'status':'COMPILER_VERSION_UNAVAILABLE','blocker':'Missing compiler'}):
            audit=b.publish(ds.root,output,OPTIONS,[])
        self.assertEqual(audit['total_labelled_files'],1)
        self.assertEqual(audit['status_counts']['COMPILER_VERSION_UNAVAILABLE'],1)
        self.assertTrue((output/'manifest.json').is_file());self.assertTrue((output/'blockers.json').is_file())
        self.assertEqual(list(self.root.glob('.large-benchmark-staging-*')),[])

    def test_worker_never_substitutes_a_different_pinned_compiler(self):
        source,contracts,catalog=prepared(self.root);output=self.root/'wrong-compiler.json'
        with self.assertRaisesRegex(ValueError,'PINNED_COMPILER_CHANGED'):
            b.worker(source,output,30,80,4,'0.0.0')
        self.assertFalse(output.exists())
    def test_source_changed_during_preparation_aborts(self):
        from unittest.mock import MagicMock
        ds,source=self.dataset();rows,_=b.inventory(ds)
        process=MagicMock();process.returncode=0
        def start(command,**kwargs):
            result=Path(command[command.index('--result')+1]);compiler=command[command.index('--compiler')+1]
            result.write_text(json.dumps({'metadata':{'compiler_used':compiler}}))
            source.write_text(source.read_text()+'\n// concurrent edit')
            process.communicate.return_value=('','');return process
        with patch.object(b.subprocess,'Popen',side_effect=start),self.assertRaisesRegex(RuntimeError,'SOURCE_CHANGED'):
            b.prepare_one(ds,rows[0],self.root,OPTIONS)

    def cache_fixture(self):
        from types import SimpleNamespace
        source,contracts,catalog=prepared(self.root)
        result=self.root/'worker-result.json'
        b.worker(source,result,30,80,4,catalog.preparation_metadata['compiler_used'])
        data=json.loads(result.read_text());cache=self.root/'cache';file='Fixture.sol'
        folder=cache/'prepared'/digest(file)[:20];folder.mkdir(parents=True)
        (folder/'structure.json').write_text(json.dumps(data['structural']))
        (folder/'provenance.json').write_text(json.dumps({k:v for k,v in data.items() if k not in ('structural','contracts')}))
        return cache,SimpleNamespace(source_path=lambda _:source),{'file':file},data,source
    def test_interrupted_cache_revalidated_and_unknown_binary_hash_remains_unknown(self):
        cache,ds,row,data,source=self.cache_fixture()
        restored,proof=b.restore_preparation(cache,ds,row,self.root/'unused',data['metadata']['compiler_used'],OPTIONS)
        self.assertEqual(restored['source_identity'],data['source_identity'])
        self.assertTrue(proof['validated']);self.assertIsNone(proof['original_compiler_binary_sha256'])
    def test_interrupted_cache_source_mismatch_is_fatal(self):
        cache,ds,row,data,source=self.cache_fixture()
        source.write_text(source.read_text()+'\n// changed after cache')
        with self.assertRaisesRegex(RuntimeError,'CACHE_PROVENANCE_MISMATCH'):
            b.restore_preparation(cache,ds,row,self.root/'unused',data['metadata']['compiler_used'],OPTIONS)

    def test_interface_only_source_remains_unevaluable(self):
        source=self.root/'Interface.sol';source.write_text('pragma solidity ^0.8.0; interface I { function f() external; }')
        from context_audit import direct_discovery as d
        _,catalog=d.prepare(source);output=self.root/'interface.json'
        b.worker(source,output,30,80,4,catalog.preparation_metadata['compiler_used'])
        result=json.loads(output.read_text())
        self.assertEqual(result['metadata']['preparation_status'],'NO_ANALYZABLE_FUNCTIONS')
        self.assertEqual(result['status'],'UNEVALUABLE')
