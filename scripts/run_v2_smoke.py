"""Prepare a reviewable smoke plan offline, or explicitly execute an approved plan."""
import argparse
import json
from pathlib import Path
from context_audit.v2_smoke import prepare_plan, prepare_verification_plan, execute_plan
from context_audit.v2_artifacts import digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('--model', required=True)
    prepare.add_argument('--output', type=Path, required=True)
    prepare.add_argument('--plan', type=Path, required=True)
    prepare.add_argument('--candidates', type=Path, help='Offline preparation for verification-only execution of saved discovery')
    run = commands.add_parser('execute')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--approved-plan-sha256', required=True)
    run.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.command == 'execute' and not args.run:
        parser.error('Execution requires --run after explicit approval of this plan')
    try:
        if args.command == 'prepare':
            plan = (prepare_verification_plan(args.source, args.model, args.output, args.candidates)
                    if args.candidates else prepare_plan(args.source, args.model, args.output))
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            with args.plan.open('x') as target:
                json.dump(plan, target, indent=2)
                target.write('\n')
            print('Prepared offline. No API calls. Plan SHA256:', digest(plan))
        else:
            plan = json.loads(args.plan.read_text())
            if digest(plan) != args.approved_plan_sha256:
                parser.error('Plan checksum does not match the approved plan')
            report = execute_plan(plan)
            print(json.dumps({'coverage': report['coverage_counts'], 'transport': report['smoke_transport']}, indent=2))
            counts = report['coverage_counts']
            if report['smoke_transport']['stopped'] or report['discovery_errors'] or counts['processing_failures'] or counts['skipped_candidates']:
                parser.exit(1, 'Partial smoke result; inspect report and budget ledger. Do not automatically retry.\n')
    except (ValueError, OSError):
        parser.exit(1, 'Preflight/artifact/configuration check failed. No automatic retries; inspect the reviewed plan and output.\n')


if __name__ == '__main__':
    main()
