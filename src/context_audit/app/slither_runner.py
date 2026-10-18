"""Bounded Slither execution with compiler selection isolated to a child process."""
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

from context_audit.app.config import ANALYSIS_TIMEOUT, ApplicationError
from context_audit.app.compilers import version_tuple
from context_audit.findings import parse_slither_findings

logger = logging.getLogger(__name__)


def executable(name: str) -> str:
    """Prefer tools from this Python environment, then search the process PATH."""
    local = Path(sys.executable).parent / name
    resolved = str(local) if local.is_file() else shutil.which(name)
    if not resolved:
        raise ApplicationError(f'{name} is not installed in the application environment.')
    return resolved


def process_environment(compiler: str, model: str | None = None) -> dict[str, str]:
    """Build child-only configuration so concurrent sessions cannot change each other."""
    version_tuple(compiler)
    environment = dict(os.environ)
    environment['SOLC_VERSION'] = compiler
    environment['PATH'] = str(Path(sys.executable).parent) + os.pathsep + environment.get('PATH', '')
    # Module workers run in the temporary source directory, not the repository.
    source_root = str(Path(__file__).resolve().parents[2])
    environment['PYTHONPATH'] = source_root + os.pathsep + environment.get('PYTHONPATH', '')
    if model is not None:
        environment['OPENAI_MODEL'] = model
    return environment


def run_slither(source: Path, compiler: str, timeout: int = ANALYSIS_TIMEOUT) -> dict:
    """Run installed solc and Slither, returning validated JSON or an actionable error."""
    environment = process_environment(compiler)
    try:
        check = subprocess.run([executable('solc'), '--version'], env=environment,
                               cwd=source.parent, capture_output=True, text=True, timeout=30)
        if check.returncode:
            raise ApplicationError(f'Installed compiler {compiler} could not start.')
        logger.info('Running Slither with solc %s', compiler)
        process = subprocess.run(
            [executable('slither'), str(source), '--compile-force-framework', 'solc',
             '--json', '-', '--fail-none'],
            env=environment, cwd=source.parent, capture_output=True, text=True, timeout=timeout,
        )
        if process.returncode:
            raise ApplicationError('Slither could not compile this source. Check the pragma and selected compiler; imports are unsupported in v1.')
        report = json.loads(process.stdout)
        parse_slither_findings(report)
        return report
    except subprocess.TimeoutExpired as error:
        raise ApplicationError(f'Slither or compiler exceeded its time limit ({timeout}s for analysis).') from error
    except (OSError, json.JSONDecodeError) as error:
        raise ApplicationError('Slither failed to run or returned invalid JSON.') from error
    except ValueError as error:
        if isinstance(error, ApplicationError):
            raise
        raise ApplicationError('Slither reported an unsuccessful analysis.') from error
