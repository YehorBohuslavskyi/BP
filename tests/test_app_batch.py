"""Batch service tests use synthetic reports and never call a paid API."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from context_audit.app.batch import batch_plan, full_analysis, export_full_analysis
from context_audit.app.config import VerificationSettings
from context_audit.app.services import Analysis
from context_audit.app.session import AuditSession
from test_gui_presentation import sample_finding, sample_report


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.session = AuditSession()
        self.session.set_upload('demo.sol', b'pragma solidity ^0.4.25; contract Demo {}')
        self.addCleanup(self.session.clear)
        self.findings = [replace(sample_finding(), id=str(i), impact=impact)
                         for i, impact in enumerate(('High', 'Medium', 'Low', 'Informational'))]
        self.findings.append(replace(sample_finding(), id='global', function_signature=None))
        self.session.analysis = Analysis('0.4.25', self.session.upload.digest, self.findings, {})

    def test_eligibility_and_impact_filters(self):
        for option, expected in [('High only', [0]), ('High + Medium', [0, 1]), ('All eligible', [0, 1, 2, 3])]:
            plan = batch_plan(self.findings, self.session.upload.source_path, {}, option)
            self.assertEqual(plan['pending'], expected)
            self.assertEqual(len(plan['eligible']), 4)
            self.assertIn('global', plan['skipped'])
        with self.assertRaises(ValueError):
            batch_plan(self.findings, None, {}, 'invalid')

    def test_completed_results_are_reused_and_progress_is_sequential(self):
        events = []
        with patch('context_audit.app.session.verify_selected', side_effect=lambda *a: sample_report()) as verify:
            self.session.verify_batch(VerificationSettings('mock'), progress=lambda *a: events.append(a))
            self.session.verify_batch(VerificationSettings('other-model'))
        self.assertEqual(verify.call_count, 2)
        self.assertEqual([(e[0], e[3]) for e in events], [(1, False), (1, True), (2, False), (2, True)])
        self.assertEqual(self.session.reviewed_finding_ids, {'0', '1'})

    def test_failure_continues_and_exports_no_exception_secrets(self):
        with patch('context_audit.app.session.verify_selected', side_effect=[RuntimeError('secret-key'), sample_report()]):
            self.session.verify_batch(VerificationSettings('mock'))
        result = full_analysis(self.session)
        self.assertEqual(result['summary']['errors'], 1)
        self.assertEqual(result['summary']['reviewed'], 1)
        self.assertEqual(result['summary']['skipped'], 3)
        self.assertFalse(result['usage']['complete'])
        self.assertEqual(result['usage']['failed_attempts'], 1)
        self.assertNotIn('secret-key', export_full_analysis(self.session))
        with patch('context_audit.app.session.verify_selected', return_value=sample_report()) as retry:
            self.session.verify_batch(VerificationSettings('mock'))
        self.assertEqual(retry.call_count, 1)
        self.assertEqual(full_analysis(self.session)['summary']['errors'], 0)

    def test_aggregation_counts_abstentions_and_all_actual_history(self):
        reports = [sample_report() for _ in range(3)]
        for report, verdict in zip(reports, ('confirmed', 'false_positive', 'inconclusive')):
            report['result']['assessment']['verdict'] = verdict
        with patch('context_audit.app.session.verify_selected', side_effect=reports):
            for index in range(3):
                self.session.verify(index, VerificationSettings('mock'))
        result = json.loads(export_full_analysis(self.session))
        self.assertEqual([result['summary'][v] for v in ('confirmed', 'false_positive', 'inconclusive')], [1, 1, 1])
        self.assertEqual(result['usage']['api_calls'], 6)
        self.assertEqual(result['usage']['input_tokens'], 2199)
        self.assertEqual(result['usage']['output_tokens'], 471)
        self.assertEqual(result['usage']['total_tokens'], 2670)
        self.assertEqual(result['usage']['average_rounds'], 2)
        self.assertEqual(result['usage']['requested_fragments'], 3)
        self.assertEqual(len(result['findings']), 5)
        self.assertEqual(result['findings'][3]['status'], 'NOT REVIEWED')

    def test_clear_preserves_analysis_and_upload(self):
        upload, analysis = self.session.upload, self.session.analysis
        with patch('context_audit.app.session.verify_selected', return_value=sample_report()):
            self.session.verify_batch(VerificationSettings('mock'))
        self.session.clear_verifications()
        self.assertIs(self.session.upload, upload)
        self.assertIs(self.session.analysis, analysis)
        self.assertEqual(full_analysis(self.session)['usage']['total_tokens'], 0)
        self.assertEqual(self.session.reviewed_finding_ids, set())
        self.assertEqual(self.session.skipped, {})

    def test_duplicate_ids_are_planned_once(self):
        plan = batch_plan([self.findings[0], self.findings[0]], None, {})
        self.assertEqual(plan['pending'], [0])
