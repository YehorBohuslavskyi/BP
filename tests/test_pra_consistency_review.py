"""Offline PRA response review and generic consistency regressions; no GT input."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from context_audit import direct_discovery as d, direct_verification as v
from context_audit.v2_artifacts import digest
from context_audit.verdict_consistency import check
from test_verdict_consistency import assessment, FID, CODE


class ParaphraseConsistencyTests(unittest.TestCase):
    def test_confirmed_paraphrase_without_vulnerability_name(self):
        a = assessment(explanation='A caller may execute the transfer twice before its recorded balance is reduced.')
        a['verdict_basis']['mechanism'] = 'Balance accounting happens after the outgoing transfer.'
        self.assertTrue(check(a, {FID: CODE})['passed'])

    def test_rejected_paraphrase_discusses_hypothesis_with_guard(self):
        a = assessment('rejected', 'The hypothesis alleges an unchecked return, but the result is checked and failure reverts.')
        a['verdict_basis']['mechanism'] = 'The hypothesized ignored result is prevented by the explicit check.'
        self.assertTrue(check(a, {FID: CODE})['passed'])

    def test_inconclusive_paraphrase_with_missing_core_evidence(self):
        a = assessment('inconclusive', 'The transfer is visible, but the accounting implementation was not supplied.')
        a['verdict_basis']['mechanism'] = 'Whether the operation breaks the balance invariant remains unknown.'
        self.assertTrue(check(a, {FID: CODE})['passed'])

    def test_confirmed_admits_no_harmful_path(self):
        a = assessment(explanation='The snippet does not establish a concrete harmful path beyond an authorized operation.')
        self.assertIn('EXPLICIT_CORE_UNCERTAINTY', check(a, {FID: CODE})['failed_rules'])

    def test_contradicted_structured_status_still_fails_with_paraphrase(self):
        a = assessment()
        a['verdict_basis'].update(mechanism='The transfer is reachable.', mechanism_status='contradicted')
        self.assertIn('CONFIRMATION_MECHANISM_NOT_SUPPORTED', check(a, {FID: CODE})['failed_rules'])

    def test_mixed_hypothesis_and_affirmative_residual_danger_still_fails(self):
        a = assessment('rejected', 'The hypothesis alleges an unchecked return, but the operation allows an attacker to bypass the guard.')
        self.assertIn('REJECTION_DESCRIBES_DANGEROUS_PATH', check(a, {FID: CODE})['failed_rules'])

    def test_structured_danger_claim_in_rejection_is_not_just_prose(self):
        a = assessment('rejected')
        a['verdict_basis']['evidence_claims'].append(dict(fragment_id=FID, source_quote='target.call(data);', role='dangerous_behavior'))
        self.assertIn('REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM', check(a, {FID: CODE})['failed_rules'])


class SavedResponseReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path('runs/mode-b-v2-consistency-development-2026-11-10/case-68aeb9008f95441250d8/analysis/sessions')
        cls.saved = {}
        for p in sorted(root.glob('*.json')):
            e = json.loads(p.read_text())
            if e['result_sha256'] != digest(e['result']):
                raise ValueError('PRA session checksum mismatch')
            cls.saved[e['result']['candidate']['primary_function']] = e['result']
        plan = json.loads(Path('experiments/mode-b-v2-consistency-hardening-2026-11-10/cases/case-68aeb9008f95441250d8-plan.json').read_text())
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')):
            cls.contracts, cls.catalog = d.prepare(Path(plan['case']['source']))

    def review(self, name):
        saved = self.saved[name]
        before = copy.deepcopy(saved)
        reviewed = v.review_saved_response(saved, self.contracts, self.catalog)
        self.assertEqual(saved, before)
        self.assertFalse(reviewed['authorizes_resume'])
        return reviewed

    def test_pra_unlock_remains_failed_for_substantive_uncertainty(self):
        r = self.review('unlock()')
        self.assertIsNone(r['eligible_model_verdict'])
        self.assertEqual(r['original_model_verdict'], 'confirmed')
        self.assertEqual(r['consistency_validation']['failed_rules'], ['EXPLICIT_CORE_UNCERTAINTY'])

    def test_pra_lock_abstention_is_eligible_only_in_separate_review(self):
        r = self.review('lock()')
        self.assertEqual(r['eligible_model_verdict'], 'inconclusive')
        self.assertTrue(r['consistency_validation']['passed'])
        self.assertEqual(self.saved['lock()']['status'], 'processing_failed')

    def test_pra_set_still_has_structured_danger_conflict(self):
        r = self.review('set(address,bool)')
        self.assertIsNone(r['eligible_model_verdict'])
        self.assertEqual(r['consistency_validation']['failed_rules'], ['REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM'])

    def test_request_source_tampering_is_rejected(self):
        r = copy.deepcopy(self.saved['lock()'])
        request = json.loads(r['rounds'][-1]['messages'][1]['content'])
        request['target']['source'] = 'fabricated();'
        r['rounds'][-1]['messages'][1]['content'] = json.dumps(request)
        with self.assertRaisesRegex(ValueError, 'Saved request source'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_request_candidate_tampering_is_rejected(self):
        r = copy.deepcopy(self.saved['lock()'])
        request = json.loads(r['rounds'][-1]['messages'][1]['content'])
        request['candidate']['primary_function'] = 'other()'
        r['rounds'][-1]['messages'][1]['content'] = json.dumps(request)
        with self.assertRaisesRegex(ValueError, 'candidate identity'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_unseen_evidence_is_rejected(self):
        r = copy.deepcopy(self.saved['lock()'])
        r['rounds'][-1]['response']['assessment']['evidence_ids'].append('fragment-unseen')
        with self.assertRaisesRegex(ValueError, 'unseen evidence'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_usage_tampering_is_rejected(self):
        r = copy.deepcopy(self.saved['lock()'])
        r['usage']['total_tokens'] += 1
        with self.assertRaisesRegex(ValueError, 'Saved usage'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_other_processing_failure_cannot_be_recovered(self):
        r = copy.deepcopy(self.saved['lock()'])
        r['errors'].append({'code': 'INCOMPLETE_MODEL_RESPONSE'})
        with self.assertRaisesRegex(ValueError, 'semantic-only'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_original_verdict_tampering_is_rejected(self):
        r = copy.deepcopy(self.saved['lock()'])
        r['original_model_verdict'] = 'confirmed'
        with self.assertRaisesRegex(ValueError, 'original verdict'):
            v.review_saved_response(r, self.contracts, self.catalog)

    def test_invented_quote_remains_a_consistency_failure(self):
        r = copy.deepcopy(self.saved['lock()'])
        r['rounds'][-1]['response']['assessment']['verdict_basis']['evidence_claims'][0]['source_quote'] = 'invented();'
        audit = v.review_saved_response(r, self.contracts, self.catalog)
        self.assertIn('SOURCE_QUOTE_NOT_SUPPORTED', audit['consistency_validation']['failed_rules'])
        self.assertIsNone(audit['eligible_model_verdict'])
