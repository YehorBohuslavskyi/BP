"""Optional integration checks for the user's pinned local CGT data copy."""
import json
import unittest
from collections import Counter
from pathlib import Path

from context_audit.cgt_archive import audit_archive
from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import load_reviewed_findings
from check_cgt_preflight import normalized_source, estimate_cohort

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'datasets/cgt'


@unittest.skipUnless((DATA/'consolidated.csv').exists(), 'Local CGT dataset is not installed')
class RealCGTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset=load_cgt(DATA)
        cls.archive=audit_archive(DATA,cls.dataset)

    def test_pinned_csv_and_complete_accounting(self):
        self.assertEqual(self.dataset.csv_sha256,'306f91a45c783494cbc9b6010c3e044ffcfcd9a67e80165f6d896528fa1d94ba')
        self.assertEqual(self.dataset.total_rows,20455)
        self.assertEqual(len(self.dataset.assessments),20455)
        self.assertEqual(Counter(a.original_label for a in self.dataset.assessments),{'t':5619,'f':14836})

    def test_all_referenced_sources_exist(self):
        self.assertEqual(Counter(a.source_status for a in self.dataset.assessments),{'available':19456,'not_provided':999})
        self.assertEqual(Counter(i['kind'] for i in self.dataset.issues),{'source_not_provided':999})
        self.assertEqual(len(list((DATA/'source').glob('*.sol'))),3103)

    def test_archived_slither_labels_are_separate_from_consolidated(self):
        self.assertEqual(len(self.archive),419)
        self.assertEqual(Counter(r['original_label'] for r in self.archive),{'TP':84,'FP':335})
        self.assertEqual(sum('label_conflict' in r['issues'] for r in self.archive),24)
        row=next(r for r in self.archive if r['file']=='test118.json' and r['category']=='tx_result')
        self.assertTrue(row['label'])
        self.assertFalse(row['consolidated_label'])
        self.assertIn('label_conflict',row['issues'])

    def test_one_to_many_groups_not_expanded(self):
        self.assertEqual(sum('ambiguous_warning_group' in r['issues'] for r in self.archive),191)
        row=next(r for r in self.archive if r['file']=='test2059.json' and r['category']=='tx_result')
        self.assertEqual(row['historical_warning_count'],2)
        self.assertEqual(row['status'],'unresolved')

    def test_mapping_selects_contract_and_detector(self):
        row=next(r for r in self.archive if r['file']=='test701.json' and r['category']=='tx_result')
        self.assertEqual(row['contract'],'Tokens')
        self.assertEqual(row['historical_warning_count'],1)
        self.assertEqual(row['detector'],'tx-origin')
        self.assertEqual(row['issues'],[])

    def test_review_manifest_matches_exact_fresh_artifacts(self):
        path=ROOT/'results/cgt_reviewed_baseline/reviews.json'
        if not path.exists():self.skipTest('Reviewed evidence not generated')
        accepted,errors=load_reviewed_findings(self.dataset,path)
        self.assertEqual(errors,[])
        self.assertEqual(len(accepted),27)
        self.assertEqual(sum(c.label for c in accepted),22)
        self.assertEqual(sum(not c.label for c in accepted),5)
        self.assertFalse(any(c.finding.detector=='calls-loop' for c in accepted))


class PreflightTests(unittest.TestCase):
    def test_string_literals_not_erased_by_source_equivalence(self):
        self.assertEqual(normalized_source('a(); //comment\nb();'),normalized_source('a(); b();'))
        self.assertNotEqual(normalized_source('emit E("a b");'),normalized_source('emit E("ab");'))
        self.assertNotEqual(normalized_source('uint ab;'),normalized_source('uint a b;'))

    def test_token_forecast_is_not_actual_api_usage(self):
        result=estimate_cohort([{'label':True,'initial_request_estimate':100,'all_context_request_estimate':400}])
        self.assertEqual(result['api_calls_min'],1)
        self.assertEqual(result['api_calls_max'],4)
        self.assertEqual(result['four_round_input_tokens_estimate_upper'],1600)
        self.assertEqual(result['output_tokens_configured_cap'],16000)
