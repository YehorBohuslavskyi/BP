"""Single-file analysis services with owned temporary storage and explicit inference."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from context_audit.app.compilers import code_tokens, compatible_compilers, detect_pragmas
from context_audit.app.config import ApplicationError, MAX_UPLOAD_BYTES, VerificationSettings
from context_audit.app.presentation import verification_ineligibility, verification_export
from context_audit.app.slither_runner import process_environment, run_slither
from context_audit.findings import Finding, parse_slither_findings

logger = logging.getLogger(__name__)


@dataclass
class UploadWorkspace:
    """Own one upload directory until the session resets or releases this object."""

    source_path: Path
    source: str
    digest: str
    pragmas: list[str]
    _temporary: TemporaryDirectory = field(repr=False)

    def close(self) -> None:
        """Remove this upload and its transient analysis files."""
        self._temporary.cleanup()


@dataclass
class Analysis:
    """Bind parsed warnings and raw Slither JSON to the analyzed source hash."""

    compiler: str
    source_digest: str
    findings: list[Finding]
    raw: dict = field(repr=False)


def create_upload(filename: str, content: bytes) -> UploadWorkspace:
    """Validate one UTF-8 Solidity upload and write it under a fixed safe filename."""
    if not filename.lower().endswith('.sol'):
        raise ApplicationError('Upload one .sol file.')
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ApplicationError('Upload must be nonempty and at most 1 MiB.')
    try:
        source = content.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ApplicationError('The Solidity file must use UTF-8 encoding.') from error
    if '\x00' in source:
        raise ApplicationError('The upload contains binary data.')
    if re.search(r'\bimport\b', code_tokens(source)):
        raise ApplicationError('Imports are unsupported in v1. Upload a self-contained Solidity file.')
    directory = TemporaryDirectory(prefix='context-audit-')
    try:
        path = Path(directory.name) / 'source.sol'
        path.write_text(source, encoding='utf-8')
        return UploadWorkspace(path, source, hashlib.sha256(path.read_bytes()).hexdigest(),
                               detect_pragmas(source), directory)
    except Exception:
        directory.cleanup()
        raise


def check_source(upload: UploadWorkspace) -> None:
    """Reject deleted or modified source before reusing a prior analysis."""
    if not upload.source_path.is_file():
        raise ApplicationError('The temporary source is no longer available. Upload it again.')
    if hashlib.sha256(upload.source_path.read_bytes()).hexdigest() != upload.digest:
        raise ApplicationError('Source changed after upload. Upload it again before analysis.')


def analyze_upload(upload: UploadWorkspace, compiler: str) -> Analysis:
    """Analyze the upload using an installed compatible compiler, without inference."""
    check_source(upload)
    if compiler not in compatible_compilers(upload.source):
        raise ApplicationError('Select an installed compiler compatible with this source.')
    raw = run_slither(upload.source_path, compiler)
    return Analysis(compiler, upload.digest, parse_slither_findings(raw), raw)


def verify_selected(upload: UploadWorkspace, analysis: Analysis, index: int,
                    settings: VerificationSettings) -> dict:
    """Verify one warning in a separate process using the unchanged core pipeline."""
    settings.validate()
    check_source(upload)
    if analysis.source_digest != upload.digest:
        raise ApplicationError('Analysis belongs to a different upload. Run Slither again.')
    if type(index) is not int or not 0 <= index < len(analysis.findings):
        raise ApplicationError('Select a finding from the current analysis.')
    finding = analysis.findings[index]
    reason = verification_ineligibility(finding, upload.source_path)
    if reason:
        raise ApplicationError(f'This warning has no resolvable supported target: {reason}')
    request = {'source': str(upload.source_path), 'finding': asdict(finding),
               'max_rounds': settings.max_rounds}
    environment = process_environment(analysis.compiler, settings.model)
    logger.info('Verifying selected finding %s, at most %d rounds', finding.detector, settings.max_rounds)
    try:
        process = subprocess.run(
            [sys.executable, '-m', 'context_audit.app.worker'], input=json.dumps(request),
            cwd=upload.source_path.parent, env=environment, capture_output=True, text=True,
            timeout=120 + 65 * settings.max_rounds,
        )
        response = json.loads(process.stdout)
        if process.returncode or 'error' in response:
            raise ApplicationError(response.get('error', 'Verification worker failed.'))
        return response
    except subprocess.TimeoutExpired as error:
        raise ApplicationError('Verification timed out. No automatic retry was made; some API usage may have occurred.') from error
    except (OSError, json.JSONDecodeError) as error:
        raise ApplicationError('Verification worker could not return a result. No automatic retry was made.') from error


def export_analysis(upload: UploadWorkspace, analysis: Analysis, verifications: list[dict]) -> str:
    """Serialize analysis and verification evidence without environment credentials."""
    check_source(upload)
    if analysis.source_digest != upload.digest:
        raise ApplicationError('Cannot export an analysis for a different upload.')
    usage = {key: sum(item['summary'][key] for item in verifications)
             for key in ('input_tokens', 'output_tokens', 'total_tokens')}
    return json.dumps({
        'schema_version': 2, 'source': upload.source, 'source_sha256': upload.digest,
        'compiler': analysis.compiler, 'slither_findings': [asdict(item) for item in analysis.findings],
        'verification': [verification_export(item) for item in verifications], 'usage': usage,
        'usage_note': 'Sum of reported usage for exported successful verifier runs; failed calls may have unreported usage.',
    }, indent=2, ensure_ascii=False)
