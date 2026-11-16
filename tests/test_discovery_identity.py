"""Strict identity resolution, including the saved real discovery protocol failure."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from context_audit import direct_discovery as d
from test_direct_discovery import prepared, candidate, response


class DiscoveryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.source, self.contracts, self.catalog = prepared(Path(self.temp.name))
        self.batch = next(b for b in d.make_batches(self.contracts)[0] if b['contract'] == 'Vault')
        self.row = next(f for f in self.batch['functions'] if f['signature'] == 'withdraw(uint256)')
        self.c = candidate(self.batch)
        self.c.update(primary_function=self.row['signature'], primary_fragment_id=self.row['fragment_id'],
                      requested_context_ids=[self.row['fragment_id']])

    def validate(self, c, **kw):
        return d.validate_response(response(self.batch, [c])['assessment'], self.batch, self.catalog, **kw)

    def test_canonical_unchanged(self):
        self.assertEqual(self.validate(self.c).candidates[0].model_dump(), self.c)

    def test_contract_qualified_signature(self):
        c = {**self.c, 'contract': 'Vault.withdraw(uint256)'}
        diagnostics = []
        parsed = self.validate(c, candidate_diagnostics=diagnostics)
        self.assertEqual(parsed.candidates[0].contract, 'Vault')
        self.assertEqual(diagnostics[0]['original_identity']['contract'], c['contract'])
        self.assertEqual(c['contract'], 'Vault.withdraw(uint256)')

    def test_qualified_primary_function(self):
        parsed = self.validate({**self.c, 'primary_function': 'Vault.withdraw(uint256)'})
        self.assertEqual(parsed.candidates[0].primary_function, 'withdraw(uint256)')

    def test_overload_cannot_be_substituted(self):
        self.validate({**self.c, 'contract': 'Vault.withdraw(uint256)'})
        with self.assertRaises(ValueError): self.validate({**self.c, 'contract': 'Vault.withdraw()'})

    def test_inherited_declaring_contract_alias(self):
        row = next(f for f in self.batch['functions'] if f['signature'] == 'deposit()')
        c = {**self.c, 'contract': 'Base.deposit()', 'primary_function': 'deposit()',
             'primary_fragment_id': row['fragment_id']}
        self.assertEqual(self.validate(c).candidates[0].contract, 'Vault')
        with self.assertRaises(ValueError): self.validate({**c, 'contract': 'Base'})

    def test_unknown_contract(self):
        for name in ['Unknown', 'Unknown.withdraw(uint256)', 'Vault.Unknown.withdraw(uint256)']:
            with self.subTest(name=name), self.assertRaises(ValueError): self.validate({**self.c, 'contract': name})

    def test_mismatched_fragment(self):
        other = next(f for f in self.batch['functions'] if f['signature'] == 'withdraw()')
        with self.assertRaises(ValueError): self.validate({**self.c, 'primary_fragment_id': other['fragment_id']})
        with self.assertRaises(ValueError): self.validate({**self.c, 'primary_fragment_id': 'fragment-fabricated'})

    def test_ambiguous_alias(self):
        duplicate = {**self.row, 'fragment_id': 'fragment-other'}
        self.batch['functions'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'):
            self.validate({**self.c, 'contract': 'Vault.withdraw(uint256)'})

    def test_inaccessible_related_id_rejected(self):
        with self.assertRaises(ValueError): self.validate({**self.c, 'related_fragment_ids': ['fragment-fabricated']})

    def test_mixed_candidates_isolate_invalid_and_preserve_originals(self):
        raw = response(self.batch, [self.c, {**self.c, 'candidate_id': 'bad', 'contract': 'Unknown'}])['assessment']
        diagnostics = []
        accepted = d.validate_response(raw, self.batch, self.catalog, candidate_diagnostics=diagnostics)
        self.assertEqual(len(accepted.candidates), 1)
        self.assertEqual([r['status'] for r in diagnostics], ['accepted', 'rejected'])
        self.assertEqual(diagnostics[1]['original_identity']['contract'], 'Unknown')

    def test_mixed_run_keeps_coverage_and_reports_rejection(self):
        def mock(batch):
            good = candidate(batch)
            return response(batch, [good, {**good, 'candidate_id': 'bad', 'contract': 'Unknown'}])
        result = d.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=mock)
        self.assertEqual(result['coverage_counts']['examined'], result['coverage_counts']['total_functions'])
        self.assertTrue(result['candidates'])
        self.assertTrue(all(e['error'] == 'DISCOVERY_CANDIDATE_REJECTED' for e in result['errors']))

    def test_duplicate_ids_reject_both_without_guessing(self):
        raw = response(self.batch, [self.c, {**self.c, 'reason': 'different'}])['assessment']
        diag = []
        with self.assertRaises(ValueError): d.validate_response(raw, self.batch, self.catalog, candidate_diagnostics=diag)
        self.assertEqual([r['status'] for r in diag], ['rejected', 'rejected'])

    def test_saved_actual_response_resolves_all_three(self):
        path = Path('runs/mode-b-v2-development-2026-11-09/ixo-authoriser/b2/analysis/discovery.json')
        saved = json.loads(path.read_text())
        plan = json.loads(Path('experiments/mode-b-v2-development-2026-11-09/prepared/ixo-authoriser/b2-plan.json').read_text())
        contracts, catalog = d.prepare(Path(plan['source']))
        # Source bytes stay fixed; the richer index is a new protocol identity.
        self.assertEqual(catalog.source_identity['source_sha256'], saved['manifest']['source']['source_sha256'])
        self.assertNotEqual(catalog.source_identity, saved['manifest']['source'])
        from context_audit.v2_artifacts import validate_discovery
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            validate_discovery(saved, contracts, catalog)
        batch = d.make_batches(contracts)[0][0]
        original = saved['rounds'][0]['response']['assessment']
        self.assertEqual([c['contract'] for c in original['candidates']], [
            'ProjectWalletAuthoriser.setAuthoriser(address)',
            'ProjectWalletAuthoriser.transfer(address,address,uint256)', 'Ownable._transferOwnership(address)'])
        before = copy.deepcopy(original); diagnostics = []
        accepted = d.validate_response(original, batch, catalog, candidate_diagnostics=diagnostics)
        self.assertEqual(len(accepted.candidates), 3)
        self.assertTrue(all(c.contract == 'ProjectWalletAuthoriser' for c in accepted.candidates))
        self.assertEqual(original, before)

    def test_prompt_separates_identity_fields(self):
        self.assertIn('contract MUST equal the exact canonical contract', d.SYSTEM_PROMPT)
        self.assertIn('primary_function MUST be the full signature', d.SYSTEM_PROMPT)
        self.assertIn('primary_fragment_id MUST be', d.SYSTEM_PROMPT)
