"""Fresh source-only bundles remain consumable without labels or old approvals."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_audit import direct_discovery as d
from context_audit.verification_profiles import limits_for
from scripts import reindex_source_proposal as reindex
from scripts import run_subscription_evaluation as runner


class SourceReindexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'Example.sol'
        self.source.write_text('pragma solidity 0.4.25; contract C { function entry() public { helper(); } function helper() internal {} }')
        _,self.catalog=d.prepare(self.source)
        self.parent=self.root/'old-proposal'
        self.parent.mkdir()
        self.case=dict(id='case-one',source=str(self.source),dataset_file='p/Example.sol',project='p',split='development',
            source_identity=self.catalog.source_identity,limits=limits_for('baseline').model_dump(),
            budget=dict(max_reserved_tokens=60000),prepared_artifact='unused-old-index',ground_truth='MUST_NOT_COPY')
        self.manifest=dict(cases=[self.case],evaluation_payload='MUST_NOT_COPY')
        (self.parent/'manifest.json').write_text(json.dumps(self.manifest))
        (self.parent/'evaluation_only').mkdir()
        (self.parent/'evaluation_only/labels.json').write_text('MUST_NOT_READ')
        self.output=self.root/'fresh-proposal'

    def test_real_reindex_restores_graph_and_keeps_parent_source_and_budgets(self):
        before=(self.parent/'manifest.json').read_bytes(),self.source.read_bytes()
        original=Path.read_text
        def guarded_read(path,*args,**kwargs):
            if 'evaluation_only' in path.parts:
                raise AssertionError('Labels must never be read')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',guarded_read):
            result=reindex.prepare(self.parent,self.output,['case-one'])
            contracts,catalog=runner.catalog_for(result['cases'][0],self.output)
        self.assertEqual(result['cases'][0]['budget'],self.case['budget'])
        self.assertEqual(result['cases'][0]['limits'],self.case['limits'])
        self.assertEqual(catalog.function_index,self.catalog.function_index)
        self.assertTrue(contracts)
        self.assertEqual(before,((self.parent/'manifest.json').read_bytes(),self.source.read_bytes()))
        self.assertNotIn('MUST_NOT_COPY',json.dumps(result))
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['evaluation_labels_loaded'])

    def test_fresh_bundle_can_prepare_larger_limit_plan_without_model(self):
        result=reindex.prepare(self.parent,self.output,['case-one'])
        with patch.object(runner,'known_source_hashes',return_value=set()):
            runner.prepare(self.output,self.root/'new-run-plan',1,'expanded')
        plan=json.loads((self.root/'new-run-plan/plan.json').read_text())
        self.assertEqual(plan['cases'][0]['id'],'case-one')
        self.assertEqual(plan['cases'][0]['limits']['max_rounds'],5)
        self.assertEqual(plan['cases'][0]['limits']['max_fragments'],12)
        self.assertFalse((self.root/'new-run-plan/cases').exists())

    def test_existing_output_preserved(self):
        self.output.mkdir()
        (self.output/'sentinel').write_text('keep')
        with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT'):
            reindex.prepare(self.parent,self.output,['case-one'])
        self.assertEqual((self.output/'sentinel').read_text(),'keep')

    def test_unknown_duplicate_and_heldout_cases_stop_before_compilation(self):
        for ids in (['missing'],['case-one','case-one']):
            with patch.object(d,'prepare') as compiler,self.assertRaises(ValueError):
                reindex.prepare(self.parent,self.output,ids)
            compiler.assert_not_called()
        self.manifest['cases'][0]['split']='held_out'
        (self.parent/'manifest.json').write_text(json.dumps(self.manifest))
        with patch.object(d,'prepare') as compiler,self.assertRaisesRegex(ValueError,'DEVELOPMENT_ONLY'):
            reindex.prepare(self.parent,self.output,['case-one'])
        compiler.assert_not_called()

    def test_changed_source_stops_and_leaves_no_final_bundle(self):
        self.source.write_text(self.source.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_CHANGED'):
            reindex.prepare(self.parent,self.output,['case-one'])
        self.assertFalse(self.output.exists())

    def test_output_cannot_add_files_to_parent_or_historical_trees(self):
        for output in (self.parent/'nested',reindex.ROOT/'runs/must-not-write'):
            with self.assertRaisesRegex(ValueError,'FORBIDDEN'):
                reindex.prepare(self.parent,output,['case-one'])

    def test_index_tampering_is_rejected_by_reconstructed_catalog(self):
        result=reindex.prepare(self.parent,self.output,['case-one'])
        path=self.output/'prepared/case-one/structure.json'
        saved=json.loads(path.read_text())
        saved['function_index']['nodes']={}
        path.write_text(json.dumps(saved))
        with self.assertRaises(AssertionError):
            runner.catalog_for(result['cases'][0],self.output)
