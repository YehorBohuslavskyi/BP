"""Limits for interactive analysis, separate from frozen experiment settings."""
from dataclasses import dataclass
import os

MAX_UPLOAD_BYTES = 1024 * 1024
ANALYSIS_TIMEOUT = 120
MAX_ROUNDS = 10
DEFAULT_ROUNDS = 4


class ApplicationError(ValueError):
    """An actionable failure safe to show without an internal traceback."""


@dataclass(frozen=True)
class VerificationSettings:
    """Per-request model and round limit; credentials stay in the environment."""

    model: str
    max_rounds: int = DEFAULT_ROUNDS

    def validate(self) -> None:
        """Reject missing credentials or invalid bounds before starting inference."""
        if not os.environ.get('OPENAI_API_KEY'):
            raise ApplicationError('OPENAI_API_KEY is missing from the application environment.')
        if not self.model.strip():
            raise ApplicationError('Select a model in the sidebar or configure OPENAI_MODEL.')
        if type(self.max_rounds) is not int or not 1 <= self.max_rounds <= MAX_ROUNDS:
            raise ApplicationError(f'Maximum rounds must be between 1 and {MAX_ROUNDS}.')
