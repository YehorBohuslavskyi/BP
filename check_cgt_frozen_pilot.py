"""Freeze the authorized preflight cohort; execute only that cohort with --run."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import load_reviewed_findings
from context_audit.cgt_sample import run_pilot
from context_audit.llm import SYSTEM_PROMPT, AuditResponse

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'results/cgt_authorized_pilot'


def main(run=False):
    preflight = ROOT / 'results/cgt_preflight/summary.json'
    manifest = ROOT / 'results/cgt_reviewed_baseline/reviews.json'
    plan = json.loads(preflight.read_text())
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == plan['manifest_sha256']
    candidates, errors = load_reviewed_findings(load_cgt(ROOT / 'datasets/cgt'), manifest)
    assert not errors, errors
    by_id = {c.review_id: c for c in candidates}
    ids = plan['pilot_ids']
    selected = [by_id[key] for key in ids]
    assert len(ids) == len(set(ids)) == 10
    assert sum(c.label for c in selected) == 5
    assert {c.review_id for c in selected if not c.label} == {c.review_id for c in candidates if not c.label}
    paths = list((ROOT / 'src/context_audit').glob('*.py')) + [Path(__file__), manifest, preflight]
    frozen = {
        'candidate_ids': ids, 'positive': 5, 'negative': 5, 'max_rounds': 4,
        'max_output_tokens_per_call': 4000, 'remaining_findings_authorized': False,
        'system_prompt': SYSTEM_PROMPT, 'response_schema': AuditResponse.model_json_schema(),
        'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    }
    OUTPUT.mkdir(exist_ok=True)
    freeze_path = OUTPUT / 'frozen.json'
    if freeze_path.exists():
        assert json.loads(freeze_path.read_text()) == frozen, 'Frozen inputs changed; refusing inference'
    else:
        freeze_path.write_text(json.dumps(frozen, indent=2))
        for p in paths:
            target = OUTPUT / 'snapshot' / p.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
    missing = [k for k in ('OPENAI_API_KEY', 'OPENAI_MODEL') if not os.environ.get(k)]
    status = {'status': 'blocked_configuration' if missing else 'ready',
              'missing_configuration': missing, 'api_calls_made': 0,
              'actual_usage': None, 'confusion_outcomes': None, 'inconclusive_count': None,
              'average_rounds': None, 'requested_fragments': None,
              'preflight_source_function_resolution_failures': plan['preflight_failures'],
              'candidate_ids': ids, 'positive': 5, 'negative': 5}
    if run and not missing:
        # Passing only these ten prevents accidental expansion to the other 17.
        status = run_pilot(selected, OUTPUT / 'pilot', 10)
    (OUTPUT / 'status.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))
    return 1 if missing else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    raise SystemExit(main(parser.parse_args().run))
