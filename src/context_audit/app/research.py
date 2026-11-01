"""Read-only adapters for frozen research evidence and presentation metrics."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = {
    'pilot': 'results/cgt_authorized_pilot/pilot/summary.json',
    'findings': 'results/cgt_authorized_pilot/pilot/findings.json',
    'cohort': 'results/cgt_reviewed_baseline/summary.json',
    'smartbugs': 'benchmarks/access_control_baseline.json',
}


def load_artifact(path: Path):
    """Return decoded saved evidence, or None when unavailable or unreadable."""
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def load_research(root: Path = ROOT) -> dict:
    """Load independent experiments without executing analysis or inference."""
    return {name: load_artifact(root / path) for name, path in ARTIFACTS.items()}


def pilot_metrics(summary: dict) -> dict:
    """Calculate filtering and retention only within the selected pilot cohort."""
    before = summary['comparison']['slither_candidate_baseline']
    after = summary['comparison']['llm_non_abstained']
    # Abstentions/errors remain candidates: only explicit false-positive verdicts
    # count as removals. Retention requires an explicit confirmed true finding.
    return {'before': before, 'after': after,
            'fp_reduction': after['TN'] / before['FP'] if before['FP'] else None,
            'tp_retention': after['TP'] / before['TP'] if before['TP'] else None}


def finding_rows(findings: list[dict]) -> list[dict]:
    """Translate evaluation-only labels into readable presentation rows."""
    rows = []
    for item in findings:
        verdict, label = item['verdict'], item['label']
        correct = (label and verdict == 'confirmed') or (not label and verdict == 'false_positive')
        outcome = ('CORRECT' if correct else 'ABSTENTION' if verdict == 'inconclusive'
                   else 'ERROR' if verdict == 'error' else 'WRONG REJECTION' if label else 'MISSED FP')
        rows.append({'Finding ID': item['review_id'], 'Detector': item['result']['finding']['detector'],
                     'Ground truth': 'REAL' if label else 'FALSE POSITIVE',
                     'LLM verdict': verdict.replace('_', ' ').upper(), 'Correct?': outcome,
                     'Rounds': item['round_count'], 'Requested fragments': item['requested_fragments'],
                     'Total tokens': item['total_tokens']})
    return rows


def evidence_fragments(item: dict, root: Path = ROOT) -> list[dict]:
    """Resolve cited saved fragments, including legacy byte-offset source IDs.

    Source paths must stay inside the local CGT tree. No compiler or LLM is used.
    Anonymous IDs absent from saved context are explicitly marked unavailable.
    """
    result = item['result']
    provided = {f['id']: f for f in result.get('provided_context', [])}
    fragments = []
    for identity in item.get('evidence_ids', []):
        fragment = provided.get(identity)
        if fragment:
            fragments.append(fragment)
            continue
        source = None
        try:
            filename, kind, start, length = identity.rsplit(':', 3)
            path = (root / 'datasets/cgt/source' / filename).resolve()
            path.relative_to((root / 'datasets/cgt/source').resolve())
            start, length = int(start), int(length)
            if start >= 0 and length > 0:
                source = path.read_bytes()[start:start + length].decode('utf-8')
        except (ValueError, OSError):
            pass
        fragments.append({'id': identity, 'source': source, 'name': 'Cited source fragment'})
    return fragments


def slither_claim(item: dict, root: Path = ROOT) -> str | None:
    """Read the exact reproduced Slither description referenced by reviewed evidence."""
    directory = root / 'results/cgt_reviewed_baseline'
    reviews = load_artifact(directory / 'reviews.json') or []
    review = next((r for r in reviews if r['review_id'] == item['review_id']), None)
    if not review:
        return None
    path = (directory / review['slither_json']).resolve()
    try:
        path.relative_to((root / 'results').resolve())
    except ValueError:
        return None
    raw = load_artifact(path) or {}
    detectors = raw.get('results', {}).get('detectors', [])
    finding = next((f for f in detectors if f.get('id') == review['finding_id']), None)
    return finding.get('description') if finding else None
