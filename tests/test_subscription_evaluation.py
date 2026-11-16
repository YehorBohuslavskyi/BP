"""Exposure tracking prevents repeat model use without touching GT labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run_subscription_evaluation as runner

class SubscriptionExposureTests(unittest.TestCase):
    def registry(self, root, data):
        path=root/'docs/reviews/new/subscription-exposure.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(data))
        return path

    def test_actual_attempt_is_excluded_but_unrun_preparation_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.registry(root, {'kind':'subscription_exposure', 'attempted_cases':[
                {'source_sha256':'a'*64,'attempted_codex_turns':1}],
                'unrun_preparation':{'source_sha256':'b'*64}})
            with patch.object(runner,'ROOT',root):
                self.assertEqual(runner.known_source_hashes(),{'a'*64})

    def test_zero_attempt_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.registry(root, {'kind':'subscription_exposure','attempted_cases':[
                {'source_sha256':'a'*64,'attempted_codex_turns':0}]})
            with patch.object(runner,'ROOT',root), self.assertRaises(ValueError):
                runner.known_source_hashes()

    def test_malformed_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.registry(root,{}).write_text('{')
            with patch.object(runner,'ROOT',root), self.assertRaises(ValueError):
                runner.known_source_hashes()

    def test_development_pilot_cannot_include_validation_or_heldout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);proposal=root/'proposal';proposal.mkdir()
            cases=[{'id':split,'source_identity':{'source_sha256':str(index)*64},'project':split,
                    'split':split,'budget':{'max_reserved_tokens':60000},'limits':{'max_candidates':3,'max_rounds':3,'max_total_tokens':60000}}
                   for index,split in enumerate(('development','validation','held_out'),1)]
            (proposal/'manifest.json').write_text(json.dumps({'cases':cases}))
            output=root/'new-output'
            with patch.object(runner,'known_source_hashes',return_value=set()), \
                 patch.object(runner,'catalog_for',return_value=([],None)) as catalog,patch.object(runner,'identity',return_value={}):
                runner.prepare(proposal,output,1)
            plan=json.loads((output/'plan.json').read_text())
            self.assertEqual([c['split'] for c in plan['cases']],['development'])
            self.assertEqual(plan['cases'][0]['limits']['max_candidates'],2)
            self.assertEqual(plan['cases'][0]['limits']['max_total_tokens'],200000)
            self.assertEqual(cases[0]['limits']['max_total_tokens'],60000)
            self.assertEqual(plan['limits']['max_model_turns'],20)
            self.assertEqual(plan['limits']['max_observed_tokens'],750000)
            self.assertEqual(catalog.call_count,1)
            self.assertFalse(plan['paid_fallback'])
            self.assertEqual(plan['cases'][0]['budget']['api_key_requests'],0)
            self.assertEqual(plan['cases'][0]['budget']['token_count_requests'],0)
            self.assertEqual(plan['cases'][0]['budget']['max_verification_tokens'],200000)
            self.assertEqual(plan['cases'][0]['preparation_budget']['max_reserved_tokens'],60000)
