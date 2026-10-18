"""Session lifecycle independent of Streamlit, including stale-result invalidation."""
from dataclasses import dataclass, field
import hashlib

from context_audit.app.config import ApplicationError, VerificationSettings
from context_audit.app.services import (
    Analysis, UploadWorkspace, analyze_upload, create_upload, verify_selected,
)


@dataclass
class AuditSession:
    """Own one upload, one current analysis, and its successful verification history."""

    upload: UploadWorkspace | None = None
    analysis: Analysis | None = None
    history: list[dict] = field(default_factory=list)
    latest: dict[int, dict] = field(default_factory=dict)
    _upload_identity: tuple[str, str] | None = field(default=None, repr=False)

    def clear(self) -> None:
        """Release temporary files and discard all results for the previous source."""
        if self.upload:
            self.upload.close()
        self.upload = None
        self.analysis = None
        self.history.clear()
        self.latest.clear()
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
        self.history.clear()
        self.latest.clear()
        self.analysis = analyze_upload(self.upload, compiler)

    def verify(self, index: int, settings: VerificationSettings) -> dict:
        """Run one explicit verification, retaining successful history for export."""
        if self.upload is None or self.analysis is None:
            raise ApplicationError('Run static analysis before verification.')
        self.latest.pop(index, None)
        result = verify_selected(self.upload, self.analysis, index, settings)
        self.latest[index] = result
        self.history.append(result)
        return result
