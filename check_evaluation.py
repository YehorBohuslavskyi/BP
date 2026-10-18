"""Inspect one saved SmartBugs analysis without rerunning Slither or inference."""
import argparse
import json
from pathlib import Path

from context_audit.reporting import evaluate_saved_contract


def main() -> None:
    """Select a contract and print its existing-policy evaluation as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path, default=Path('datasets/smartbugs-curated'))
    parser.add_argument('--contract', default='FibonacciBalance.sol')
    parser.add_argument('--slither-json', type=Path, default=Path('fibonacci_slither.json'))
    args = parser.parse_args()
    print(json.dumps(evaluate_saved_contract(args.dataset_root, args.contract, args.slither_json), indent=2))


if __name__ == '__main__':
    main()
