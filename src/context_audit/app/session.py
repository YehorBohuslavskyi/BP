"""Session lifecycle independent of Streamlit, including stale-result invalidation."""
from dataclasses import asdict, dataclass, field
import hashlib

from context_audit.app.batch import batch_plan
from context_audit.app.presentation import finding_key
from context_audit.app.config import ApplicationError, VerificationSettings
from context_audit.app.services import (
    Analysis, UploadWorkspace, analyze_upload, create_upload, verify_selected, export_analysis,
)


@dataclass
class AuditSession:
    """Own one upload, one current analysis, and its successful verification history."""

    upload: UploadWorkspace | None = None
    analysis: Analysis | None = None
    history: list[dict] = field(default_factory=list)
    latest: dict[str, dict] = field(default_factory=dict)
    reviewed_finding_ids: set[str] = field(default_factory=set)
    errors: dict[str, str] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)
    failed_attempts: int = 0
    exported_result: str | None = None
    _upload_identity: tuple[str, str] | None = field(default=None, repr=False)

    def clear(self) -> None:
        """Release temporary files and discard all results for the previous source."""
        if self.upload:
            self.upload.close()
        self.upload = None
        self.analysis = None
        self.errors.clear()
        self.skipped.clear()
        self.failed_attempts = 0
        self.history.clear()
        self.latest.clear()
        self.reviewed_finding_ids.clear()
        self.exported_result = None
        self._upload_identity = None

    def set_upload(self, filename: str, content: bytes) -> None:
        """Replace changed uploads, clearing stale results even when validation fails."""
        identity = filename, hashlib.sha256(content).hexdigest()
        if identity == self._upload_identity:
            return
        self.clear()
        self.upload = create_upload(filename, content)
        self._upload_identity = identity

    def analyze(self, compiler: str) -> None:
        """Run local analysis explicitly and invalidate results from earlier runs."""
        if self.upload is None:
            raise ApplicationError('Upload a Solidity file first.')
        self.analysis = None
        self.errors.clear()
        self.skipped.clear()
        self.failed_attempts = 0
        self.history.clear()
        self.latest.clear()
        self.reviewed_finding_ids.clear()
        self.exported_result = None
        self.analysis = analyze_upload(self.upload, compiler)
        self.exported_result = export_analysis(self.upload, self.analysis, self.history)

    def verify(self, index: int, settings: VerificationSettings) -> dict:
        """Run one explicit verification, retaining successful history for export."""
        if self.upload is None or self.analysis is None:
            raise ApplicationError('Run static analysis before verification.')
        result = verify_selected(self.upload, self.analysis, index, settings)
        finding = self.analysis.findings[index]
        result['finding'] = asdict(finding)
        identity = finding_key(finding)
        self.errors.pop(identity, None)
        self.skipped.pop(identity, None)
        self.latest[identity] = result
        self.reviewed_finding_ids.add(identity)
        self.history.append(result)
        self.exported_result = export_analysis(self.upload, self.analysis, self.history)
        return result

    def clear_verifications(self) -> None:
        """Forget GUI verification state while retaining upload and static analysis."""
        self.history.clear()
        self.latest.clear()
        self.reviewed_finding_ids.clear()
        self.errors.clear()
        self.skipped.clear()
        self.failed_attempts = 0
        self.exported_result = (export_analysis(self.upload, self.analysis, [])
                                if self.upload and self.analysis else None)

    def verify_batch(self, settings: VerificationSettings, impact_filter='High + Medium',
                     progress=None) -> dict:
        """Verify pending targets sequentially and retain each outcome immediately.

        Completion is keyed by stable finding ID, including inconclusive results.
        A later explicit batch action retries errors but never completed findings.
        """
        if self.upload is None or self.analysis is None:
            raise ApplicationError('Run static analysis before verification.')
        plan = batch_plan(self.analysis.findings, self.upload.source_path, self.latest, impact_filter)
        self.skipped = plan['skipped']
        for number, index in enumerate(plan['pending'], 1):
            finding = self.analysis.findings[index]
            identity = finding_key(finding)
            if identity in self.latest:
                continue
            if progress:
                progress(number, len(plan['pending']), finding, False)
            try:
                self.verify(index, settings)
            except Exception:
                # Worker exceptions can contain provider details or credentials. Public
                # batch exports retain a safe message, never arbitrary exception text.
                self.errors[identity] = 'Verification failed. Check configuration and retry explicitly.'
                self.failed_attempts += 1
            if progress:
                progress(number, len(plan['pending']), finding, True)
        return plan


def upgrade_session(session: AuditSession) -> AuditSession:
    """Preserve an older live GUI session when presentation code is hot-reloaded."""
    for name, default in (('errors', {}), ('skipped', {}), ('failed_attempts', 0)):
        if not hasattr(session, name):
            setattr(session, name, default)
    if hasattr(session, 'reviewed_finding_ids') and hasattr(session, 'exported_result'):
        return session
    session.reviewed_finding_ids = set()
    session.latest = {
        finding_key(session.analysis.findings[index]) if isinstance(index, int) else index: report
        for index, report in session.latest.items()
        if not isinstance(index, int) or (session.analysis and 0 <= index < len(session.analysis.findings))
    }
    session.reviewed_finding_ids.update(session.latest)
    if session.analysis:
        findings = {finding_key(finding): finding for finding in session.analysis.findings}
        for report in session.history:
            identity = report.get('result', {}).get('finding', {}).get('id')
            if identity in findings:
                report.setdefault('finding', asdict(findings[identity]))
                session.reviewed_finding_ids.add(identity)
    session.exported_result = (export_analysis(session.upload, session.analysis, session.history)
                               if session.upload and session.analysis else None)
    return AuditSession(
        upload=session.upload, analysis=session.analysis, history=session.history,
        latest=session.latest, reviewed_finding_ids=session.reviewed_finding_ids,
        exported_result=session.exported_result, _upload_identity=session._upload_identity,
    )
