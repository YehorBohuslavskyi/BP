"""Direct-only sanitized staging and explicit, local compiler preparation."""
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from solc_select.solc_select import ARTIFACTS_DIR
from context_audit.app.compilers import compatible_compilers, detect_pragmas

# Strings are consumed before comments, so URL/string literals remain unchanged.
TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\r\n]*|/\*[\s\S]*?\*/')
ANNOTATION = re.compile(r'\bSWC[-\s]*\d{3}\b|\bDAppSCAN\b|\bground[ -]?truth\b', re.I)
CATEGORY_LOCATION = re.compile(r'\b(?:reentrancy|unchecked call return value|unprotected ether withdrawal|authorization through tx\.origin|delegatecall to untrusted callee|transaction order dependence)\s*:\s*L?\d+(?:\s*[-–]\s*L?\d+)?', re.I)


def sanitize_source(source):
    """Blank annotation comments, retaining newlines and UTF-8 byte positions."""
    def clean(match):
        text = match.group()
        if text.startswith(('//', '/*')) and (ANNOTATION.search(text) or CATEGORY_LOCATION.search(text)):
            return ''.join(c if c in '\r\n' else ' ' * len(c.encode('utf-8')) for c in text)
        return text
    return TOKENS.sub(clean, source)


class PreparationError(ValueError):
    def __init__(self, status, message, metadata=None):
        super().__init__(message)
        self.metadata = {**(metadata or {}), 'preparation_status': status, 'preparation_error': message, 'session_count': 0}


def project_root(source):
    """Use the checkout's project boundary, otherwise a nearby build manifest."""
    source = source.resolve()
    for parent in source.parents:
        if parent.parent.name == 'contracts' and parent.parent.parent.name == 'DAppSCAN-source':
            return parent
    for parent in source.parents:
        if any((parent / f).exists() for f in ('foundry.toml', 'hardhat.config.js', 'package.json', 'remappings.txt')):
            return parent
    return source.parent


def dependency_graph(source, root):
    texts = {}
    imports = {}
    remaps = []
    for remap_file in root.rglob('remappings.txt'):
        for line in remap_file.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                prefix, destination = line.strip().split('=', 1)
                remaps.append((prefix, remap_file.parent / destination))
    def visit(path):
        path = path.resolve()
        if path in texts:
            return
        text = sanitize_source(path.read_text())
        texts[path] = text
        code = TOKENS.sub(lambda m: ' ' * len(m.group()) if m.group().startswith(('/',)) else m.group(), text)
        for match in re.finditer(r'\bimport\s+(?:[^;]*?\bfrom\s+)?["\']([^"\']+)["\'][^;]*;', code):
            name = match[1]
            options = [path.parent / name, root / name, root / 'node_modules' / name]
            options += [destination / name[len(prefix):] for prefix, destination in remaps if name.startswith(prefix)]
            # Resolve vendored packages only when the suffix identifies one file.
            options += list(root.glob('**/node_modules/' + name))
            if name.startswith('@openzeppelin/'):
                options += list(root.glob('**/openzeppelin-contracts/' + name.split('/', 1)[1]))
            found = next((p.resolve() for p in options if p.is_file() and p.resolve().is_relative_to(root)), None)
            if found is None:
                raise PreparationError('MISSING_DEPENDENCY', f'Missing dependency {name} imported by {path.name}')
            imports[(path, name)] = found
            visit(found)
    visit(source)
    return texts, imports


@contextmanager
def staged_source(source):
    source = source.resolve()
    root = project_root(source)
    metadata = {'selected': True, 'pragma': '; '.join(detect_pragmas(source.read_text())), 'compiler_used': None, 'compiler_version_attempted': None}
    try:
        texts, imports = dependency_graph(source, root)
        versions = compatible_compilers('\n'.join(texts.values()))
        if not versions:
            raise PreparationError('COMPILER_VERSION_UNAVAILABLE', 'No installed compiler satisfies source and dependency pragmas')
        version = versions[0]
        metadata.update(compiler_used=version, compiler_version_attempted=version)
        binary = Path(ARTIFACTS_DIR) / f'solc-{version}' / f'solc-{version}'
        if not binary.is_file():
            raise PreparationError('COMPILER_VERSION_UNAVAILABLE', f'Installed compiler binary unavailable: {version}')
        with tempfile.TemporaryDirectory(prefix='direct-sanitized-') as temp:
            stage = Path(temp)
            for path, text in texts.items():
                target = stage / path.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            remappings = []
            for (owner, name), destination in imports.items():
                remappings.append(f'{stage / owner.relative_to(root).parent}/:{name}={stage / destination.relative_to(root)}')
            yield stage / source.relative_to(root), stage, {'solc': str(binary), 'compile_force_framework': 'solc', 'solc_remaps': remappings, 'solc_args': f'--allow-paths {stage}'}, metadata
    except PreparationError as exc:
        exc.metadata = {**metadata, **exc.metadata}
        raise
    except Exception as exc:
        raise PreparationError('COMPILATION_FAILED', str(exc), metadata) from exc
