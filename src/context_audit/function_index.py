"""Compiler-backed source navigation. Edges are not execution or security proofs."""
import copy
from collections import deque

from slither.core.declarations import Function, Modifier, SolidityFunction
from slither.slithir.operations import InternalDynamicCall, LibraryCall

VERSION = 'function-index-v1'


def build_index(parsed, catalog, failures, safe_source):
    nodes = {}
    elements = {}
    element_ids = {}
    pending = deque()

    def reference(element):
        # Resolve compiler objects and source spans, never names or text similarity.
        if not hasattr(element, 'source_mapping') or not safe_source(element):
            return None
        if getattr(element, 'is_constructor_variables', False):
            return None
        if isinstance(element, Modifier):
            kind = 'modifier'
        elif isinstance(element, Function):
            kind = 'function'
        else:
            return None
        fid = catalog.add(element, kind, element.full_name)
        if fid not in nodes:
            nodes[fid] = dict(fragment_id=fid, kind=kind, signature=element.full_name,
                declared_in=element.contract_declarer.name, implemented=element.is_implemented,
                visibility=element.visibility, outgoing=[], incoming=[], modifiers=[],
                unresolved_calls=[], state_reads=None, state_writes=None,
                outgoing_complete=True, callers_complete=False)
            pending.append(fid)
        if id(element) not in element_ids.setdefault(fid, set()):
            elements.setdefault(fid, []).append(element)
            element_ids[fid].add(id(element))
        return fid

    for contract in parsed.contracts:
        for element in [*contract.functions, *contract.modifiers]:
            reference(element)

    # All referenced source functions normally exist in parsed.contracts; the
    # queue also includes compiler-resolved imported/library targets if needed.
    visited = set()
    while pending:
        fid = pending.popleft()
        if fid in visited:
            continue
        visited.add(fid)
        node = nodes[fid]
        edges = {}
        unknown = set()
        reads, writes = set(), set()
        state_complete = True
        for element in list(elements[fid]):
            for modifier in element.modifiers:
                target = reference(modifier)
                if target:
                    node['modifiers'].append(target)
                    edges[(target, 'modifier')] = dict(fragment_id=target, relation='modifier', resolution='source_span')
                else:
                    unknown.add('MODIFIER_SOURCE_UNAVAILABLE')
            if id(element) in failures or not element.is_implemented:
                node['outgoing_complete'] = False
                state_complete = False
                unknown.add('IR_UNAVAILABLE' if id(element) in failures else 'DECLARATION_WITHOUT_IMPLEMENTATION')
                continue
            try:
                for values, destination in ((element.state_variables_read, reads), (element.state_variables_written, writes)):
                    for variable in values:
                        if safe_source(variable):
                            destination.add(catalog.add(variable, 'state_variable', variable.canonical_name))
                        else:
                            unknown.add('STATE_SOURCE_UNAVAILABLE')
                            state_complete = False
                for call in element.internal_calls:
                    called = getattr(call, 'function', None)
                    if isinstance(called, SolidityFunction):
                        continue
                    target = reference(called)
                    if target:
                        if target not in node['modifiers']:
                            edges[(target, 'internal_call')] = dict(fragment_id=target, relation='internal_call', resolution='source_span')
                    else:
                        unknown.add('INTERNAL_TARGET_UNRESOLVED')
                for _, call in element.high_level_calls:
                    if isinstance(call, LibraryCall):
                        continue
                    target_element = getattr(call, 'function', None)
                    target = reference(target_element)
                    if target:
                        # An interface/contract declaration identifies the source
                        # selected by the compiler, not deployed address behavior.
                        edges[(target, 'external_call')] = dict(fragment_id=target, relation='external_call', resolution='declared_target_runtime_unknown')
                        unknown.add('EXTERNAL_RUNTIME_IMPLEMENTATION_UNKNOWN')
                    else:
                        unknown.add('EXTERNAL_TARGET_UNRESOLVED')
                if any(isinstance(ir, InternalDynamicCall) for ir in element.slithir_operations):
                    unknown.add('DYNAMIC_INTERNAL_TARGET_UNKNOWN')
                if element.low_level_calls:
                    unknown.add('LOW_LEVEL_RUNTIME_TARGET_UNKNOWN')
                for call in getattr(element, 'library_calls', []):
                    target = reference(getattr(call, 'function', None))
                    if target:
                        edges[(target, 'library_call')] = dict(fragment_id=target, relation='library_call', resolution='source_span')
                    else:
                        unknown.add('LIBRARY_TARGET_UNRESOLVED')
            except (AttributeError, TypeError, ValueError):
                unknown.add('CALL_METADATA_UNAVAILABLE')
                node['outgoing_complete'] = False
                state_complete = False
        node['state_reads'] = sorted(reads) if state_complete else None
        node['state_writes'] = sorted(writes) if state_complete else None
        node['modifiers'] = sorted(set(node['modifiers']))
        node['outgoing'] = [edges[key] for key in sorted(edges)]
        node['unresolved_calls'] = sorted(unknown)
        if unknown:
            node['outgoing_complete'] = False

    complete = all(n['outgoing_complete'] for n in nodes.values())
    for fid, node in nodes.items():
        for edge in node['outgoing']:
            nodes[edge['fragment_id']]['incoming'].append(dict(fragment_id=fid,
                relation=edge['relation'], resolution=edge['resolution']))
    for node in nodes.values():
        node['incoming'] = sorted(node['incoming'], key=lambda e: (e['fragment_id'], e['relation']))
        node['callers_complete'] = complete
    state_writers = {}
    for fid, node in nodes.items():
        for variable in node['state_writes'] or []:
            state_writers.setdefault(variable, []).append(fid)
    return dict(version=VERSION, scope='indexed_source_only', runtime_reachability_proven=False,
                nodes={fid: nodes[fid] for fid in sorted(nodes)},
                state_writers={fid: sorted(writers) for fid, writers in sorted(state_writers.items())})


