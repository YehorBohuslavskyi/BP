"""Generic contradictions, source claims, processing outcomes and historical replay."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.verdict_consistency import check
from context_audit.v2_dataset_scoring import score_labels
from consistency_fixtures import with_basis
from test_direct_discovery import prepared
from test_direct_verification import final

FID = 'fragment-generic'
CODE = 'function act() external { require(allowed[msg.sender]); target.call(data); value = 0; }'


def assessment(verdict='confirmed', explanation=None):
    explanation = explanation or {'confirmed': 'The operation allows an attacker to bypass the intended invariant.',
        'rejected': 'The supplied guard prevents the suspected path.',
        'inconclusive': 'A required relationship remains unknown.'}[verdict]
    return with_basis(dict(action='final', requested_ids=[], verdict=verdict,
        severity='high' if verdict == 'confirmed' else None, explanation=explanation,
        evidence_ids=[FID], execution_flow=[], incomplete_evidence=['Required source missing'] if verdict == 'inconclusive' else []),
        [dict(id=FID, source=CODE)])


class ConsistencyRuleTests(unittest.TestCase):
    def outcome(self, data):
        parsed = v.VerificationResponse.model_validate(data)
        return check(parsed, {FID: CODE})
    def fails(self, data, rule=None):
        r=self.outcome(data);self.assertFalse(r['passed'])
        if rule:self.assertIn(rule,r['failed_rules'])
        return r
    def test_valid_confirmed(self): self.assertTrue(self.outcome(assessment())['passed'])
    def test_valid_rejected(self): self.assertTrue(self.outcome(assessment('rejected'))['passed'])
    def test_valid_inconclusive(self): self.assertTrue(self.outcome(assessment('inconclusive'))['passed'])
    def test_checked_return_and_revert_contradict_confirmation(self):
        self.fails(assessment(explanation='The return value is checked and failure reverts.'),'PROTECTION_WITHOUT_RESIDUAL_DANGER')
    def test_authorization_protection_contradicts_confirmation(self):
        self.fails(assessment(explanation='The permission guard prevents an unauthorized caller.'),'PROTECTION_WITHOUT_RESIDUAL_DANGER')
    def test_effects_before_interaction_contradicts_confirmation(self):
        self.fails(assessment(explanation='State is updated before the external call, preventing the suspected path.'),'PROTECTION_WITHOUT_RESIDUAL_DANGER')
    def test_checked_arithmetic_prevention_contradicts_confirmation(self):
        self.fails(assessment(explanation='Overflow is prevented by checked arithmetic.'),'PROTECTION_WITHOUT_RESIDUAL_DANGER')
    def test_unsupported_hypothesis_contradicts_confirmation(self):
        self.fails(assessment(explanation='The candidate hypothesis is not supported.'),'EXPLICIT_HYPOTHESIS_DENIAL')
    def test_cannot_establish_core_mechanism_contradicts_confirmation(self):
        self.fails(assessment(explanation='I cannot establish the core dangerous behavior.'),'EXPLICIT_CORE_UNCERTAINTY')
    def test_flow_can_contradict_positive_explanation(self):
        a=assessment();a['execution_flow']=['The suspected path is prevented by the guard.']
        self.fails(a,'EXPLICIT_HYPOTHESIS_DENIAL')
    def test_core_unknown_structured(self):
        a=assessment();a['verdict_basis']['core_conditions']='unknown'
        self.fails(a,'CONFIRMATION_CORE_CONDITIONS_UNKNOWN')
    def test_effective_mitigation_structured(self):
        a=assessment();a['verdict_basis']['mitigation_status']='effective'
        self.fails(a,'CONFIRMATION_MITIGATION_NOT_RESOLVED')
    def test_unknown_mitigation_structured(self):
        a=assessment();a['verdict_basis']['mitigation_status']='unknown'
        self.fails(a,'CONFIRMATION_MITIGATION_NOT_RESOLVED')
    def test_unresolved_core_condition_hidden_from_top_level(self):
        a=assessment();a['verdict_basis']['unresolved_conditions']=['Caller reachability unknown']
        self.fails(a,'CONFIRMATION_UNRESOLVED_CONDITIONS')
    def test_protection_claim_does_not_support_danger(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['role']='protection'
        self.fails(a,'NO_DANGEROUS_SOURCE_CLAIM')
    def test_fabricated_source_quote(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['source_quote']='missing_source_operation();'
        self.fails(a,'SOURCE_QUOTE_NOT_SUPPORTED')
    def test_comment_quote_cannot_ground_claim(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['source_quote']='// target.call(data);'
        self.fails(a,'SOURCE_QUOTE_NOT_SUPPORTED')
    def test_uncited_source_quote_id(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['fragment_id']='fragment-other'
        self.fails(a,'CLAIM_EVIDENCE_NOT_SUPPLIED_OR_CITED')
    def test_blank_mechanism_is_invalid(self):
        a=assessment();a['verdict_basis']['mechanism']='   '
        with self.assertRaises(ValidationError):
            self.outcome(a)
    def test_mixed_risk_and_guard_without_resolution(self):
        a=assessment(explanation='The guard prevents one path, but the operation allows an attacker to bypass another invariant.')
        self.fails(a,'MIXED_RISK_AND_PROTECTION_UNRESOLVED')
    def test_guard_with_grounded_residual_mechanism_is_allowed(self):
        a=assessment(explanation='The guard prevents one path, but the operation allows an attacker to bypass the intended invariant.')
        b=a['verdict_basis'];b.update(mitigation_status='ineffective',mitigation_reason='The supplied guard controls a different path; the residual operation remains reachable.')
        b['evidence_claims'].append(dict(fragment_id=FID,source_quote='require(allowed[msg.sender]);',role='protection'))
        self.assertTrue(self.outcome(a)['passed'])
    def test_ineffective_mitigation_requires_its_own_source(self):
        a=assessment();a['verdict_basis'].update(mitigation_status='ineffective',mitigation_reason='The guard misses this path.')
        self.fails(a,'MITIGATION_BYPASS_NOT_GROUNDED')
    def test_checked_word_alone_does_not_reject_confirmation(self):
        a=assessment(explanation='The checked input is bounded, but the operation allows an attacker to bypass the intended invariant.')
        self.assertTrue(self.outcome(a)['passed'])
    def test_rejected_with_reachable_danger_is_flagged(self):
        self.fails(assessment('rejected','The operation allows an attacker to bypass the intended invariant.'),'REJECTION_DESCRIBES_DANGEROUS_PATH')
    def test_rejected_unknown_mechanism_is_flagged(self):
        a=assessment('rejected');a['verdict_basis']['mechanism_status']='unknown'
        self.fails(a,'REJECTION_MECHANISM_NOT_CONTRADICTED')
    def test_rejected_with_unresolved_condition_is_flagged(self):
        a=assessment('rejected');a['verdict_basis']['unresolved_conditions']=['Whether the guard applies is unknown']
        self.fails(a,'REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM')
    def test_inconclusive_supported_claim_is_flagged(self):
        a=assessment('inconclusive');a['verdict_basis']['mechanism_status']='supported'
        self.fails(a,'ABSTENTION_CLAIMS_ESTABLISHED_MECHANISM')
    def test_inconclusive_without_uncertainty_is_flagged(self):
        a=assessment('inconclusive');a['incomplete_evidence']=[];a['verdict_basis']['unresolved_conditions']=[]
        self.fails(a,'ABSTENTION_WITHOUT_UNCERTAINTY')
    def test_live_protocol_cannot_downgrade_to_legacy(self):
        a=assessment();del a['verdict_basis']
        with self.assertRaises(ValidationError):v.VerificationResponse.model_validate(a)
        self.assertEqual(v.LegacyVerificationResponse.model_validate(a).verdict,'confirmed')
    def test_null_basis_not_a_live_final_verdict(self):
        a=assessment();a['verdict_basis']=None
        self.fails(a,'MISSING_VERDICT_BASIS')
    def test_negated_check_is_not_a_defensive_assertion(self):
        a=assessment(explanation='The return value is not checked and failure does not revert, which allows an attacker to bypass the intended invariant.')
        self.assertTrue(self.outcome(a)['passed'])
    def test_no_unchecked_path_is_not_a_positive_risk(self):
        a=assessment('rejected','No unchecked return exists; the guard prevents the suspected path.')
        self.assertTrue(self.outcome(a)['passed'])
    def test_quote_cannot_change_a_string_literal(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['source_quote']='require(ok, "two words");'
        self.assertIn('SOURCE_QUOTE_NOT_SUPPORTED',check(a,{FID:'require(ok, "two    words");'})['failed_rules'])
    def test_unknown_reachability_in_flow_is_not_confirmation(self):
        a=assessment();a['execution_flow']=['Caller reachability remains unknown.']
        self.fails(a,'EXPLICIT_CORE_UNCERTAINTY')
    def test_missing_guard_does_not_justify_rejection(self):
        a=assessment('rejected','I cannot verify the core guard because required source is missing.')
        self.fails(a,'REJECTION_WITH_CORE_UNCERTAINTY')
    def test_established_vulnerability_and_uncertain_severity_not_abstention(self):
        a=assessment('inconclusive','The vulnerability is established; severity is unknown.')
        self.fails(a,'ABSTENTION_ASSERTS_DANGEROUS_PATH')
    def test_blank_explanation_is_rejected_by_structural_guard(self):
        with self.assertRaises(ValidationError):
            v.VerificationResponse.model_validate(assessment(explanation='   '))
    def test_blank_uncertainty_is_not_abstention_evidence(self):
        a=assessment('inconclusive');a['incomplete_evidence']=[' '];a['verdict_basis']['unresolved_conditions']=[' ']
        self.fails(a,'ABSTENTION_WITHOUT_UNCERTAINTY')


class ConsistencyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        _,self.contracts,self.catalog=prepared(Path(self.tmp.name))
        contract=next(c for c in self.contracts if c['contract']=='Vault')
        f=next(f for f in contract['functions'] if f['signature']=='withdraw(uint256)')
        self.c=dict(candidate_id='generic-candidate',contract='Vault',primary_function=f['signature'],
            primary_fragment_id=f['fragment_id'],suspected_type='Example hypothesis',reason='Example reason',
            related_fragment_ids=[],requested_context_ids=[],uncertainty='Needs source')
    def test_failure_keeps_original_response_usage_and_no_security_verdict(self):
        captured=[]
        def mock(p,s,**kw):
            a=final(p,s);a['assessment']['explanation']='The hypothesis is unsupported.'
            a['assessment']['verdict_basis']['mechanism']=a['assessment']['explanation']
            captured.append(copy.deepcopy(a));return a
        r=v.verify_candidate(self.c,self.contracts,self.catalog,analyze_fn=mock)
        self.assertEqual(r['status'],'processing_failed');self.assertIsNone(r['verdict']);self.assertIsNone(r['severity'])
        self.assertEqual(r['original_model_verdict'],'confirmed')
        self.assertEqual(r['errors'][0]['code'],'SEMANTIC_CONSISTENCY_FAILED')
        self.assertEqual(r['rounds'][0]['response'],captured[0]);self.assertEqual(r['usage']['total_tokens'],15)
        self.assertEqual(r['errors'][0]['diagnostic']['candidate_id'],self.c['candidate_id'])
    def test_unseen_evidence_still_precedes_consistency(self):
        def mock(p,s,**kw):
            a=final(p,s);a['assessment']['evidence_ids']=['fragment-invented'];return a
        r=v.verify_candidate(self.c,self.contracts,self.catalog,analyze_fn=mock)
        self.assertEqual(r['errors'][0]['code'],'UNSEEN_EVIDENCE_ID')
    def test_failed_consistency_is_inconclusive_under_unchanged_scorer(self):
        target={'contract':'Vault','fragment_id':self.c['primary_fragment_id'],'location':{}}
        rows=score_labels([{'label_id':'L','swc_id':'SWC-999','targets':[target],'original_label':{}}],
            {'coverage_counts':{'processing_failures':1},'contracts':[],'issues':[]},{})
        self.assertEqual(rows[0]['status'],'INCONCLUSIVE')
    def test_context_request_cannot_also_claim_a_verdict_basis(self):
        def mock(p,s,**kw):
            a=final(p,s);a['assessment'].update(action='request_context',requested_ids=[p['available_context'][0]['id']],
                verdict=None,severity=None,evidence_ids=[],execution_flow=[])
            return a
        r=v.verify_candidate(self.c,self.contracts,self.catalog,analyze_fn=mock)
        self.assertEqual(r['errors'][0]['code'],'SEMANTIC_CONSISTENCY_FAILED')
        self.assertIn('CONTEXT_REQUEST_HAS_VERDICT_BASIS',r['consistency_validation']['failed_rules'])
        self.assertEqual(r['errors'][0]['diagnostic']['candidate_id'],self.c['candidate_id'])
    def test_saved_completed_consistency_metadata_cannot_be_tampered(self):
        r=v.verify_candidate(self.c,self.contracts,self.catalog,analyze_fn=lambda p,s,**kw:final(p,s))
        v.validate_saved_result(r,self.contracts,self.catalog)
        r['consistency_validation']['passed']=False
        with self.assertRaisesRegex(ValueError,'semantic consistency mismatch'):
            v.validate_saved_result(r,self.contracts,self.catalog)
    def test_valid_evidence_id_with_invented_quote_is_processing_failure(self):
        def mock(p,s,**kw):
            a=final(p,s);a['assessment']['verdict_basis']['evidence_claims'][0]['source_quote']='madeUpOperation();';return a
        r=v.verify_candidate(self.c,self.contracts,self.catalog,analyze_fn=mock)
        self.assertIsNone(r['verdict']);self.assertEqual(r['status'],'processing_failed')
        self.assertIn('SOURCE_QUOTE_NOT_SUPPORTED',r['consistency_validation']['failed_rules'])
    def test_pipeline_aggregation_reports_semantic_failure_without_finding(self):
        from context_audit.v2_pipeline import run_verification
        from test_direct_discovery import response
        def discover(batch):
            own=any(f['fragment_id']==self.c['primary_fragment_id'] for f in batch['functions'])
            return response(batch,[self.c] if own else [])
        found=d.run_discovery(self.contracts,self.catalog,execute=True,analyze_fn=discover)
        def mock(p,s,**kw):
            a=final(p,s);a['assessment']['explanation']='The hypothesis is not supported.'
            a['assessment']['verdict_basis']['mechanism']=a['assessment']['explanation'];return a
        report=run_verification(found,self.contracts,self.catalog,Path(self.tmp.name)/'report',analyze_fn=mock)
        self.assertEqual(report['coverage_counts']['semantic_consistency_failures'],1)
        self.assertEqual(report['coverage_counts']['processing_failures'],1)
        self.assertEqual(report['coverage_counts']['confirmed_candidates'],0)
        self.assertEqual(report['coverage_counts']['candidates_verified'],0)


class HistoricalConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pilot=json.loads(Path('experiments/mode-b-v2-development-pilot-2026-11-10/plan.json').read_text())
        wallet=json.loads(Path('experiments/mode-b-v2-development-2026-11-09/prepared/ixo-authoriser/b2-plan.json').read_text())['source']
        dataset=json.loads(Path('experiments/mode-b-v2-dataset-2026-11-09/manifest.json').read_text())
        voting=next(c for c in dataset['cases'] if c['id']=='element-core-voting')['source']
        cls.reports={};cls.prepared={}
        for name,source,path in [('wallet',wallet,'runs/mode-b-v2-unseen-evidence-continuation-2026-11-09/report.json'),
            ('voting',voting,'runs/mode-b-v2-dataset-2026-11-09/development/element-core-voting/analysis/report.json'),
            ('owner',pilot['execution']['cases'][0]['source'],'runs/mode-b-v2-development-pilot-first-case-retry-2026-11-10/case-c8c6063234efc85a1847/analysis/report.json'),
            ('transfers',pilot['execution']['cases'][1]['source'],'runs/mode-b-v2-development-pilot-2026-11-10/case-b9165b696836c994f572/analysis/report.json')]:
            cls.reports[name]=json.loads(Path(path).read_text())
            with patch('openai.OpenAI.__init__',side_effect=AssertionError('No API')):
                cls.prepared[name]=d.prepare(Path(source))
    def replay(self,name,function):
        r=next(i['result'] for i in self.reports[name]['issues'] if i['result']['candidate']['primary_function'].startswith(function))
        before=copy.deepcopy(r);review=v.replay_consistency(r,*self.prepared[name]);self.assertEqual(r,before)
        return r,review
    def test_transfers_is_flagged_without_rewriting_original(self):
        old,new=self.replay('transfers','safeTransfer(')
        self.assertEqual(old['verdict'],'confirmed');self.assertIsNone(new['verdict'])
        self.assertEqual(new['status'],'processing_failed')
        self.assertIn('EXPLICIT_HYPOTHESIS_DENIAL',new['consistency_validation']['failed_rules'])
    def test_valid_wallet_confirmation_preserved(self):
        _,new=self.replay('wallet','transfer(');self.assertEqual(new['verdict'],'confirmed')
    def test_preserved_ownership_rejection_remains_rejected(self):
        _,new=self.replay('wallet','_transferOwnership(');self.assertEqual(new['verdict'],'rejected')
    def test_wallet_abstention_preserved(self):
        _,new=self.replay('wallet','setAuthoriser(');self.assertEqual(new['verdict'],'inconclusive')
    def test_voting_confirmation_preserved(self):
        _,new=self.replay('voting','execute(');self.assertEqual(new['verdict'],'confirmed')
    def test_voting_rejection_preserved(self):
        _,new=self.replay('voting','vote(');self.assertEqual(new['verdict'],'rejected')
    def test_owner_confirmation_newly_flagged(self):
        _,new=self.replay('owner','addOwnerWithThreshold(');self.assertIsNone(new['verdict'])
        self.assertIn('EXPLICIT_CORE_UNCERTAINTY',new['consistency_validation']['failed_rules'])
    def test_owner_rejections_preserved(self):
        for f in ('removeOwner(','setupOwners('):
            _,new=self.replay('owner',f);self.assertEqual(new['verdict'],'rejected')
    def test_historical_parent_cannot_silently_use_new_protocol(self):
        from context_audit.development_pilot import validate_parent
        p=json.loads(Path('experiments/mode-b-v2-development-pilot-2026-11-10/plan.json').read_text())
        with self.assertRaisesRegex(ValueError,'PARENT_PROMPTS_CHANGED'):
            validate_parent(p['parent_manifest'])
    def test_valid_smoke_confirmation_preserved(self):
        root=Path('runs/mode-b-v2-protocol-hardened-retry-2026-11-09-01')
        source=json.loads((root/'smoke_manifest.json').read_text())['plan']['source']
        report=json.loads((root/'analysis/report.json').read_text())
        with patch('openai.OpenAI.__init__',side_effect=AssertionError('No API')):
            contracts,catalog=d.prepare(Path(source))
        original=report['issues'][0]['result']
        replay=v.replay_consistency(original,contracts,catalog)
        self.assertEqual(replay['verdict'],'confirmed')


class NeutralEvidenceRoleTests(unittest.TestCase):
    def test_rejection_can_describe_a_guarded_operation_as_context(self):
        a=assessment('rejected')
        a['verdict_basis']['evidence_claims'].append(dict(fragment_id=FID,source_quote='target.call(data);',role='context'))
        self.assertTrue(check(a,{FID:CODE})['passed'])
    def test_context_cannot_substitute_for_dangerous_confirmation_evidence(self):
        a=assessment();a['verdict_basis']['evidence_claims'][0]['role']='context'
        self.assertIn('NO_DANGEROUS_SOURCE_CLAIM',check(a,{FID:CODE})['failed_rules'])
    def test_context_cannot_substitute_for_a_rejection_guard(self):
        a=assessment('rejected');a['verdict_basis']['evidence_claims'][0]['role']='context'
        self.assertIn('NO_PROTECTION_SOURCE_CLAIM',check(a,{FID:CODE})['failed_rules'])
