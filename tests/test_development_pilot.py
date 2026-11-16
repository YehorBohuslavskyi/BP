"""Offline deterministic pilot selection and approval-scope tests."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from context_audit import development_pilot as pilot

ROOT=Path('experiments/mode-b-v2-development-pilot-2026-11-10')

class PilotSelectionTests(unittest.TestCase):
    def fixtures(self):
        cases=[];records=[]
        for i in range(9):
            c={'id':str(i),'split':'development','project':'p'+str(i),'dataset_file':str(i)+'.sol'}
            r={'file':c['dataset_file'],'metadata':{'preparation_status':'READY','total_source_functions':i+1},
               'summary_rows':i+1,'batches':1,'gt_resolution':[{'status':'RESOLVED','label':{'swc_id':'SWC-'+str(100+i%5)}}]}
            cases.append(c);records.append(r)
        return {'cases':cases},records
    def test_selection_is_deterministic_under_input_permutation(self):
        p,r=self.fixtures();a,_=pilot.select_cases(p,r)
        p['cases'].reverse();r.reverse();b,_=pilot.select_cases(p,r)
        self.assertEqual([c['id'] for c in a],[c['id'] for c in b])
    def test_validation_and_held_out_cannot_be_selected(self):
        p,r=self.fixtures();p['cases'][0]['split']='held_out';p['cases'][1]['split']='validation'
        selected,_=pilot.select_cases(p,r)
        self.assertTrue(all(c['split']=='development' for c in selected));self.assertEqual(len(selected),7)
    def test_ambiguous_GT_and_partial_preparation_excluded(self):
        p,r=self.fixtures();r[0]['gt_resolution'][0]['status']='AMBIGUOUS';r[1]['metadata']['preparation_status']='PARTIALLY_READY'
        selected,_=pilot.select_cases(p,r)
        self.assertNotIn('0',[c['id'] for c in selected]);self.assertNotIn('1',[c['id'] for c in selected])
    def test_one_case_per_project(self):
        p,r=self.fixtures();p['cases'][0]['project']=p['cases'][1]['project']
        selected,_=pilot.select_cases(p,r)
        self.assertEqual(len({c['project'] for c in selected}),7)
    def test_security_outcomes_do_not_influence_selection(self):
        p,r=self.fixtures();expected,_=pilot.select_cases(p,r)
        for c in p['cases']:c['previous_verdict']='confirmed' if c['id']=='8' else 'rejected'
        actual,_=pilot.select_cases(p,r)
        self.assertEqual([c['id'] for c in expected],[c['id'] for c in actual])
    def test_insufficient_candidates_stop(self):
        p,r=self.fixtures()
        for c in p['cases']:c['split']='held_out'
        with self.assertRaises(ValueError):pilot.select_cases(p,r)

class FrozenPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen_plan=json.loads((ROOT/'plan.json').read_text())
        # Exercise scope checks under the current implementation without editing
        # or authorizing execution of a historical, checksum-bound plan.
        cls.plan=copy.deepcopy(cls.frozen_plan)
        cls.plan['configuration']=pilot.identity()
        cls.plan['execution']['configuration']=pilot.dataset_identity()
        # A private revised protocol bundle exercises current scope/budget checks;
        # the historical bundle must continue rejecting a changed verifier prompt.
        from context_audit.v2_artifacts import digest,file_hash
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name);(root/'evaluation_only').mkdir()
        original=Path(cls.frozen_plan['parent_manifest'])
        parent=json.loads(original.read_text())
        records=json.loads((original.parent/'evaluation_only/records.json').read_text())
        parent['protocols']['verification']={**pilot.v.configuration(pilot.LIMITS),'model':parent['model']}
        parent['protocols']['discovery']['prompt_sha256']=digest(pilot.d.SYSTEM_PROMPT)
        (root/'manifest.json').write_text(json.dumps(parent))
        (root/'evaluation_only/records.json').write_text(json.dumps(records))
        (root/'bundle_provenance.json').write_text(json.dumps({'manifest_sha256':digest(parent),
            'files_sha256':{'evaluation_only/records.json':file_hash(root/'evaluation_only/records.json')}}))
        cls.plan['parent_manifest']=str(root/'manifest.json')
        cls.plan['parent_manifest_sha256']=file_hash(root/'manifest.json')
        cls.plan['parent_bundle_sha256']=file_hash(root/'bundle_provenance.json')
        selected,_=pilot.select_cases(parent,records)
        # These are scope/approval unit tests with a private revised parent.
        # Keep their reuse input private too: unrelated malformed historical
        # reports must not prevent the scope assertions from running. The real
        # audit still fails closed and is exercised independently below.
        cls.plan['reuse_audit']=copy.deepcopy(cls.frozen_plan['reuse_audit'])
        cls.enterClassContext(patch.object(pilot,'audit_reuse',return_value=cls.plan['reuse_audit']))
    def test_historical_approval_cannot_authorize_changed_implementation(self):
        with patch.object(pilot,'execute_cohort') as run,self.assertRaisesRegex(ValueError,'PILOT_IMPLEMENTATION_CHANGED'):
            pilot.execute(copy.deepcopy(self.frozen_plan))
        run.assert_not_called()
    def test_actual_pilot_matches_deterministic_rule_and_frozen_budgets(self):
        p,r=pilot.validate_parent(self.plan['parent_manifest']);selected,trace=pilot.select_cases(p,r)
        self.assertEqual(trace,self.plan['selection_trace'])
        self.assertEqual([c['id'] for c in selected],[c['id'] for c in self.plan['execution']['cases']])
        self.assertEqual(sum(c['budget']['max_reserved_tokens'] for c in selected),420000)
        self.assertEqual(sum(c['budget']['max_generation_calls'] for c in selected),72)
    def test_execution_invokes_development_cohort_only(self):
        with patch.object(pilot,'execute_cohort',return_value=[]) as call:
            pilot.execute(copy.deepcopy(self.plan))
        call.assert_called_once();self.assertEqual(call.call_args.args[1],'development')
        self.assertEqual(len(call.call_args.args[0]['cases']),7)
        self.assertFalse(call.call_args.kwargs['resume'])
    def test_tampered_budget_rejected_before_runner(self):
        plan=copy.deepcopy(self.plan);plan['execution']['cases'][0]['budget']['max_reserved_tokens']+=1
        with patch.object(pilot,'execute_cohort') as run,self.assertRaisesRegex(ValueError,'FROZEN_CASE_OR_BUDGET_CHANGED'):
            pilot.execute(plan)
        run.assert_not_called()
    def test_reuse_state_change_blocks_before_runner(self):
        with patch.object(pilot,'audit_reuse',return_value=[{'unexpected_selected_result':True}]),patch.object(pilot,'execute_cohort') as run:
            with self.assertRaisesRegex(ValueError,'REUSE_STATE_CHANGED'):pilot.execute(copy.deepcopy(self.plan))
        run.assert_not_called()
    def test_plan_only_new_development_outputs_no_historical_replay(self):
        self.assertFalse(any(r['matched_selected_cases'] for r in self.frozen_plan['reuse_audit']))
        root=Path(self.plan['execution']['output'])
        for c in self.plan['execution']['cases']:
            self.assertEqual(Path(c['output']).parent,root);self.assertIsNone(c['recovery_path'])
            self.assertEqual(c['split'],'development')
    def test_tampered_model_rejected_before_runner(self):
        plan=copy.deepcopy(self.plan);plan['execution']['cases'][0]['model']='different-model'
        with patch.object(pilot,'execute_cohort') as run,self.assertRaisesRegex(ValueError,'FROZEN_MODEL_CHANGED'):
            pilot.execute(plan)
        run.assert_not_called()


class ReuseIntegrityTests(unittest.TestCase):
    def test_malformed_historical_report_is_never_silently_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json'
            path.write_text('{"mode":"direct_detection_v2"} trailing data')
            with patch.object(Path,'rglob',return_value=[path]):
                with self.assertRaises(json.JSONDecodeError):
                    pilot.audit_reuse([])