def wire_node(node):
    """Whitelist metadata; no paths, arbitrary strings, source or audit labels."""
    keys = ('fragment_id', 'kind', 'signature', 'declared_in', 'implemented', 'visibility',
            'outgoing_complete', 'callers_complete', 'unresolved_calls', 'state_reads', 'state_writes')
    result = {k: copy.deepcopy(node[k]) for k in keys if k in node}
    result['modifiers'] = list(node.get('modifiers', []))
    for direction in ('outgoing', 'incoming'):
        result[direction] = [{k: e[k] for k in ('fragment_id', 'relation', 'resolution')}
                             for e in node.get(direction, [])]
    return result


def relationship_view(index, seen):
    if not index:
        return dict(version=None, scope='unavailable', runtime_reachability_proven=False, nodes=[])
    return dict(version=index['version'], scope='indexed_source_only', runtime_reachability_proven=False,
                nodes=[wire_node(index['nodes'][fid]) for fid in sorted(seen) if fid in index['nodes']])


def context_menu(index, seen, entries):
    """Prioritize graph neighbors without delivering or authorizing their source.

    The existing fragment/token/round limits are applied before this function.
    No source is automatically added. Traversal is bounded by the finite index
    and visited IDs, including recursion and shared callees.
    """
    if not index:
        return entries
    nodes = index['nodes']
    distances = {fid: 0 for fid in seen}
    reasons = {}
    queue = deque(sorted(seen))
    while queue:
        fid = queue.popleft()
        node = nodes.get(fid, {})
        links = [(e['fragment_id'], e['relation']) for e in node.get('outgoing', [])]
        links += [(e['fragment_id'], 'caller') for e in node.get('incoming', [])]
        links += [(target, 'state_declaration') for target in set((node.get('state_reads') or []) + (node.get('state_writes') or []))]
        links += [(target, 'state_writer') for target in index.get('state_writers', {}).get(fid, [])]
        for target, relation in links:
            if target not in distances:
                distances[target] = distances[fid] + 1
                queue.append(target)
            if distances[target] == distances[fid] + 1:
                reasons.setdefault(target, set()).add(relation)
    result = []
    for entry in entries:
        item = dict(entry)
        if entry['id'] in distances:
            item.update(relationship_distance=distances[entry['id']],
                        relationship_roles=sorted(reasons.get(entry['id'], set())))
        result.append(item)
    return sorted(result, key=lambda item: (distances.get(item['id'], float('inf')), item['id']))
