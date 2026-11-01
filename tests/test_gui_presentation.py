"""Source-only accounting, eligibility, and session/export regression checks."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from context_audit.app.config import ApplicationError, VerificationSettings
from context_audit.app.presentation import (
    compact_lines, finding_key, is_finding_verifiable, requested_fragment_ids,
    source_context_efficiency, source_fragments, verification_export,
    target_function_lines, marked_source_excerpt,
)
from context_audit.app.services import Analysis
from context_audit.app.session import AuditSession, upgrade_session
from context_audit.findings import Finding


def sample_finding() -> Finding:
    return Finding('stable-id', 'suicidal', 'High', 'High', 'Static claim',
                   'Demo', 'kill()', 'source.sol', [1], 0, 4)


def round_result(number: int, requested: list[str]) -> dict:
    return {'round': number, 'result': {'assessment': {
        'action': 'request_context' if requested else 'final', 'requested_ids': requested,
        'explanation': 'Public structured explanation', 'evidence_ids': [],
    }}}


def sample_report() -> dict:
    payload = {'target': {'id': 'target', 'source': 'abcd', 'signature': 'kill()'},
               'available_context': [{'id': 'guard', 'kind': 'modifier', 'name': 'owned()',
                                      'reasons': ['modifier']}]}
    result = {'assessment': {'verdict': 'confirmed', 'explanation': 'Public explanation',
                             'evidence_ids': ['guard']},
              'rounds': [round_result(1, ['guard']), round_result(2, [])],
              'provided_context': [{'id': 'guard', 'kind': 'modifier', 'name': 'owned()', 'source': 'abcdefgh'}]}
    return {'finding': asdict(sample_finding()), 'initial_payload': payload, 'result': result,
            'summary': {'rounds': 2, 'input_tokens': 733, 'output_tokens': 157, 'total_tokens': 890},
            'context_efficiency': source_context_efficiency('a' * 40, payload, result),
            'model': 'test-only', 'compiler': '0.4.25'}


class PresentationTests(unittest.TestCase):
    def test_compact_ranges(self):
        self.assertEqual(compact_lines([15, 12, 13, 14, 12]), '12-15')
        self.assertEqual(compact_lines([12, 15, 18, 19, 20]), '12, 15, 18-20')
        self.assertEqual(compact_lines([]), '')
        self.assertEqual(compact_lines([9]), '9')
        with self.assertRaises(ValueError):
            compact_lines([0])

    def test_function_metadata_not_detector_name_controls_eligibility(self):
        finding = sample_finding()
        self.assertTrue(is_finding_verifiable(finding))
        for fields in ({'contract': None}, {'function_signature': None}, {'file': None},
                       {'function_start': None}, {'function_length': 0}):
            self.assertFalse(is_finding_verifiable(replace(finding, **fields)))
        self.assertTrue(is_finding_verifiable(replace(finding, detector='arbitrary-rule')))
        self.assertFalse(is_finding_verifiable(finding, Path('/tmp/other.sol')))
        self.assertTrue(is_finding_verifiable(finding, Path('/tmp/source.sol')))

    def test_source_metrics_ignore_metadata_and_api_usage(self):
        report = sample_report()
        metrics = report['context_efficiency']
        self.assertEqual(metrics['full_source_estimated_tokens'], 10)
        self.assertEqual(metrics['initial_selected_source_estimated_tokens'], 1)
        self.assertEqual(metrics['additional_selected_source_estimated_tokens'], 2)
        self.assertEqual(metrics['cumulative_selected_source_estimated_tokens'], 3)
        self.assertAlmostEqual(metrics['source_context_reduction'], .7)
        report['initial_payload']['task'] = 'large metadata' * 1000
        self.assertEqual(source_context_efficiency('a' * 40, report['initial_payload'], report['result']), metrics)

    def test_empty_full_and_larger_selected_source(self):
        result = {'rounds': [], 'provided_context': []}
        empty = {'target': {'id': 't', 'source': ''}}
        self.assertIsNone(source_context_efficiency('', empty, result)['source_context_reduction'])
        full = {'target': {'id': 't', 'source': 'abcd'}}
        self.assertEqual(source_context_efficiency('abcd', full, result)['source_context_reduction'], 0)
        larger = {'target': {'id': 't', 'source': 'abcdefgh'}}
        self.assertEqual(source_context_efficiency('abcd', larger, result)['source_context_reduction'], -1)

    def test_requests_are_unique_and_last_round_is_not_sent(self):
        report = sample_report()
        result = report['result']
        result['rounds'] = [round_result(1, ['guard', 'guard']), round_result(2, ['late'])]
        result['provided_context'] *= 2
        result['provided_context'].append({'id': 'late', 'source': 'x' * 1000})
        self.assertEqual(requested_fragment_ids(result), ['guard', 'late'])
        self.assertEqual(requested_fragment_ids(result, sent_only=True), ['guard'])
        metrics = source_context_efficiency('a' * 40, report['initial_payload'], result)
        self.assertEqual(metrics['additional_selected_source_estimated_tokens'], 2)
        fragments = source_fragments(report['initial_payload'], result)
        self.assertFalse(next(f for f in fragments if f['id'] == 'late')['sent_to_model'])
        self.assertEqual(next(f for f in fragments if f['id'] == 'guard')['reasons'], ['modifier'])

    def test_exports_public_fields_only(self):
        report = sample_report()
        report['OPENAI_API_KEY'] = 'private-secret'
        report['result']['reasoning'] = 'hidden-reasoning'
        exported = verification_export(report)
        encoded = json.dumps(exported)
        self.assertNotIn('private-secret', encoded)
        self.assertNotIn('hidden-reasoning', encoded)
        self.assertEqual(exported['finding']['function'], 'kill()')
        self.assertEqual(exported['finding']['impact'], 'High')
        self.assertEqual(exported['verification']['requested_fragment_ids'], ['guard'])
        self.assertEqual(exported['usage']['total_tokens'], 890)
        self.assertEqual(exported['context_efficiency']['cumulative_selected_source_estimated_tokens'], 3)

    def test_utf8_function_range_and_read_only_markers(self):
        source = '// é\nfunction f() {}\n'
        finding = replace(sample_finding(), lines=[2], function_start=len('// é\n'.encode()),
                          function_length=len('function f() {}'.encode()))
        self.assertEqual(target_function_lines(source, finding), [2])
        self.assertIn('▶    2', marked_source_excerpt(source, finding))


class ReviewedSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = AuditSession()
        self.session.set_upload('demo.sol', b'pragma solidity ^0.4.25; contract Demo {}')
        self.addCleanup(self.session.clear)
        self.session.analysis = Analysis('0.4.25', self.session.upload.digest, [sample_finding()], {})

    def test_unique_ids_and_export_cache_survive_reverification(self):
        with patch('context_audit.app.session.verify_selected', side_effect=lambda *args: sample_report()) as verify:
            self.session.verify(0, VerificationSettings('test'))
            self.session.verify(0, VerificationSettings('test'))
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(self.session.reviewed_finding_ids, {'stable-id'})
        self.assertEqual(len(self.session.latest), 1)
        exported = json.loads(self.session.exported_result)
        self.assertEqual(len(exported['verification']), 2)
        self.assertEqual(exported['usage']['total_tokens'], 1780)
        self.assertEqual(exported['schema_version'], 2)

    def test_failure_does_not_count_as_review_and_preserves_completed_result(self):
        with patch('context_audit.app.session.verify_selected', side_effect=ApplicationError('failed')):
            with self.assertRaises(ApplicationError):
                self.session.verify(0, VerificationSettings('test'))
        self.assertEqual(self.session.reviewed_finding_ids, set())
        with patch('context_audit.app.session.verify_selected', return_value=sample_report()):
            self.session.verify(0, VerificationSettings('test'))
        with patch('context_audit.app.session.verify_selected', side_effect=ApplicationError('failed')):
            with self.assertRaises(ApplicationError):
                self.session.verify(0, VerificationSettings('test'))
        self.assertEqual(self.session.reviewed_finding_ids, {'stable-id'})
        self.assertEqual(len(self.session.history), 1)
        self.session.clear()
        self.assertEqual(self.session.reviewed_finding_ids, set())
        self.assertIsNone(self.session.exported_result)

    def test_missing_legacy_id_has_stable_fallback(self):
        finding = replace(sample_finding(), id='')
        self.assertEqual(finding_key(finding), finding_key(replace(finding)))
        self.assertNotEqual(finding_key(finding), finding_key(replace(finding, function_signature='other()')))

    def test_hot_reload_preserves_legacy_review_without_new_calls(self):
        self.session.latest = {0: sample_report()}
        self.session.history = [sample_report()]
        del self.session.reviewed_finding_ids
        del self.session.exported_result
        with patch('context_audit.app.session.verify_selected') as verify:
            upgraded = upgrade_session(self.session)
        self.assertEqual(upgraded.reviewed_finding_ids, {'stable-id'})
        self.assertIn('stable-id', upgraded.latest)
        self.assertEqual(json.loads(upgraded.exported_result)['schema_version'], 2)
        verify.assert_not_called()
