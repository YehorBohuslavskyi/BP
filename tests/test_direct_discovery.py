"""Offline compiler and mocked transport coverage for discovery; no API calls."""
import copy
import json
from unittest.mock import patch

import unittest
import tempfile
from slither.core.declarations import Function
from context_audit import direct_discovery as d
from context_audit.direct import prepare as prepare_v1


def prepared(tmp_path):
    source = tmp_path / 'Example.sol'
    source.write_text('''pragma solidity ^0.4.25;
contract Base { uint public balance = 1; function deposit() public payable { balance += msg.value; } }
contract Vault is Base {
 modifier auth() { require(msg.sender == address(1)); _; }
 // SWC-107 DAppSCAN ground truth Reentrancy: L8
 function withdraw(uint amount) public auth { msg.sender.call.value(amount)(""); balance -= amount; }
 function withdraw() public { withdraw(balance); }
}''')
    contracts, catalog = d.prepare(source)
    return source, contracts, catalog


def response(batch, candidates=None):
    return {'assessment': {'examined_functions': [{'fragment_id': f['fragment_id'], 'reason': 'Needs source review'} for f in batch['functions']], 'candidates': candidates or []},
            'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}


def candidate(batch):
    f = batch['functions'][0]
    return dict(candidate_id='one', contract=batch['contract'], primary_function=f['signature'],
                primary_fragment_id=f['fragment_id'], suspected_type='Accounting', reason='Shared state needs review',
                related_fragment_ids=[], requested_context_ids=[f['fragment_id']], uncertainty='Source ordering unknown')


def check_structure_determinism_inheritance_overloads_calls(prepared):
    source, contracts, catalog = prepared
    assert d.prepare(source)[0] == contracts
    vault = next(c for c in contracts if c['contract'] == 'Vault')
    assert vault['inherits'] == ['Base']
    funcs = {f['signature']: f for f in vault['functions']}
    assert {'withdraw()', 'withdraw(uint256)', 'deposit()'} <= funcs.keys()
    assert funcs['deposit()']['declared_in'] == 'Base'
    w = funcs['withdraw(uint256)']
    assert w['state_reads'] == w['state_writes'] == ['balance']
    assert w['modifiers'][0]['name'] == 'auth()'
    assert w['low_level_calls'] == ['msg.sender.call']
    assert w['external_calls'] == []
    assert 'withdraw(uint256)' in funcs['withdraw()']['internal_calls']
    assert w['state_dependencies'][0]['direct_writers']
    assert all(fid in catalog.fragments for fid in d.referenced_ids(contracts))
    assert 'source"' not in json.dumps(contracts)
    assert 'slitherConstructor' not in json.dumps(catalog.fragments)
    assert 'slitherConstructor' not in json.dumps(contracts)


def check_offline_and_no_leakage(prepared):
    _, contracts, catalog = prepared
    with patch.object(d, 'OpenAI', side_effect=AssertionError('API forbidden')):
        result = d.run_discovery(contracts, catalog)
    assert result['usage']['api_calls'] == 0
    assert result['coverage_counts']['included'] == result['coverage_counts']['total_functions']
    for batch in result['batches']:
        batch['ground_truth'] = 'SECRET'
        batch['functions'][0]['source'] = 'SECRET'
        text = json.dumps(d.messages(batch))
        assert 'SECRET' not in text
        assert 'SWC-107' not in text
        assert 'DAppSCAN' not in text
    assert 'SWC-107' not in json.dumps(catalog.fragments)


def check_complete_empty_coverage_usage(prepared):
    _, contracts, catalog = prepared
    result = d.run_discovery(contracts, catalog, execute=True, analyze_fn=response)
    assert not result['errors']
    assert result['coverage_counts']['not_selected'] == result['coverage_counts']['total_functions']
    assert result['coverage_counts']['examined'] == result['coverage_counts']['total_functions']
    assert result['usage']['total_tokens'] == 15 * len(result['batches'])
    assert not result['candidates']
    assert 'not classified as safe' in d.markdown(result)


def check_batching_and_explicit_limits(prepared):
    _, contracts, _ = prepared
    contract = copy.deepcopy(contracts[-1])
    contract['functions'] *= 40
    limit = max(len(d.encoded({**{k: contract[k] for k in ('contract', 'file', 'inherits')}, 'functions': [f]})) for f in contract['functions'])
    batches, coverage = d.make_batches([contract], limit)
    assert len(batches) > 1
    assert sum(len(b['functions']) for b in batches) == len(coverage)
    assert all(len(d.encoded(b)) <= limit for b in batches)
    batches, coverage = d.make_batches([contract], 256)
    assert not batches
    assert all(r['status'] == 'unevaluable' for r in coverage)


def check_protocol_rejects(prepared, fault):
    _, contracts, catalog = prepared
    def mock(batch):
        c = candidate(batch)
        r = response(batch, [c])
        if fault == 'unknown': c['requested_context_ids'] = ['fabricated']
        if fault == 'wrong_signature': c['primary_function'] = 'fake()'
        if fault == 'wrong_contract': c['contract'] = 'Fake'
        if fault == 'duplicate_id': r['assessment']['candidates'].append(dict(c))
        if fault == 'duplicate_candidate': r['assessment']['candidates'].append({**c, 'candidate_id': 'two'})
        if fault == 'missing_examined': r['assessment']['examined_functions'] = []
        if fault == 'duplicate_examined': r['assessment']['examined_functions'] *= 2
        if fault == 'malformed': r['assessment'] = {'unexpected': True}
        if fault == 'incomplete': r['status'] = 'incomplete'
        return r
    result = d.run_discovery(contracts, catalog, execute=True, analyze_fn=mock)
    assert result['errors']
    assert result['coverage_counts']['examined'] == 0
    assert result['coverage_counts']['unevaluable'] == result['coverage_counts']['total_functions']
    assert result['usage']['total_tokens'] > 0
    assert not result['candidates']


def check_valid_candidates_unique_ids(prepared):
    _, contracts, catalog = prepared
    result = d.run_discovery(contracts, catalog, execute=True, analyze_fn=lambda b: response(b, [candidate(b)]))
    assert not result['errors']
    assert result['coverage_counts']['selected'] > 0
    ids = [c['candidate_id'] for c in result['candidates']]
    assert len(ids) == len(set(ids))


def check_source_fallback(prepared):
    source, _, _ = prepared
    original = Function.generate_slithir_and_analyze
    def fail(f):
        if f.name == 'withdraw': raise ValueError('IR failure')
        return original(f)
    with patch.object(Function, 'generate_slithir_and_analyze', fail):
        contracts, _ = d.prepare(source)
    rows = [f for c in contracts for f in c['functions'] if f['signature'].startswith('withdraw')]
    assert rows
    for row in rows:
        assert row['preparation_mode'] == 'SOURCE_FALLBACK'
        assert row['state_reads'] is None
        assert row['internal_calls'] is None
        assert row['lines'] and row['fragment_id']
    assert next(r for r in rows if r['signature'] == 'withdraw(uint256)')['modifiers']


def check_v1_unchanged(prepared):
    source, _, _ = prepared
    before, catalog = prepare_v1(source)
    assert not hasattr(catalog, 'discovery_contracts')
    d.prepare(source)
    after, _ = prepare_v1(source)
    assert before == after


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.prepared = prepared(Path(self.temp.name))


def attach(test):
    def run(self):
        test(self.prepared)
    setattr(DiscoveryTests, test.__name__.replace('check_', 'test_', 1), run)


for name, test in list(globals().items()):
    if name.startswith('check_') and name != 'check_protocol_rejects':
        attach(test)

for fault in ['unknown', 'wrong_signature', 'wrong_contract', 'duplicate_id', 'duplicate_candidate', 'missing_examined', 'duplicate_examined', 'malformed', 'incomplete']:
    def run(self, fault=fault):
        check_protocol_rejects(self.prepared, fault)
    setattr(DiscoveryTests, 'test_protocol_' + fault, run)


class DiscoveryIntegrationTests(unittest.TestCase):
    def test_external_and_solidity_reads(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'C.sol'
            source.write_text('''pragma solidity ^0.4.25;
contract Token { function transfer(address to, uint n) public returns(bool); }
contract C { function send(Token t) public { require(tx.origin == msg.sender); t.transfer(msg.sender, 1); } }''')
            contracts, _ = d.prepare(source)
            row = next(c for c in contracts if c['contract'] == 'C')['functions'][0]
            self.assertEqual(row['external_calls'], ['Token.transfer(address,uint256)'])
            self.assertIn('tx.origin', row['solidity_reads'])

    def test_unsafe_mapping_recorded(self):
        from pathlib import Path
        from context_audit.direct import safe_source
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'C.sol'
            source.write_text('pragma solidity ^0.4.25; contract C { function f() public {} }')
            with patch('context_audit.direct.safe_source', side_effect=lambda e: e.name != 'f' and safe_source(e)):
                contracts, catalog = d.prepare(source)
            result = d.run_discovery(contracts, catalog)
            self.assertEqual(result['coverage_counts']['total_functions'], 1)
            self.assertEqual(result['coverage_counts']['unevaluable'], 1)

    def test_cli_offline_and_preserves_outputs(self):
        import runpy
        import sys
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _, _ = prepared(root)
            argv = ['run_direct_discovery.py', str(source), '--output', str(root / 'out')]
            with patch.object(sys, 'argv', argv), patch.object(d, 'OpenAI', side_effect=AssertionError('Forbidden API')):
                runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')
                result = json.loads((root / 'out/discovery.json').read_text())
                self.assertEqual(result['usage']['api_calls'], 0)
                self.assertTrue((root / 'out/summary.md').is_file())
                with self.assertRaises(SystemExit):
                    runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')

    def test_transport_model_and_usage(self):
        from types import SimpleNamespace
        batch = {'contract': 'C', 'inherits': [], 'functions': []}
        parsed = d.DiscoveryResponse(examined_functions=[], candidates=[])
        transport = SimpleNamespace(status='completed', output_parsed=parsed, model='mock', id='r',
                                    usage=SimpleNamespace(model_dump=lambda: {'total_tokens': 12}))
        with patch.dict('os.environ', {'OPENAI_MODEL': 'mock'}), patch.object(d, 'OpenAI') as client:
            client.return_value.responses.parse.return_value = transport
            result = d.analyze(batch)
            self.assertEqual(result['usage']['total_tokens'], 12)
            self.assertEqual(client.return_value.responses.parse.call_args.kwargs['model'], 'mock')
            self.assertFalse(client.return_value.responses.parse.call_args.kwargs['store'])
