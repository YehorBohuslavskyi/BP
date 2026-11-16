"""Neutral risk observations do not establish exploitability in an abstention."""
import unittest
from context_audit.verdict_consistency import check
from test_verdict_consistency import assessment,FID,CODE

class NeutralAbstentionTests(unittest.TestCase):
    def test_ignored_return_fact_with_unknown_mechanism_can_abstain(self):
        a=assessment('inconclusive','The return value is ignored; its consequence depends on external implementation behavior.')
        self.assertTrue(check(a,{FID:CODE})['passed'])

    def test_neutral_fact_does_not_replace_required_uncertainty(self):
        a=assessment('inconclusive','The return value is ignored.')
        a['incomplete_evidence']=[];a['verdict_basis']['unresolved_conditions']=[]
        self.assertIn('ABSTENTION_WITHOUT_UNCERTAINTY',check(a,{FID:CODE})['failed_rules'])

    def test_affirmative_dangerous_role_still_contradicts_abstention(self):
        a=assessment('inconclusive')
        a['verdict_basis']['evidence_claims'][0]['role']='dangerous_behavior'
        self.assertIn('ABSTENTION_ASSERTS_DANGEROUS_PATH',check(a,{FID:CODE})['failed_rules'])

    def test_explicit_dangerous_path_still_blocks_abstention(self):
        a=assessment('inconclusive','The operation allows an attacker to drain funds.')
        self.assertIn('ABSTENTION_ASSERTS_DANGEROUS_PATH',check(a,{FID:CODE})['failed_rules'])

    def test_rejection_rule_is_unchanged(self):
        a=assessment('rejected','The return value is ignored.')
        self.assertIn('REJECTION_DESCRIBES_DANGEROUS_PATH',check(a,{FID:CODE})['failed_rules'])

    def test_legacy_limited_abstention_check_is_unchanged(self):
        a=assessment('inconclusive','The return value is ignored.');del a['verdict_basis']
        self.assertIn('ABSTENTION_ASSERTS_DANGEROUS_PATH',check(a,{FID:CODE},historical=True)['failed_rules'])
