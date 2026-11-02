"""Prepare by default; inference requires --run."""
import argparse
import json
from pathlib import Path
from context_audit.direct import prepare, run_function, aggregate


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--function')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--max-rounds', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payloads, catalog = prepare(args.source.resolve())
    if args.function:
        payloads = [p for p in payloads if p['target']['signature'] == args.function]
    if args.run and args.output.exists() and any(args.output.iterdir()):
        parser.error('Choose an empty output directory to preserve existing sessions')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'prepared.json').write_text(json.dumps(payloads, indent=2))
    print(f'{len(payloads)} function sessions selected')
    if args.run:
        results = [run_function(p, catalog, args.output / f'function-{i}.json', args.max_rounds)
                   for i, p in enumerate(payloads)]
        (args.output / 'contract_reports.json').write_text(json.dumps(aggregate(results), indent=2))


if __name__ == '__main__':
    main()
