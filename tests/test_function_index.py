"""Real compiler graphs and mocked selective retrieval; never model/GT calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from slither.core.declarations import Function
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.function_index import context_menu, wire_node
from context_audit.v2_artifacts import digest, validate_discovery
from test_direct_discovery import prepared, response
from test_direct_verification import request, final


class FunctionIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.contracts, self.catalog = prepared(self.root)
        self.nodes = self.catalog.function_index['nodes']

    def node(self, signature, owner='Vault', catalog=None):
        nodes = (catalog or self.catalog).function_index['nodes']
        return next(n for n in nodes.values() if n['signature'] == signature and n['declared_in'] == owner)

    def candidate(self, node):
        return dict(candidate_id='offline', contract='Vault', primary_function=node['signature'],
                    primary_fragment_id=node['fragment_id'], suspected_type='Authorization',
                    reason='Check whether the caller path enforces authorization.', related_fragment_ids=[],
                    requested_context_ids=[], uncertainty='Caller guard source must be inspected.')

    def test_forward_reverse_links_resolve_exact_overload_and_modifier(self):
        caller, target, guard = self.node('withdraw()'), self.node('withdraw(uint256)'), self.node('auth()')
        edge = next(e for e in caller['outgoing'] if e['relation'] == 'internal_call')
        self.assertEqual(edge['fragment_id'], target['fragment_id'])
        self.assertIn(caller['fragment_id'], [e['fragment_id'] for e in target['incoming']])
        self.assertEqual(target['modifiers'], [guard['fragment_id']])
        self.assertEqual(self.catalog.fragments[guard['fragment_id']]['kind'], 'modifier')
        self.assertTrue(any(e['relation'] == 'modifier' for e in target['outgoing']))

    def test_inheritance_shares_source_identity_without_name_resolution(self):
        base = self.node('deposit()', 'Base')
        rows = [f for c in self.contracts for f in c['functions'] if f['signature'] == 'deposit()']
        self.assertEqual({r['fragment_id'] for r in rows}, {base['fragment_id']})
        self.assertEqual(len([n for n in self.nodes.values() if n['signature'] == 'deposit()']), 1)

    def test_state_declarations_and_writers_have_exact_source_links(self):
        node = self.node('withdraw(uint256)')
        self.assertTrue(node['state_reads'])
        for fid in node['state_reads']:
            self.assertEqual(self.catalog.get(fid)['kind'], 'state_variable')
            self.assertIn(node['fragment_id'], self.catalog.function_index['state_writers'][fid])

    def test_graph_is_deterministic_bound_to_source_identity_and_serialized(self):
        _, other = d.prepare(self.source)
        self.assertEqual(self.catalog.function_index, other.function_index)
        self.assertEqual(self.catalog.source_identity['function_index_sha256'], digest(self.catalog.function_index))
        saved = d.run_discovery(self.contracts, self.catalog)
        self.assertEqual(saved['function_index'], self.catalog.function_index)
        self.assertEqual(json.loads(json.dumps(saved))['function_index'], self.catalog.function_index)
        for node in self.nodes.values():
            self.assertEqual(node['fragment_id'], self.catalog.get(node['fragment_id'])['id'])
            for edge in node['outgoing'] + node['incoming']:
                self.assertIn(edge['fragment_id'], self.catalog.fragments)

    def test_failed_ir_is_unknown_not_empty_and_reverse_sets_are_incomplete(self):
        original = Function.generate_slithir_and_analyze
        def fail(element):
            if element.name == 'withdraw':
                raise ValueError('offline forced missing IR')
            return original(element)
        with patch.object(Function, 'generate_slithir_and_analyze', fail):
            _, catalog = d.prepare(self.source)
        node = self.node('withdraw(uint256)', catalog=catalog)
        self.assertIn('IR_UNAVAILABLE', node['unresolved_calls'])
        self.assertFalse(node['outgoing_complete'])
        self.assertIsNone(node['state_reads'])
        self.assertTrue(all(not n['callers_complete'] for n in catalog.function_index['nodes'].values()))

    def test_dynamic_calls_remain_unknown(self):
        node = self.node('withdraw(uint256)')
        self.assertIn('LOW_LEVEL_RUNTIME_TARGET_UNKNOWN', node['unresolved_calls'])
        self.assertFalse(self.catalog.function_index['runtime_reachability_proven'])
        self.assertFalse(node['callers_complete'])

    def test_external_interface_is_a_declaration_not_runtime_implementation(self):
        source = self.root / 'External.sol'
        source.write_text('pragma solidity 0.4.25; contract T { function send(uint n) public; } contract C { function pay(T t) public { t.send(1); } }')
        _, catalog = d.prepare(source)
        caller = self.node('pay(T)', 'C', catalog)
        edge = next(e for e in caller['outgoing'] if e['relation'] == 'external_call')
        target = catalog.function_index['nodes'][edge['fragment_id']]
        self.assertFalse(target['implemented'])
        self.assertEqual(edge['resolution'], 'declared_target_runtime_unknown')
        self.assertIn('EXTERNAL_RUNTIME_IMPLEMENTATION_UNKNOWN', caller['unresolved_calls'])

    def test_recursive_graph_has_bounded_traversal_and_keeps_unrelated_menu(self):
        source = self.root / 'Recursive.sol'
        source.write_text('pragma solidity 0.4.25; contract C { function a(uint n) internal { if(n>0) b(n-1); } function b(uint n) internal { if(n>0) a(n-1); } function unrelated() public {} }')
        _, catalog = d.prepare(source)
        node = self.node('a(uint256)', 'C', catalog)
        entries = [{k: f[k] for k in ('id', 'kind', 'name')} for f in catalog.fragments.values() if f['id'] != node['fragment_id']]
        menu = context_menu(catalog.function_index, {node['fragment_id']}, entries)
        self.assertEqual(len(menu), len(entries))
        self.assertEqual(len({e['id'] for e in menu}), len(menu))
        self.assertEqual(menu[0]['name'], 'b(uint256)')
        self.assertTrue(any(e['name'] == 'unrelated()' and 'relationship_distance' not in e for e in menu))

    def test_relationships_reach_both_discovery_and_verification_without_source_leak(self):
        batch = next(b for b in d.make_batches(self.contracts)[0] if b['contract'] == 'Vault')
        wire = json.loads(d.messages(batch)[1]['content'])
        self.assertTrue(all('relationships' in f for f in wire['functions']))
        node = self.node('withdraw()')
        candidate, row = v.validate_candidate(self.candidate(node), self.contracts, self.catalog)
        payload = v.payload_for(candidate, row, self.catalog)
        sent = json.loads(v.messages(payload, [])[1]['content'])
        self.assertEqual(len(sent['relationships']['nodes']), 1)
        self.assertEqual(sent['evidence_policy']['allowed_evidence_ids'], [node['fragment_id']])
        self.assertEqual(sent['provided_context'], [])
        self.assertEqual(sent['available_context'][0]['id'], self.node('withdraw(uint256)')['fragment_id'])
        self.assertEqual(sent['available_context'][0]['relationship_distance'], 1)
        self.assertNotIn('source', sent['relationships']['nodes'][0])
        self.assertTrue(all('source' not in e for e in sent['available_context']))

    def test_retrieved_caller_exposes_its_guard_for_next_request(self):
        node = self.node('withdraw(uint256)')
        caller = self.node('withdraw()')
        candidate, row = v.validate_candidate(self.candidate(caller), self.contracts, self.catalog)
        payload = v.payload_for(candidate, row, self.catalog)
        sent = json.loads(v.messages(payload, [v.safe_fragment(self.catalog.get(node['fragment_id']))])[1]['content'])
        self.assertEqual(len(sent['relationships']['nodes']), 2)
        guard = self.node('auth()')['fragment_id']
        entry = next(e for e in sent['available_context'] if e['id'] == guard)
        self.assertEqual(entry['relationship_distance'], 1)
        self.assertNotIn(guard, sent['evidence_policy']['allowed_evidence_ids'])

    def test_mocked_verifier_follows_pointers_then_cites_only_delivered_source(self):
        caller = self.node('withdraw()')
        target = self.node('withdraw(uint256)')
        guard = self.node('auth()')
        requests = []
        def verify(payload, supplied, **kwargs):
            wire = json.loads(v.messages(payload, supplied)[1]['content'])
            requests.append(wire)
            if not supplied:
                return request([target['fragment_id']])
            if len(supplied) == 1:
                return request([guard['fragment_id']])
            return final(payload, supplied, 'inconclusive')
        result = v.verify_candidate(self.candidate(caller), self.contracts, self.catalog,
            analyze_fn=verify, limits=v.Limits(max_rounds=3))
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['round_count'], 3)
        self.assertEqual(len(requests[0]['evidence_policy']['allowed_evidence_ids']), 1)
        self.assertEqual(len(requests[-1]['evidence_policy']['allowed_evidence_ids']), 3)
        self.assertIn(guard['fragment_id'], result['evidence_ids'])

    def test_source_budget_still_filters_linked_fragments(self):
        candidate, row = v.validate_candidate(self.candidate(self.node('withdraw()')), self.contracts, self.catalog)
        payload = v.payload_for(candidate, row, self.catalog)
        payload['retrieval_budget'] = dict(rounds_after_this=1, max_new_fragments=8, max_new_source_tokens=0)
        self.assertEqual(v.requestable_context(payload, []), [])

    def test_graph_tamper_blocks_discovery_reuse(self):
        saved = d.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=response)
        self.catalog.function_index['nodes'][self.node('withdraw()')['fragment_id']]['outgoing'] = []
        with self.assertRaisesRegex(ValueError, 'function index'):
            validate_discovery(saved, self.contracts, self.catalog)

    def test_wire_metadata_whitelist_excludes_injected_audit_or_source_fields(self):
        node = copy.deepcopy(self.node('withdraw()'))
        node.update(source='SECRET', path='SECRET', ground_truth='SECRET')
        self.assertNotIn('SECRET', json.dumps(wire_node(node)))


    def test_library_call_uses_compiler_object_and_exact_target_span(self):
        source = self.root / 'Library.sol'
        source.write_text('pragma solidity 0.4.25; library Math { function inc(uint n) internal pure returns(uint) { return n+1; } } contract C { using Math for uint; function add(uint n) public pure returns(uint) { return n.inc(); } }')
        _, catalog = d.prepare(source)
        caller = self.node('add(uint256)', 'C', catalog)
        target = self.node('inc(uint256)', 'Math', catalog)
        edges = [e for e in caller['outgoing'] if e['relation'] == 'library_call']
        self.assertEqual([e['fragment_id'] for e in edges], [target['fragment_id']])
        self.assertTrue(any(e['fragment_id'] == caller['fragment_id'] for e in target['incoming']))

    def test_same_signature_in_different_contracts_never_merges(self):
        source = self.root / 'Names.sol'
        source.write_text('pragma solidity 0.4.25; contract A { function helper(uint n) internal pure returns(uint) {return n;} function run(uint n) public pure returns(uint) {return helper(n);} } contract B { function helper(uint n) internal pure returns(uint) {return n+1;} function run(uint n) public pure returns(uint) {return helper(n);} }')
        _, catalog = d.prepare(source)
        targets = []
        for owner in ('A', 'B'):
            caller = self.node('run(uint256)', owner, catalog)
            target = self.node('helper(uint256)', owner, catalog)
            self.assertEqual([e['fragment_id'] for e in caller['outgoing']], [target['fragment_id']])
            targets.append(target['fragment_id'])
        self.assertNotEqual(*targets)

    def test_function_pointer_remains_dynamic_even_when_its_type_is_known(self):
        source = self.root / 'Pointer.sol'
        source.write_text('pragma solidity 0.4.25; contract C { function run(function(uint) internal returns(uint) callback, uint n) internal returns(uint) { return callback(n); } }')
        _, catalog = d.prepare(source)
        caller = next(n for n in catalog.function_index['nodes'].values() if n['signature'].startswith('run('))
        self.assertIn('DYNAMIC_INTERNAL_TARGET_UNKNOWN', caller['unresolved_calls'])
        self.assertFalse(caller['outgoing_complete'])

    def test_known_guard_and_missing_guard_remain_distinct_source_paths(self):
        source = self.root / 'Paths.sol'
        source.write_text('pragma solidity 0.4.25; contract C { modifier auth() {require(msg.sender==address(1));_;} function guarded() public auth {sendMoney();} function open() public {sendMoney();} function sendMoney() internal {} }')
        _, catalog = d.prepare(source)
        target = self.node('sendMoney()', 'C', catalog)
        callers = {catalog.function_index['nodes'][e['fragment_id']]['signature'] for e in target['incoming']}
        self.assertEqual(callers, {'guarded()', 'open()'})
        self.assertTrue(self.node('guarded()', 'C', catalog)['modifiers'])
        self.assertEqual(self.node('open()', 'C', catalog)['modifiers'], [])
        entries = [{k:f[k] for k in ('id','kind','name')} for f in catalog.fragments.values() if f['id'] != target['fragment_id']]
        menu = context_menu(catalog.function_index, {target['fragment_id']}, entries)
        immediate = [e for e in menu if e.get('relationship_distance') == 1]
        self.assertEqual({e['name'] for e in immediate}, {'guarded()', 'open()'})


if __name__ == '__main__':
    unittest.main()
