"""Explicit local demonstration sources; registering one never executes analysis."""
from dataclasses import dataclass
from pathlib import Path
from context_audit.app.config import ApplicationError


@dataclass(frozen=True)
class DemoContract:
    """A named, validated demonstration source relative to the repository root."""
    label: str
    path: str


DEMO_CONTRACTS = {
    'simple_suicide': DemoContract(
        'Confirmed vulnerability example · simple_suicide.sol',
        'datasets/smartbugs-curated/dataset/access_control/simple_suicide.sol'),
    'valuetrader_false_positive': DemoContract(
        'Validated false-positive example · ValueTrader.die()',
        'datasets/cgt/source/efe5ebd718c6afa9c24214bb4373b40d.sol'),
}


def load_demo(identity: str, root: Path | None = None) -> tuple[str, bytes]:
    """Read a registered local source for the normal upload service."""
    demo = DEMO_CONTRACTS.get(identity)
    if demo is None:
        raise ApplicationError('Unknown demo contract.')
    root = root or Path(__file__).resolve().parents[3]
    path = root / demo.path
    try:
        return path.name, path.read_bytes()
    except OSError as error:
        raise ApplicationError('Demo contract source is not available locally.') from error
