"""Pure GUI helpers for finding eligibility, source accounting, and safe exports."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from collections.abc import Iterable

from context_audit.cgt_inference import estimated_tokens
from context_audit.findings import Finding


def compact_lines(lines: Iterable[int]) -> str:
    """Sort and deduplicate positive line numbers, collapsing contiguous runs."""
    values = sorted(set(lines))
    if any(type(line) is not int or line < 1 for line in values):
        raise ValueError('Source lines must be positive integers')
    ranges = []
    for line in values:
        if ranges and line == ranges[-1][1] + 1:
            ranges[-1][1] = line
        else:
            ranges.append([line, line])
    return ', '.join(str(first) if first == last else f'{first}-{last}' for first, last in ranges)


def finding_key(finding: Finding) -> str:
    """Use the analyzer ID, with a deterministic fallback for old JSON without IDs."""
    return finding.id or hashlib.sha256(json.dumps(asdict(finding), sort_keys=True).encode()).hexdigest()


def verification_ineligibility(finding: Finding, source: Path | None = None) -> str | None:
    """Gate function/modifier-scoped verification using target metadata, never detector names.

    This is a structural check, not a compilation guarantee. The core
    resolver still checks the exact contract/signature before any inference.
    """
    if not finding.function_signature:
        return 'No target function or modifier; this may be an informational or global finding.'
    if not finding.contract:
        return 'No target contract; unsupported source scope.'
    if not finding.file:
        return 'Missing source identity; the target cannot be resolved safely.'
    if finding.function_start is None or finding.function_length is None:
        return 'No target source range; unsupported source scope.'
    if finding.function_start < 0 or finding.function_length <= 0:
        return 'Invalid target source range.'
    if source is not None:
        candidate = Path(finding.file)
        matches = (candidate.resolve() == source.resolve() if candidate.is_absolute() or candidate.parent != Path('.')
                   else candidate.name == source.name)
        if not matches:
            return 'The target belongs to a different source file.'
    return None


def is_finding_verifiable(finding: Finding, source: Path | None = None) -> bool:
    """Return whether a warning carries a supported function/modifier-scoped target."""
    return verification_ineligibility(finding, source) is None


def requested_fragment_ids(result: dict, *, sent_only: bool = False) -> list[str]:
    """Collect unique requests in first-request order.

    A request in the last round was never supplied to a later model call. Keep
    it in request counts, but exclude it from selected-code transmission totals.
    """
    rounds = result.get('rounds', [])
    if sent_only:
        rounds = rounds[:-1]
    return list(dict.fromkeys(fragment_id for round_info in rounds
                             for fragment_id in round_info['result']['assessment'].get('requested_ids', [])))


def source_context_efficiency(full_source: str, payload: dict, result: dict) -> dict:
    """Measure source strings only; metadata and API usage never enter reduction.

    Each fragment ID is counted once, excluding repeated transmission in later
    rounds. Distinct overlapping fragments remain separate; their total can
    exceed the full source and the reduction is deliberately not clamped.
    """
    target = payload['target']
    full = estimated_tokens(full_source)
    initial = estimated_tokens(target['source'])
    sent = set(requested_fragment_ids(result, sent_only=True))
    unique = {fragment['id']: fragment for fragment in result.get('provided_context', [])
              if fragment['id'] in sent and fragment['id'] != target['id']}
    additional = sum(estimated_tokens(fragment['source']) for fragment in unique.values())
    total = initial + additional
    return {
        'full_source_estimated_tokens': full,
        'initial_selected_source_estimated_tokens': initial,
        'additional_selected_source_estimated_tokens': additional,
        'cumulative_selected_source_estimated_tokens': total,
        'source_context_reduction': 1 - total / full if full else None,
    }


def source_fragments(payload: dict, result: dict) -> list[dict]:
    """Join supplied source with its catalog metadata for evidence and export."""
    target = payload['target']
    metadata = {item['id']: item for item in payload.get('available_context', [])}
    sent_ids = set(requested_fragment_ids(result, sent_only=True)) | {target['id']}
    fragments = [dict(target, kind=target.get('kind', 'function'), name=target.get('signature', 'Target')),
                 *result.get('provided_context', [])]
    unique = {}
    for fragment in fragments:
        identity = fragment['id']
        info = metadata.get(identity, {})
        unique[identity] = {
            'id': identity, 'kind': fragment.get('kind', info.get('kind', 'source')),
            'name': fragment.get('name', info.get('name', identity)),
            'source': fragment['source'], 'reasons': list(info.get('reasons', [])),
            'sent_to_model': identity in sent_ids,
        }
    return list(unique.values())


def verification_export(report: dict) -> dict:
    """Export only public finding, assessment, fragment, and accounting fields."""
    result = report['result']
    assessment = result['assessment']
    finding = report.get('finding', result.get('finding', {}))
    requested = requested_fragment_ids(result)
    return {
        'finding': {**{key: finding.get(key) for key in
                       ('id', 'detector', 'impact', 'confidence', 'contract', 'lines', 'description')},
                    'function': finding.get('function_signature', finding.get('function'))},
        'verification': {
            'verdict': assessment['verdict'], 'explanation': assessment.get('explanation', ''),
            'evidence_ids': assessment.get('evidence_ids', []),
            'round_count': report['summary'].get('rounds', len(result.get('rounds', []))),
            'requested_fragment_ids': requested, 'requested_fragments': len(requested),
        },
        'usage': {key: report['summary'][key] for key in ('input_tokens', 'output_tokens', 'total_tokens')},
        'context_efficiency': report.get('context_efficiency', {}),
        'source_fragments': source_fragments(report['initial_payload'], result) if 'initial_payload' in report else [],
        'model': report.get('model'), 'compiler': report.get('compiler'),
        'rounds': [{'round': item['round'],
                    'action': item['result']['assessment']['action'],
                    'explanation': item['result']['assessment'].get('explanation', ''),
                    'requested_fragment_ids': item['result']['assessment'].get('requested_ids', []),
                    'evidence_ids': item['result']['assessment'].get('evidence_ids', [])}
                   for item in result.get('rounds', [])],
    }


def target_kind_label(source: str, finding: Finding) -> str:
    """Display declaration kind from its source range; core resolution is authoritative.

    Slither serializes modifiers as type=function, so the JSON tag is insufficient.
    """
    import re
    start, length = finding.function_start, finding.function_length
    if start is None or length is None or start < 0 or length <= 0:
        return "Unknown"
    declaration = source.encode("utf-8")[start:start + length].decode("utf-8", errors="replace")
    match = re.match(r"\s*(modifier|function|constructor|fallback|receive)\b", declaration)
    return ("Modifier" if match[1] == "modifier" else "Function") if match else "Unknown"


def target_function_lines(source: str, finding: Finding) -> list[int]:
    """Translate valid half-open UTF-8 function offsets for source display only."""
    encoded = source.encode('utf-8')
    start, length = finding.function_start, finding.function_length
    if start is None or length is None or start < 0 or length <= 0 or start + length > len(encoded):
        return []
    return list(range(encoded[:start].count(b'\n') + 1,
                      encoded[:start + length - 1].count(b'\n') + 2))


def marked_source_excerpt(source: str, finding: Finding, limit: int = 120) -> str:
    """Show original line numbers and explicit finding/function markers, without HTML."""
    lines = source.splitlines()
    finding_lines = set(finding.lines)
    function_lines = set(target_function_lines(source, finding))
    selected = {line + offset for line in finding_lines | function_lines for offset in range(-2, 3)
                if 1 <= line + offset <= len(lines)}
    output = []
    previous = 0
    for line in sorted(selected)[:limit]:
        if previous and line > previous + 1:
            output.append('    …')
        marker = '▶' if line in finding_lines else ('│' if line in function_lines else ' ')
        output.append(f'{marker} {line:4}  {lines[line - 1]}')
        previous = line
    if len(selected) > limit:
        output.append('    … More lines available in the full source view.')
    return '\n'.join(output)
