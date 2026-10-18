"""Inspect a bounded preview of SmartBugs metadata without running analysis."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from context_audit.dataset import load_smartbugs_curated


def main() -> None:
    """Print dataset size and a configurable contract preview."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path, default=Path('datasets/smartbugs-curated'))
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    contracts = load_smartbugs_curated(args.dataset_root)
    print(json.dumps({'contracts': len(contracts), 'preview': [asdict(c) for c in contracts[:args.limit]]},
                     indent=2, default=str))


if __name__ == '__main__':
    main()
