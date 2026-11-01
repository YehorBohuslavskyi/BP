#!/usr/bin/env python3
"""Compile one acquired victim and record static-analysis evidence; never infer labels.

Run with the project's Python environment. Imports use the compiler's normal local
resolution from the source directory; dependencies are never installed or rewritten.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT / 'examples/defihacklabs/evaluation/final20/contracts'
MANAGED = ('compilation.txt', 'slither.json', 'slither.txt', 'integration.json')


def source_metadata(source):
    content = source.read_bytes()
    text = content.decode('utf-8-sig')
    # Ignore comments before extracting Solidity directives.
    code = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    imports = re.findall(r'\bimport\s+[^;]+;', code)
    return dict(source_sha256=hashlib.sha256(content).hexdigest(), source_bytes=len(content),
                source_lines=len(text.splitlines()), pragma_lines=re.findall(r'\bpragma\s+solidity\s+[^;]+;', code),
                imports=imports, looks_flattened=not imports,
                flattened_heuristic='No import directives; not a provenance/equivalence assertion')


def compiler_path(version):
    from solc_select.solc_select import ARTIFACTS_DIR
    path = ARTIFACTS_DIR / f'solc-{version}' / f'solc-{version}'
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f'Compiler {version} is not installed locally. Run: solc-select install {version}')
    return path


def parse_findings(report):
    # Reuse production finding parsing; no verifier or inference module is imported.
    from context_audit.findings import parse_slither_findings
    if not isinstance(report, dict):
        raise ValueError('Slither JSON must be an object')
    return parse_slither_findings(report)


def print_summary(report):
    findings = parse_findings(report)
    print(f'Total findings: {len(findings)}')
    order = {'High': 0, 'Medium': 1, 'Low': 2, 'Informational': 3, 'Optimization': 4}
    severity = None
    for finding in sorted(findings, key=lambda f: (order.get(f.impact, 5), f.impact, f.detector, f.id)):
        if severity != finding.impact:
            severity = finding.impact
            print(f'\n{severity}:')
        lines = ','.join(map(str, finding.lines)) or 'unknown'
        print(f'  {finding.detector} | impact={finding.impact} | confidence={finding.confidence} | '
              f'{finding.contract or "unknown"}.{finding.function_signature or "unknown"} | '
              f'lines={lines} | id={finding.id}')


def execute(command, cwd, timeout):
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        def decode(value): return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
        return 124, decode(error.stdout), decode(error.stderr) + '\nProcess timed out.'
    except OSError as error:
        return 127, '', f'{type(error).__name__}: {error}'


@contextmanager
def evidence_lock(evidence, overwrite):
    evidence.mkdir(parents=True, exist_ok=True)
    lock = evidence / '.processing.lock'
    with lock.open('x'):
        pass
    try:
        if any((evidence / name).is_symlink() for name in MANAGED):
            raise ValueError('Refusing symlink evidence files')
        if not overwrite and any(p.name != lock.name for p in evidence.iterdir()):
            raise ValueError('Evidence exists; use --summary-only or explicitly --overwrite')
        if overwrite:
            for name in MANAGED:
                (evidence / name).unlink(missing_ok=True)
        yield
    finally:
        lock.unlink()


def process(case, source, compiler, overwrite=False, summary_only=False):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', case):
        raise ValueError('Case must contain lowercase letters/digits separated by single hyphens')
    if compiler is not None and not re.fullmatch(r'\d+\.\d+\.\d+', compiler):
        raise ValueError('Compiler must be an exact version, e.g. 0.6.12')
    evidence = CASE_ROOT / case / 'evidence'
    if not evidence.resolve().is_relative_to(CASE_ROOT.resolve()):
        raise ValueError('Evidence path escapes contracts directory')
    if summary_only:
        print_summary(json.loads((evidence / 'slither.json').read_text()))
        return 0
    if source is None or compiler is None:
        raise ValueError('--source and --compiler are required unless --summary-only is used')
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() != '.sol':
        raise ValueError(f'Source must be an existing Solidity .sol file: {source}')
    if source.is_relative_to(evidence.resolve()):
        raise ValueError('Source cannot be inside the output evidence directory')
    metadata = source_metadata(source)
    solc = compiler_path(compiler)  # Native binary: never triggers solc-select downloads.
    slither = Path(sys.executable).parent / 'slither'
    if not slither.is_file():
        found = shutil.which('slither')
        if not found:
            raise ValueError('Slither is not installed in the current environment')
        slither = Path(found)
    compile_command = [str(solc), '--bin', str(source)]
    slither_command = [str(slither), str(source), '--solc', str(solc),
                       '--compile-force-framework', 'solc', '--json', '-', '--fail-none']
    record = dict(case=case, source_status='SOURCE_NEEDS_REVIEW', source_path=str(source),
                  compiler=compiler, **metadata, compilation_status='NOT_RUN', slither_status='NOT_RUN',
                  slither_finding_count=0, baseline_classification='PENDING_MANUAL_ADJUDICATION',
                  matched_slither_finding_ids=[], llm_target_created=False,
                  compile_command=compile_command, slither_command=slither_command,
                  working_directory=str(source.parent),
                  status_scope='Technical readiness only; incident/deployment provenance requires separate review')
    with evidence_lock(evidence, overwrite):
        try:
            code, stdout, stderr = execute(compile_command, source.parent, 180)
            (evidence / 'compilation.txt').write_text(
                f'Command: {json.dumps(compile_command)}\nExit code: {code}\n\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}')
            record['compilation_status'] = 'SUCCESS' if code == 0 else 'FAILURE'
            if code:
                print(f'Compilation failed (exit {code}); see {evidence / "compilation.txt"}', file=sys.stderr)
                return 1
            record['source_status'] = 'SOURCE_READY'
            code, stdout, stderr = execute(slither_command, source.parent, 300)
            (evidence / 'slither.txt').write_text(f'Exit code: {code}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}')
            try:
                report = json.loads(stdout)
                # Preserve complete JSON even when Slither reports analysis failure.
                (evidence / 'slither.json').write_text(stdout)
                findings = parse_findings(report)
                if code:
                    raise ValueError(f'Slither exited {code}')
            except (ValueError, TypeError, KeyError) as error:
                record['slither_status'] = 'FAILURE'
                record['slither_error'] = str(error)
                print(f'Slither failed; see {evidence / "slither.txt"}', file=sys.stderr)
                return 1
            record['slither_status'] = 'SUCCESS'
            record['slither_finding_count'] = len(findings)
            print_summary(report)
            return 0
        finally:
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            record['source_unchanged'] = actual == metadata['source_sha256']
            (evidence / 'integration.json').write_text(json.dumps(record, indent=2) + '\n')
            if not record['source_unchanged']:
                raise ValueError('Source changed during processing')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--compiler')
    parser.add_argument('--overwrite', action='store_true', help='Replace only this script\'s evidence files')
    parser.add_argument('--summary-only', action='store_true', help='Read existing Slither JSON; no subprocesses or writes')
    args = parser.parse_args(argv)
    if args.summary_only and args.overwrite:
        parser.error('--summary-only cannot be combined with --overwrite')
    try:
        return process(args.case, args.source, args.compiler, args.overwrite, args.summary_only)
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
