"""Run the local scanner, prepare a source, or launch its interface."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
from uuid import uuid4

# solc-select stores binaries inside the active environment. Support invoking
# .venv/bin/python directly, without requiring manual shell activation.
if sys.prefix != sys.base_prefix:
    os.environ.setdefault('VIRTUAL_ENV', sys.prefix)
os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')

from context_audit.app.compilers import available_compilers, compatible_compilers
from context_audit.app.config import ApplicationError
from context_audit.app.scanner import ScannerSettings, prepare_upload, scan_direct, direct_report, scan_static, report_json, report_html
from context_audit.app.services import create_upload

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve', help='Open the scanner interface on localhost')
    serve.add_argument('--port', type=int, default=8501)
    sub.add_parser('doctor', help='Check installed local dependencies without API requests')
    scan = sub.add_parser('scan', help='Scan a self-contained Solidity file; defaults to local static analysis')
    scan.add_argument('source', type=Path, nargs='?')
    scan.add_argument('--example', choices=('vulnerable', 'guarded'))
    scan.add_argument('--method', choices=('static', 'direct', 'prepare'), default='static')
    scan.add_argument('--provider', choices=('openai','codex'), default='codex')
    scan.add_argument('--live', action='store_true', help='Explicitly start model requests using the selected backend')
    scan.add_argument('--model', default=os.environ.get('OPENAI_MODEL', ''))
    scan.add_argument('--limit-profile', choices=('baseline','rounds','context','coverage','expanded'))
    scan.add_argument('--max-candidates', type=int)
    scan.add_argument('--max-rounds', type=int)
    scan.add_argument('--max-fragments', type=int)
    scan.add_argument('--max-source-tokens', type=int)
    scan.add_argument('--max-verification-tokens', type=int)
    scan.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'serve':
        if not 1024 <= args.port <= 65535:
            parser.error('Port must be between 1024 and 65535')
        return subprocess.call([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'streamlit_app.py'),
            '--server.address', '127.0.0.1', '--server.port', str(args.port), '--browser.gatherUsageStats', 'false'], cwd=ROOT)
    if args.command == 'doctor':
        import importlib.util
        versions = available_compilers()
        print(json.dumps({'python': sys.version.split()[0], 'solidity_compilers': versions,
            'slither_available': importlib.util.find_spec('slither') is not None,
            'gui_available': importlib.util.find_spec('streamlit') is not None,
            'api_key_configured': bool(os.environ.get('OPENAI_API_KEY')),
            'model_configured': bool(os.environ.get('OPENAI_MODEL')),
            'note': 'No API requests were made.'}, indent=2))
        return int(not versions)
    if bool(args.source) == bool(args.example):
        parser.error('Provide a Solidity source path or --example, exactly one')
    if args.method == 'direct' and not args.live:
        parser.error('Direct scanning requires --live; use --method prepare for local preparation')
    if args.live and args.method != 'direct':
        parser.error('--live applies only to direct scanning')
    output = args.output or ROOT / 'scanner-output' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])
    if output.exists():
        parser.error('Choose a new output directory; existing results are never overwritten')
    path = args.source or ROOT / 'examples/scanner' / ('VulnerableVault.sol' if args.example == 'vulnerable' else 'GuardedVault.sol')
    upload = None
    try:
        upload = create_upload(path.name, path.read_bytes())
        if args.method == 'prepare':
            result = prepare_upload(upload)
            output.mkdir(parents=True)
            (output / 'preparation.json').write_text(json.dumps(result, indent=2))
            print(f"Prepared {result['analyzable_functions']} functions; {result['batch_count']} batches. No API requests.")
        else:
            if args.method == 'static':
                versions = compatible_compilers(upload.source)
                if not versions:
                    raise ApplicationError('No compatible compiler is installed.')
                report = scan_static(upload, versions[0])
            else:
                model = args.model or ('gpt-6-luna' if args.provider=='codex' else '')
                settings = (ScannerSettings.for_profile(model,args.limit_profile,provider=args.provider)
                            if args.limit_profile else ScannerSettings(model,provider=args.provider))
                overrides = {key: value for key, value in {
                    'max_rounds':args.max_rounds,'max_candidates':args.max_candidates,
                    'max_fragments':args.max_fragments,'max_source_tokens':args.max_source_tokens,
                    'max_verification_tokens':args.max_verification_tokens}.items() if value is not None}
                settings = replace(settings,**overrides)
                settings.validate()
                preparation = prepare_upload(upload)
                report = direct_report(upload, scan_direct(upload, preparation, settings), settings)
            output.mkdir(parents=True)
            shutil.copytree(upload.source_path.parent,output/'artifacts')
            (output / 'report.json').write_text(report_json(report))
            (output / 'report.html').write_text(report_html(report))
            print(json.dumps({'status': report['status'], 'counts': report['counts'], 'usage': report['usage']}, indent=2))
        print('Results: ' + str(output.resolve()))
        return int(args.method != 'prepare' and report['status'] != 'completed')
    except (ApplicationError, OSError) as exc:
        output.mkdir(parents=True, exist_ok=True)
        (output/'failure.json').write_text(json.dumps({'status':'failed','message':str(exc)},indent=2)+'\n')
        if upload and not (output/'diagnostics').exists():
            shutil.copytree(upload.source_path.parent,output/'diagnostics')
        print('Scan failed: ' + str(exc), file=sys.stderr)
        print('Saved diagnostics: ' + str(output.resolve()),file=sys.stderr)
        return 1
    finally:
        if upload:
            upload.close()


if __name__ == '__main__':
    raise SystemExit(main())
