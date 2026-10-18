"""Verify one selected saved finding; execution may make paid API requests."""
import argparse
import json
from pathlib import Path

from context_audit.findings import parse_slither_findings
from context_audit.verifier import summarize_verification, verify_finding


def main() -> None:
    """Select one exact finding and invoke the existing verifier explicitly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--slither-json', type=Path, required=True)
    parser.add_argument('--finding-id', required=True)
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--max-rounds', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.max_rounds <= 4:
        parser.error('--max-rounds must be 1..4')
    findings = parse_slither_findings(json.loads(args.slither_json.read_text()))
    selected = [finding for finding in findings if finding.id == args.finding_id]
    if len(selected) != 1:
        parser.error('--finding-id must identify exactly one warning')
    result = verify_finding(args.source.resolve(), (args.project_root or args.source.parent).resolve(),
                            selected[0], args.max_rounds)
    print(json.dumps({'result': result, 'summary': summarize_verification(result)}, indent=2))


if __name__ == '__main__':
    main()
