"""Offline scope/provenance tests for the single-contract approval entry point."""
import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import MagicMock,patch

from context_audit import direct_discovery as d,direct_verification as v
from context_audit.v2_artifacts import digest

PARENT=Path('experiments/mode-b-v2-dataset-2026-11-09/manifest.json')

class SingleCasePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.parent=Path(cls.temp.name)/'parent.json'
        fixture=json.loads(PARENT.read_text())
        case=next(c for c in fixture['cases'] if c['id']=='element-core-voting')
        case['output']=str(Path(cls.temp.name)/'run')
        _,catalog=d.prepare(Path(case['source']))
        case['source_identity']=catalog.source_identity
        cls.parent.write_text(json.dumps(fixture))
        cls.module=runpy.run_path('scripts/run_v2_single_case.py')
        with patch('openai.OpenAI.__init__',side_effect=AssertionError('Offline only')):
            cls.plan=cls.module['prepare'](cls.parent,'element-core-voting')
    def test_source_and_budget_exactly_match_frozen_case(self):
        old=next(c for c in json.loads(self.parent.read_text())['cases'] if c['id']=='element-core-voting')
        self.assertEqual(self.plan['case'],old)
        self.assertEqual(self.plan['case']['budget']['max_reserved_tokens'],60000)
        self.assertEqual(self.plan['case']['budget']['max_generation_calls'],11)
        self.assertEqual(self.plan['case']['budget']['max_count_calls'],11)
    def test_current_prompts_are_preserved(self):
        frozen=json.loads(PARENT.read_text())
        last=json.loads(Path('experiments/mode-b-v2-unseen-evidence-2026-11-09/continuation-plan.json').read_text())
        self.assertEqual(self.plan['frozen_protocols']['discovery']['prompt_sha256'],digest(d.SYSTEM_PROMPT))
        self.assertNotEqual(self.plan['frozen_protocols']['discovery']['prompt_sha256'],frozen['frozen_protocols']['discovery']['prompt_sha256'])
        self.assertEqual(self.plan['frozen_protocols']['verification']['prompt_sha256'],digest(v.SYSTEM_PROMPT))
        self.assertNotEqual(self.plan['frozen_protocols']['verification']['prompt_sha256'],last['prompt_sha256'])
        self.assertEqual(self.plan['frozen_protocols']['verification']['prompt_sha256'],digest(v.SYSTEM_PROMPT))
        self.assertIn('verdict_basis',v.VerificationResponse.model_json_schema()['required'])
    def test_execute_calls_exactly_one_case(self):
        execute=self.module['execute'];mock=MagicMock(return_value={'done':True})
        with patch.dict(execute.__globals__,{'execute_case':mock}):
            result=execute(copy.deepcopy(self.plan))
        self.assertEqual(result,{'done':True});mock.assert_called_once()
        self.assertEqual(mock.call_args.args[0]['id'],'element-core-voting')
        self.assertFalse(mock.call_args.kwargs.get('resume',False))
    def test_tampered_budget_rejected_before_executor(self):
        plan=copy.deepcopy(self.plan);plan['case']['budget']['max_generation_calls']=12
        execute=self.module['execute'];mock=MagicMock()
        with patch.dict(execute.__globals__,{'execute_case':mock}),self.assertRaises(ValueError):execute(plan)
        mock.assert_not_called()
    def test_parent_hash_mismatch_rejected_before_executor(self):
        plan=copy.deepcopy(self.plan);plan['parent_manifest_sha256']='bad'
        execute=self.module['execute'];mock=MagicMock()
        with patch.dict(execute.__globals__,{'execute_case':mock}),self.assertRaises(ValueError):execute(plan)
        mock.assert_not_called()
    def test_held_out_plan_cannot_use_development_entrypoint(self):
        held=next(c['id'] for c in json.loads(self.parent.read_text())['cases'] if c['cohort']=='held_out')
        with self.assertRaisesRegex(ValueError,'DEVELOPMENT_ONLY'):self.module['prepare'](self.parent,held)
    def test_existing_output_blocks_replay(self):
        with patch('pathlib.Path.exists',return_value=True),self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):
            self.module['prepare'](self.parent,'element-core-voting')
    def test_unknown_case_rejected(self):
        with self.assertRaisesRegex(ValueError,'EXACTLY_ONE_CASE'):self.module['prepare'](self.parent,'missing')
