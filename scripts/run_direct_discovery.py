"""Mode B v2: offline preparation by default; every live stage requires --run."""
import argparse
import json
import os
from pathlib import Path
from context_audit.direct_discovery import prepare, run_discovery, markdown
from context_audit.direct_preparation import PreparationError
from context_audit.direct_verification import Limits
from context_audit.v2_artifacts import atomic_json
from context_audit.v2_pipeline import run_verification


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--run', action='store_true', help='Explicitly authorize API execution')
    parser.add_argument('--stage', choices=('prepare', 'discover', 'verify', 'all'))
    parser.add_argument('--candidates', type=Path, help='Saved discovery.json including its provenance manifest')
    parser.add_argument('--resume', action='store_true', help='Reuse matching saved verification sessions explicitly')
    parser.add_argument('--max-summary-chars', type=int, default=24000)
    for name, field in Limits.model_fields.items():
        parser.add_argument('--' + name.replace('_', '-'), type=int, default=field.default)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage or ('discover' if args.run else 'prepare')
    if stage != 'prepare' and not args.run:
        parser.error('Live stages require --run; omit it for offline preparation')
    if stage == 'prepare' and args.run:
        parser.error('Offline preparation does not accept --run')
    if args.resume and stage not in ('verify', 'all'):
        parser.error('--resume applies to verification only')
    if args.candidates and stage != 'verify':
        parser.error('--candidates applies to --stage verify')
    if stage == 'verify' and not args.candidates:
        parser.error('--stage verify requires --candidates discovery.json')
    if args.output.exists() and (not args.output.is_dir() or (any(args.output.iterdir()) and not args.resume)):
        parser.error('Choose an empty output directory to preserve existing artifacts, or explicitly --resume verification')
    if args.max_summary_chars < 256:
        parser.error('--max-summary-chars must be at least 256')
    try:
        limits = Limits(**{name: getattr(args, name) for name in Limits.model_fields})
    except ValueError:
        parser.error('Invalid verification limits')
    if stage != 'prepare' and not os.environ.get('OPENAI_MODEL'):
        parser.error('Set OPENAI_MODEL for live execution or compatible resume')
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        contracts, catalog = prepare(args.source.resolve())
        if stage == 'verify' or (stage == 'all' and args.resume):
            saved = args.candidates if stage == 'verify' else args.output / 'discovery.json'
            discovery = json.loads(saved.read_text())
        else:
            discovery = run_discovery(contracts, catalog, execute=stage != 'prepare', max_chars=args.max_summary_chars)
            atomic_json(args.output / 'discovery.json', discovery)
            (args.output / 'summary.md').write_text(markdown(discovery))
        if stage in ('verify', 'all'):
            result = run_verification(discovery, contracts, catalog, args.output, resume=args.resume, limits=limits)
            # Copy only after provenance validation, retaining a self-contained run.
            if stage == 'verify' and not args.resume:
                atomic_json(args.output / 'discovery.json', discovery)
            print(json.dumps(result['coverage_counts'], indent=2))
            counts = result['coverage_counts']
            if counts['processing_failures'] or counts['skipped_candidates'] or counts['pending_candidates'] or discovery['errors']:
                parser.exit(1, 'Partial analysis: inspect report.json for errors, limits and pending candidates\n')
        else:
            print(json.dumps(discovery['coverage_counts'], indent=2))
            if discovery['errors']:
                parser.exit(1, 'Discovery errors recorded in discovery.json\n')
    except PreparationError as exc:
        if not args.resume:
            atomic_json(args.output / 'preparation_error.json', exc.metadata)
        parser.exit(1, 'Preparation failed; inspect preparation_error.json for offline diagnostics\n')
    except KeyboardInterrupt:
        parser.exit(130, 'Interrupted; completed verification checkpoints and any partial report are retained\n')
    except (ValueError, OSError, KeyError):
        parser.exit(1, 'Invalid or incompatible artifact/input; check source, manifests, model, limits and output paths\n')


if __name__ == '__main__':
    main()
