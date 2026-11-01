"""Offline accounting/leakage checks; never invoke model or alter research files."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('fp_cohort',Path(__file__).resolve().parents[1]/'scripts/run_defihacklabs_fp_cohort.py')
module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)

class FrozenFindingWorkflowTests(unittest.TestCase):
    def test_configuration_missing_prevents_worker(self):
        with patch.object(module,'verify_freeze'),patch.dict(module.os.environ,{},clear=True),patch.object(module.subprocess,'run') as worker:
            with self.assertRaisesRegex(AssertionError,'Set OPENAI_API_KEY'):
                module.run()
            worker.assert_not_called()

    def test_metrics_include_all_frozen_findings_and_abstentions(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);results=base/'results';results.mkdir()
            cohort_path=base/'cohort.json';cohort_path.write_text('{}')
            targets=base/'targets.json'
            rows=[dict(target_id=str(n),case='fixture',finding_id=str(n),detector='fixture',ground_truth_label='TP' if n<5 else 'FP') for n in range(15)]
            targets.write_text(json.dumps({'targets':[dict(target_id=str(n),preparation_status='READY') for n in range(15)]}))
            # TP: retained 3, lost 1, abstained 1; FP: filtered 7, retained 2, abstained 1.
            verdicts=['confirmed']*3+['false_positive','inconclusive']+['false_positive']*7+['confirmed']*2+['inconclusive']
            for n,verdict in enumerate(verdicts):
                (results/f'{n}.json').write_text(json.dumps(dict(status='COMPLETED',verdict=verdict,rounds=[{}],requested_fragments=2,total_tokens=10,api_calls_attempted=1)))
            cohort=dict(records=rows,adjudications_sha256='fixture',baseline=dict(tp=5,fp=10))
            with patch.object(module,'BASE',base),patch.object(module,'RESULTS',results),patch.object(module,'COHORT',cohort_path),patch.object(module,'TARGETS',targets),patch.object(module,'verify_freeze',return_value=cohort),contextlib.redirect_stdout(io.StringIO()):
                module.summarize()
            m=json.loads((base/'fp_reduction_results.json').read_text())['llm_metrics']
            self.assertEqual((m['tp_retained'],m['tp_lost'],m['tp_inconclusive']),(3,1,1))
            self.assertEqual((m['fp_filtered'],m['fp_retained'],m['fp_inconclusive']),(7,2,1))
            self.assertEqual(m['tp_retention'],.6);self.assertEqual(m['fp_reduction'],.7)
            self.assertEqual(m['precision_after_llm_binary'],3/5)
            self.assertEqual(m['conservative_precision'],4/7)
            self.assertEqual(m['inconclusive_rate'],2/15)
            self.assertEqual(m['total_tokens'],150)

    def test_summarize_refreshes_existing_reports_without_api_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);results=base/'results';results.mkdir()
            cohort_path=base/'cohort.json';cohort_path.write_text('{}')
            targets=base/'targets.json'
            rows=[dict(target_id=str(n),case='fixture',finding_id=str(n),detector='fixture',ground_truth_label='TP' if n<5 else 'FP') for n in range(15)]
            targets.write_text(json.dumps({'targets':[dict(target_id=str(n),preparation_status='READY') for n in range(15)]}))
            verdicts=['confirmed']*4+['inconclusive']+['false_positive']*7+['confirmed']*2+['inconclusive']
            for n,verdict in enumerate(verdicts):
                rounds=2 if n<7 else 1
                (results/f'{n}.json').write_text(json.dumps(dict(status='COMPLETED',verdict=verdict,rounds=[{}]*rounds,requested_fragments=2 if n<8 else 1,total_tokens=3632,api_calls_attempted=rounds,model='saved-model')))
            protected={p:p.read_bytes() for p in [cohort_path,targets,*results.iterdir()]}
            (base/'fp_reduction_results.json').write_text(' {"status":"INCOMPLETE","not_run":15}')
            (base/'fp_reduction_results.md').write_text('Status: INCOMPLETE; NOT_RUN = 15')
            cohort=dict(records=rows,adjudications_sha256='fixture',baseline=dict(tp=5,fp=10))
            from context_audit import llm
            with patch.object(module,'BASE',base),patch.object(module,'RESULTS',results),patch.object(module,'COHORT',cohort_path),patch.object(module,'TARGETS',targets),patch.object(module,'verify_freeze',return_value=cohort),patch.dict(module.os.environ,{},clear=True),patch.object(module,'run') as run,patch.object(module,'worker') as worker,patch.object(llm,'analyze') as analyze,patch('sys.argv',['runner','--summarize']),contextlib.redirect_stdout(io.StringIO()):
                module.main()
                first=(base/'fp_reduction_results.json').read_bytes()
                module.main()  # Repeated summaries refresh the same canonical files.
            run.assert_not_called();worker.assert_not_called();analyze.assert_not_called()
            report=json.loads((base/'fp_reduction_results.json').read_text())
            self.assertEqual(report['status'],'COMPLETE')
            self.assertFalse(report['configuration_ready'])
            self.assertEqual(report['model'],'saved-model')
            self.assertEqual(report['llm_metrics'],dict(tp_retained=4,tp_lost=0,tp_inconclusive=1,fp_filtered=7,fp_retained=2,fp_inconclusive=1,errors=0,not_run=0,tp_retention=.8,fp_reduction=.7,precision_after_llm_binary=4/6,conservative_precision=5/8,inconclusive_rate=2/15,total_api_calls_attempted=22,total_tokens=54480,average_rounds=22/15,average_requested_fragments=23/15,usage_may_be_incomplete=False))
            markdown=(base/'fp_reduction_results.md').read_text()
            self.assertIn('Status: **COMPLETE**',markdown)
            for verdict in ['confirmed','false_positive','inconclusive']:self.assertIn(verdict,markdown)
            self.assertEqual(first,(base/'fp_reduction_results.json').read_bytes())
            self.assertEqual(list(base.glob('fp_reduction_results-*.json')),[])
            self.assertEqual(len(report['records']),15)
            for path,content in protected.items():self.assertEqual(path.read_bytes(),content)

    def test_actual_prepared_targets_contain_only_production_payload(self):
        targets=json.loads(module.TARGETS.read_text())['targets']
        self.assertEqual(len(targets),15)
        forbidden={'ground_truth_label','adjudication_label','provenance','adjudications','label_scope','matched_slither_finding_ids','expected_verdict','historical_ground_truth'}
        for target in targets:
            self.assertEqual(target['preparation_status'],'READY')
            self.assertFalse(forbidden.intersection(target))
            self.assertEqual(set(target['initial_payload']),{'target','available_context','context_complete','task','finding'})
            self.assertFalse(forbidden.intersection(target['initial_payload']['finding']))
