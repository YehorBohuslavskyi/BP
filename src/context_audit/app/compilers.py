"""Read Solidity version constraints and select installed compilers without mutation."""
import re

from solc_select.solc_select import installed_versions

from context_audit.app.config import ApplicationError
from context_audit.cgt_inference import strip_comments

_VERSION = re.compile(r'\d+\.\d+\.\d+')
_CONSTRAINT = re.compile(r'(\^|~|>=|<=|>|<|=)?\s*(\d+\.\d+\.\d+)')
_STRINGS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def code_tokens(source: str) -> str:
    """Blank comments and strings before inspecting language-level directives."""
    return _STRINGS.sub(lambda match: ' ' * len(match.group()), strip_comments(source))


def detect_pragmas(source: str) -> list[str]:
    """Return Solidity version constraints, excluding text inside comments or strings."""
    return re.findall(r'\bpragma\s+solidity\s+([^;]+);', code_tokens(source))


def version_tuple(version: str) -> tuple[int, int, int]:
    """Validate a release version and produce an ordered numeric triple."""
    if not _VERSION.fullmatch(version):
        raise ApplicationError(f'Unsupported compiler version: {version!r}')
    major, minor, patch = (int(part) for part in version.split('.'))
    return major, minor, patch


def satisfies(version: str, constraint: str) -> bool:
    """Match exact, caret, tilde, comparator conjunctions, and OR constraints.

    Unrecognized forms fail explicitly instead of guessing a compiler. All
    pragmas in a source must be satisfied; the compiler remains the final check.
    """
    current = version_tuple(version)
    alternatives = []
    for branch in constraint.split('||'):
        terms = []
        remainder = branch.strip()
        if not remainder:
            raise ApplicationError('Empty Solidity version constraint.')
        while remainder:
            match = _CONSTRAINT.match(remainder)
            if not match:
                raise ApplicationError(f'Unsupported Solidity pragma: {constraint!r}')
            operator, text = match.groups()
            target = version_tuple(text)
            major, minor, patch = target
            if operator == '^':
                upper = (major + 1, 0, 0) if major else ((0, minor + 1, 0) if minor else (0, 0, patch + 1))
                terms.append(target <= current < upper)
            elif operator == '~':
                terms.append(target <= current < (major, minor + 1, 0))
            else:
                terms.append({None: current == target, '=': current == target,
                              '>': current > target, '>=': current >= target,
                              '<': current < target, '<=': current <= target}[operator])
            remainder = remainder[match.end():].strip()
        alternatives.append(all(terms))
    return any(alternatives)


def available_compilers() -> list[str]:
    """List local solc-select releases, newest first; never download a compiler."""
    try:
        return sorted(installed_versions(), key=version_tuple, reverse=True)
    except OSError as error:
        raise ApplicationError('Cannot read installed solc-select compilers.') from error


def compatible_compilers(source: str, installed: list[str] | None = None) -> list[str]:
    """Select installed releases satisfying every pragma; allow selection if absent."""
    pragmas = detect_pragmas(source)
    versions = available_compilers() if installed is None else installed
    return [version for version in versions if all(satisfies(version, pragma) for pragma in pragmas)]
