"""Regression coverage for per-label attribution and overloaded functions."""
import unittest
from unittest.mock import patch
from context_audit.direct_evaluation import evaluate, render_markdown


def session(signature, verdict, swc=None, lines=(54, 55, 61)):
    return {'dataset_file': 'C.sol', 'target': {'id': signature, 'signature': signature, 'lines': list(lines)},
            'assessment': {'verdict': verdict, 'findings': [{'swc_id': swc, 'vulnerability_type': 'test issue'}] if verdict=='vulnerable' else []},
            'round_count': 1, 'requested_fragments': 0, 'usage': {'total_tokens': 10}}


class EvaluationTests(unittest.TestCase):
    def evaluate(self, sessions, function='deposit(address,uint256)', lines=None, swc='SWC-107'):
        label = {'function': function, 'lines': lines or [], 'swc_id': swc}
        with patch('context_audit.direct_evaluation.aggregate', return_value=[]):
            return evaluate([{'file': 'C.sol', 'labels': [label]}], sessions)

    def test_wrong_swc_is_missed_and_additional(self):
        report = self.evaluate([session('deposit(address,uint256)', 'vulnerable', 'SWC-114')])
        self.assertEqual(report['labels'][0]['status'], 'MISSED')
        self.assertEqual(report['additional_findings'][0]['status'], 'ADDITIONAL_UNLABELED_FINDING')
        self.assertEqual(report['metrics']['additional_unlabeled_findings'], 1)

    def test_clean_is_missed(self):
        self.assertEqual(self.evaluate([session('deposit(address,uint256)', 'no_vulnerability_found')])['labels'][0]['status'], 'MISSED')

    def test_matching_is_detected(self):
        report = self.evaluate([session('deposit(address,uint256)', 'vulnerable', 'SWC-107')])
        self.assertEqual(report['labels'][0]['status'], 'DETECTED')
        self.assertEqual(report['additional_findings'], [])
        self.assertIn('DETECTED', render_markdown(report))

    def test_relevant_inconclusive(self):
        self.assertEqual(self.evaluate([session('deposit(address,uint256)', 'inconclusive')])['labels'][0]['status'], 'INCONCLUSIVE')

    def test_unrelated_inconclusive_does_not_change_miss(self):
        report = self.evaluate([session('deposit(address,uint256)', 'vulnerable'), session('transfer(address)', 'inconclusive')])
        self.assertEqual(report['labels'][0]['status'], 'MISSED')

    def test_exact_overloads(self):
        report = self.evaluate([session('deposit(address)', 'vulnerable', 'SWC-107'), session('deposit(address,uint256)', 'no_vulnerability_found')])
        self.assertEqual(report['labels'][0]['status'], 'MISSED')

    def test_bare_name_resolved_by_lines(self):
        sessions = [session('deposit(address,uint256)', 'vulnerable'), session('deposit(address)', 'vulnerable', 'SWC-114', (66,67,73)), session('other()', 'inconclusive')]
        for lines, swc, expected in [([53,54,61], 'SWC-107', 'MISSED'), ([65,66,73], 'SWC-107', 'MISSED'), ([65,66,73], 'SWC-114', 'DETECTED')]:
            with self.subTest(swc=swc, lines=lines):
                self.assertEqual(self.evaluate(sessions, 'deposit', lines, swc)['labels'][0]['status'], expected)

    def test_ambiguous_bare_overload_not_detected(self):
        report = self.evaluate([session('deposit(address)', 'vulnerable', 'SWC-107'), session('deposit(address,uint256)', 'no_vulnerability_found')], 'deposit')
        self.assertEqual(report['labels'][0]['resolution'], 'ambiguous_overload')
        self.assertEqual(report['metrics']['detected'], 0)

    def test_other_file_cannot_match(self):
        result = session('deposit(address,uint256)', 'vulnerable', 'SWC-107'); result['dataset_file'] = 'other.sol'
        self.assertEqual(self.evaluate([result])['metrics']['detected'], 0)

    def protocol_abstention(self, signature, mode, lines):
        result = session(signature, 'inconclusive', lines=lines)
        result['target']['preparation_mode'] = mode
        result['errors'] = ['Already supplied fragment requested']
        result['rounds'] = [{'result': {'assessment': {'action': 'request_context', 'requested_ids': ['helper']}}}]
        return result

    def test_full_index_protocol_inconclusive(self):
        result = self.protocol_abstention('exchange(uint256,uint256)', 'FULL_INDEX', range(167,174))
        report = self.evaluate([result], 'exchange', [172], 'SWC-115')
        self.assertEqual(report['labels'][0]['status'], 'INCONCLUSIVE')
        self.assertEqual(report['metrics']['evaluation_coverage'], 1)
        self.assertEqual(report['metrics']['analyzed_files'], 1)
        self.assertTrue(report['labels'][0]['relevant_sessions'][0]['errors'])

    def test_fallback_protocol_inconclusive(self):
        result = self.protocol_abstention('create()', 'SOURCE_FALLBACK', range(125,136))
        report = self.evaluate([result], 'create', [129], 'SWC-115')
        self.assertEqual(report['labels'][0]['status'], 'INCONCLUSIVE')
        self.assertEqual(report['labels'][0]['target_preparation_modes'], ['SOURCE_FALLBACK'])

    def test_fallback_unmatched_is_missed(self):
        result = session('create()', 'vulnerable', 'SWC-107', [129])
        result['target']['preparation_mode'] = 'SOURCE_FALLBACK'
        report = self.evaluate([result], 'create()', [129], 'SWC-115')
        self.assertEqual(report['labels'][0]['status'], 'MISSED')
        self.assertEqual(len(report['additional_findings']), 1)

    def test_fallback_match_is_detected(self):
        result = session('create()', 'vulnerable', 'SWC-115', [129])
        result['target']['preparation_mode'] = 'SOURCE_FALLBACK'
        self.assertEqual(self.evaluate([result], 'create()', [129], 'SWC-115')['labels'][0]['status'], 'DETECTED')

    def test_absent_session_unevaluable(self):
        self.assertEqual(self.evaluate([], 'create', [129])['labels'][0]['status'], 'UNEVALUABLE')

    def test_transport_failure_without_response_unevaluable(self):
        result = session('create()', 'inconclusive', lines=[129])
        result['errors'] = ['Connection failure']
        result['rounds'] = []
        self.assertEqual(self.evaluate([result], 'create', [129])['labels'][0]['status'], 'UNEVALUABLE')

    def test_fallback_bare_name_line_overlap_isolates_overloads(self):
        a = self.protocol_abstention('exchange(uint256)', 'SOURCE_FALLBACK', [20,21])
        b = session('exchange(uint256,uint256)', 'no_vulnerability_found', lines=[167,172,173])
        self.assertEqual(self.evaluate([a,b], 'exchange', [172])['labels'][0]['status'], 'MISSED')
        self.assertEqual(self.evaluate([a,b], 'exchange(uint256,uint256)')['labels'][0]['status'], 'MISSED')
