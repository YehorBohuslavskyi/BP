"""Offline Slither baseline on the same sanitized dependency graph; no model client."""
import argparse
import inspect
import json
import subprocess
import sys
from pathlib import Path
from importlib.metadata import version
from context_audit.direct_preparation import staged_source, project_root
from context_audit.v2_artifacts import file_hash


def worker(source):
    from slither.slither import Slither
    from slither.detectors import all_detectors
    from slither.detectors.abstract_detector import AbstractDetector
    with staged_source(source) as (staged, root, kwargs, metadata):
        slither = Slither(str(staged), **kwargs)
        for detector in vars(all_detectors).values():
            if inspect.isclass(detector) and issubclass(detector, AbstractDetector) and detector is not AbstractDetector:
                slither.register_detector(detector)
        findings = [f for group in slither.run_detectors() for f in group]
        # Map transient staged paths back to the unchanged original dependency tree.
        findings = json.loads(json.dumps(findings).replace(str(root), str(project_root(source))))
    return {'success': True, 'source': str(source), 'source_sha256': file_hash(source),
            'slither_version': version('slither-analyzer'), 'preparation': metadata,
            'sanitized': True, 'results': {'detectors': findings}}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.worker:
        print(json.dumps(worker(args.source.resolve())))
        return
    if not args.output or args.output.exists():
        p.error('Provide a new --output path')
    try:
        completed = subprocess.run([sys.executable, __file__, str(args.source.resolve()), '--worker'],
                                   capture_output=True, text=True, timeout=60)
        result = json.loads(completed.stdout) if completed.returncode == 0 else {
            'success': False, 'status': 'UNEVALUABLE', 'reason': 'SLITHER_PREPARATION_FAILED',
            'returncode': completed.returncode}
    except subprocess.TimeoutExpired:
        result = {'success': False, 'status': 'UNEVALUABLE', 'reason': 'SLITHER_TIMEOUT'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({'success': result['success'], 'findings': len(result.get('results', {}).get('detectors', []))}))


if __name__ == '__main__':
    main()
