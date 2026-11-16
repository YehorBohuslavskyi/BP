"""Offline recovery, dataset execution/resume and strict post-inference scoring."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from context_audit import v2_dataset as runner
from context_audit import v2_dataset_scoring as scoring
from context_audit.discovery_recovery import build_import,validate_import
from context_audit import direct_discovery as d
from context_audit.v2_artifacts import validate_discovery
from context_audit.v2_pipeline import run_verification,groups_for
from test_direct_verification import final
from test_v2_verification_failures import envelope

MODEL='gpt-5.4-mini-2026-03-17'
RECOVERY=Path('experiments/mode-b-v2-identity-fix-2026-11-09/offline_reprocessing.json')
SOURCE=Path(json.loads(Path('experiments/mode-b-v2-development-2026-11-09/prepared/ixo-authoriser/b2-plan.json').read_text())['source'])

class RecoveryDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts,cls.catalog=d.prepare(SOURCE)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        from current_protocol_fixtures import recovery_fixture
        self.recovery=recovery_fixture(self.root/'fixture',self.contracts,self.catalog,MODEL)
    def changed(self,key,value):
        data=json.loads(self.recovery.read_text());data[key]=value
        path=self.root/'recovery.json';path.write_text(json.dumps(data));return path
    def test_recovery_three_candidates_and_audit(self):
        x=build_import(self.recovery,self.contracts,self.catalog,MODEL)
        self.assertEqual(len(x['candidates']),3);self.assertNotIn('manifest',x)
        self.assertEqual(len(groups_for(x['candidates'])),3)
        self.assertEqual(x['usage']['total_tokens'],2945)
        self.assertEqual(len(x['recovery_import']['identity_audit']),3)
    def test_default_pipeline_cannot_silently_import(self):
        x=build_import(self.recovery,self.contracts,self.catalog,MODEL)
        with self.assertRaises(ValueError):validate_discovery(x,self.contracts,self.catalog)
    def test_recovery_source_tampering(self):
        path=self.changed('current_source_identity',{})
        with self.assertRaises(ValueError):build_import(path,self.contracts,self.catalog,MODEL)
    def test_recovery_original_hash_tampering(self):
        path=self.changed('source_artifact_sha256','bad')
        with self.assertRaises(ValueError):build_import(path,self.contracts,self.catalog,MODEL)
    def test_recovery_audit_tampering(self):
        path=self.changed('candidate_validation',[])
        with self.assertRaises(ValueError):build_import(path,self.contracts,self.catalog,MODEL)
    def test_recovery_candidate_tampering(self):
        path=self.changed('accepted_candidates',[])
        with self.assertRaises(ValueError):build_import(path,self.contracts,self.catalog,MODEL)
    def test_recovery_model_tampering(self):
        with self.assertRaises(ValueError):build_import(self.recovery,self.contracts,self.catalog,'other')
    def test_import_content_tampering(self):
        x=build_import(self.recovery,self.contracts,self.catalog,MODEL);x['candidates']=[]
        with self.assertRaises(ValueError):validate_import(x,self.recovery,self.contracts,self.catalog,MODEL)
    def test_explicit_verifier_import_and_resume(self):
        x=build_import(self.recovery,self.contracts,self.catalog,MODEL)
        with patch.dict(os.environ,{'OPENAI_MODEL':MODEL}):
            r=run_verification(x,self.contracts,self.catalog,self.root/'analysis',recovery_path=self.recovery,analyze_fn=lambda p,s,**kw:final(p,s))
            self.assertEqual(r['coverage_counts']['confirmed_candidates'],3)
            r2=run_verification(x,self.contracts,self.catalog,self.root/'analysis',recovery_path=self.recovery,resume=True,
                analyze_fn=lambda *a,**k:self.fail('completed result replayed'))
            self.assertEqual(r2['efficiency']['verification_this_invocation']['api_calls'],0)
    def test_execution_has_zero_discovery_and_completed_resume_zero_calls(self):
        case=runner.case_plan(SOURCE,MODEL,self.root/'run',self.recovery);case.update(id='one',cohort='development')
        client=MagicMock();client.responses.input_tokens.count.return_value=SimpleNamespace(input_tokens=100)
        def generate(**kw):
            p=json.loads(kw['input'][1]['content']);fid=p['target']['id']
            from consistency_fixtures import with_basis
            return envelope(json.dumps(with_basis({'action':'final','requested_ids':[],'verdict':'inconclusive','severity':None,
                'explanation':'Mock unavailable external behavior','evidence_ids':[fid],'execution_flow':[],
                'incomplete_evidence':['Missing external behavior']},[p['target']])))
        client.responses.create.side_effect=generate
        manifest={'configuration':runner.identity(),'output':str(self.root),'cases':[case],
            'cohort_budgets':{'development':{k:case['budget'][k] for k in ('max_generation_calls','max_count_calls','max_reserved_tokens')}}}
        with patch.dict(os.environ,{'OPENAI_MODEL':MODEL,'OPENAI_API_KEY':'offline-placeholder','OPENAI_BASE_URL':'https://api.openai.com/v1'}),patch.object(d,'analyze',side_effect=AssertionError('Discovery forbidden')):
            runner.execute_cohort(manifest,'development',client_factory=lambda **kw:client)
            ledger=json.loads((Path(case['output'])/'budget_ledger.json').read_text())
            self.assertEqual(ledger['discovery_calls'],0);self.assertEqual(ledger['generation_calls'],3)
            runner.execute_cohort(manifest,'development',resume=True,client_factory=lambda **kw:self.fail('API on completed resume'))
            self.assertEqual(client.responses.create.call_count,3)
    def test_cohort_budget_mismatch_before_api(self):
        case=runner.case_plan(SOURCE,MODEL,self.root/'run',self.recovery);case.update(id='one',cohort='development')
        m={'configuration':runner.identity(),'cases':[case],'cohort_budgets':{'development':dict(max_generation_calls=0)}}
        with self.assertRaises(ValueError):runner.execute_cohort(m,'development')

    def test_historical_recovery_stays_rejected_under_new_index(self):
        with self.assertRaisesRegex(ValueError,'RECOVERY_SOURCE_OR_CATALOG_MISMATCH'):
            build_import(RECOVERY,self.contracts,self.catalog,MODEL)

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.location={'file':'File.sol','lines':[10,11]}
        self.target={'contract':'C','signature':'f()','fragment_id':'fragment-f','location':self.location}
        self.labels=[{'label_id':'L','swc_id':'SWC-104','targets':[self.target],'original_label':{}}]
        self.report={'coverage_counts':{},'discovery_errors':[],
            'contracts':[{'coverage':[{'contract':'C','fragment_id':'fragment-f','status':'not_selected'}]}],'issues':[]}
    def confirmed(self):
        self.report['issues']=[{'issue_id':'I','result':{'candidate':{'contract':'C','primary_fragment_id':'fragment-f'},
            'status':'completed','verdict':'confirmed','evidence_ids':['fragment-f'],'source_locations':{'fragment-f':self.location}}}]
    def status(self,assignments=None):return scoring.score_labels(self.labels,self.report,assignments or {})[0]['status']
    def test_unselected_completed_discovery_is_miss(self):self.assertEqual(self.status(),'MISSED')
    def test_processing_failure_not_miss(self):
        self.report['coverage_counts']['processing_failures']=1;self.assertEqual(self.status(),'INCONCLUSIVE')
    def test_discovery_failure_not_miss(self):
        self.report['discovery_errors']=[{}];self.assertEqual(self.status(),'INCONCLUSIVE')
    def test_skipped_candidate_not_miss(self):
        self.report['coverage_counts']['skipped_candidates']=1;self.assertEqual(self.status(),'INCONCLUSIVE')
    def test_no_inference_not_miss(self):self.assertEqual(scoring.score_labels(self.labels,None,{})[0]['status'],'INCONCLUSIVE')
    def test_unresolved_gt_unevaluable(self):
        self.labels[0]['targets']=[];self.assertEqual(self.status(),'UNEVALUABLE')
    def test_confirmed_type_requires_review(self):
        self.confirmed();self.assertEqual(self.status(),'INCONCLUSIVE')
    def test_exact_grounded_match(self):
        self.confirmed();self.assertEqual(self.status({'I':{'swc_id':'SWC-104','rationale':'Reviewed return handling','gt_match_reviewed':True,'matched_label_ids':['L'],'match_rationale':'Same unchecked call at target location'}}),'DETECTED')
    def test_broad_type_without_location_cannot_hit(self):
        self.confirmed();self.report['issues'][0]['result']['source_locations']={}
        self.assertNotEqual(self.status({'I':{'swc_id':'SWC-104','rationale':'Review'}}),'DETECTED')
    def test_other_contract_cannot_hit(self):
        self.confirmed();self.report['issues'][0]['result']['candidate']['contract']='Other'
        self.assertNotEqual(self.status({'I':{'swc_id':'SWC-104','rationale':'Review'}}),'DETECTED')
    def test_wrong_swc_no_hit(self):
        self.confirmed();self.assertEqual(self.status({'I':{'swc_id':'SWC-107','rationale':'Review'}}),'MISSED')
    def test_denominators(self):
        m=scoring.metrics([{'status':s} for s in ['DETECTED','MISSED','INCONCLUSIVE','UNEVALUABLE']])
        self.assertAlmostEqual(m['strict_recall'],1/3);self.assertEqual(m['conclusive_only_recall'],.5)
        self.assertEqual(m['evaluation_coverage'],.75)

class AggregationTests(unittest.TestCase):
    def test_partial_ledger_usage_included_without_final_report(self):
        usage=scoring.actual_usage({'partial':{'generation_calls':2,'count_calls':2,'events':[
            {'usage':{'input_tokens':100,'output_tokens':20,'total_tokens':120}},
            {'status':'generation_outcome_unknown'}]}})
        self.assertEqual(usage['total_tokens'],120);self.assertEqual(usage['generation_calls'],2)
        self.assertEqual(usage['unknown_generation_usage'],1)
    def test_overall_and_swc_aggregation_no_automatic_precision(self):
        manifest={'cases':[{'id':'one','cohort':'held_out','coverage':[], 'preparation':{'FULL_INDEX':1}}]}
        evaluation={'one':{'labels':[{'label_id':'L','swc_id':'SWC-107','targets':[{'contract':'C'}],'original_label':{}}]}}
        summary=scoring.summarize(manifest,evaluation,{})
        self.assertEqual(summary['metrics']['inconclusive'],1)
        self.assertEqual(summary['per_swc']['SWC-107']['strict_recall'],0)
        self.assertIsNone(summary['manual_precision_decided_only'])

class CohortControlTests(unittest.TestCase):
    def run_mock(self,partial=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        cases=[{'id':name,'cohort':cohort,'output':str(root/name),'budget':{'max_generation_calls':1,'max_count_calls':1,'max_reserved_tokens':100}}
            for name,cohort in [('dev-a','development'),('dev-b','development'),('held','held_out')]]
        manifest={'configuration':runner.identity(),'output':str(root),'cases':cases,
            'cohort_budgets':{'development':{'max_generation_calls':2,'max_count_calls':2,'max_reserved_tokens':200}}}
        report={'discovery_errors':[{}] if partial else [],'coverage_counts':{'processing_failures':0,'skipped_candidates':0,'pending_candidates':0},'transport_this_run':{'stopped':False}}
        with patch.object(runner,'preflight_case'),patch.object(runner,'execute_case',return_value=report) as execute:
            result=runner.execute_cohort(manifest,'development')
        return result,execute
    def test_development_never_continues_to_held_out(self):
        result,execute=self.run_mock()
        self.assertEqual(execute.call_count,2)
        self.assertEqual([r['case'] for r in result],['dev-a','dev-b'])
    def test_processing_failure_stops_before_next_contract(self):
        result,execute=self.run_mock(partial=True)
        self.assertEqual(execute.call_count,1);self.assertEqual(result[0]['status'],'partial')

class ApprovalScopeTests(unittest.TestCase):
    def test_development_checksum_cannot_authorize_held_out(self):
        import runpy,sys
        from context_audit.v2_artifacts import digest
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'manifest.json';manifest={'model':'mock'};path.write_text(json.dumps(manifest))
            approval=digest({'manifest_sha256':digest(manifest),'cohort':'development'})
            argv=['run_v2_dataset.py','execute','--manifest',str(path),'--cohort','held_out',
                  '--approved-plan-sha256',approval,'--run']
            with patch.object(sys,'argv',argv),patch.object(runner,'execute_cohort') as execute:
                with self.assertRaises(SystemExit) as exc:runpy.run_path('scripts/run_v2_dataset.py',run_name='__main__')
            self.assertEqual(exc.exception.code,2);execute.assert_not_called()
