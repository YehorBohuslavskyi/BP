"""Prepare offline; execute exactly one approved source/method, never a cohort."""
import argparse
import json
from pathlib import Path
from context_audit.development_experiment import prepare, execute
from context_audit.v2_artifacts import digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('source', type=Path)
    prep.add_argument('--model', required=True)
    prep.add_argument('--method', choices=('b1', 'b2'), required=True)
    prep.add_argument('--max-calls', type=int, required=True)
    prep.add_argument('--max-tokens', type=int, required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--plan', type=Path, required=True)
    run = sub.add_parser('execute')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--approved-plan-sha256', required=True)
    run.add_argument('--run', action='store_true')
    run.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        plan = prepare(args.source, args.model, args.output, args.method, args.max_calls, args.max_tokens)
        args.plan.parent.mkdir(parents=True, exist_ok=True)
        with args.plan.open('x') as f:
            json.dump(plan, f, indent=2); f.write('\n')
        print('Prepared offline; plan SHA256:', digest(plan))
    else:
        plan = json.loads(args.plan.read_text())
        if not args.run or digest(plan) != args.approved_plan_sha256:
            parser.error('Execution requires --run and the exact approved plan checksum')
        execute(plan, resume=args.resume)
        print('Stopped after one source/method; inspect report and budget_ledger.json before continuing.')


if __name__ == '__main__':
    main()
