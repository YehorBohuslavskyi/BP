"""Small, strict provenance manifests and atomic local checkpoints for Mode B v2."""
import hashlib
import json
import os
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hash(names):
    return digest({name: file_hash(Path(__file__).with_name(name + '.py')) for name in names})


def source_identity(source, staged, root, catalog):
    return {'source_sha256': file_hash(source), 'source_name': source.name,
            'sanitized_project_sha256': digest({p.relative_to(root).as_posix(): file_hash(p)
                for p in sorted(root.rglob('*')) if p.is_file()}),
            'catalog_sha256': digest(catalog.fragments),
            'structure_sha256': digest(catalog.discovery_contracts),
            'locations_sha256': digest(catalog.fragment_locations),
            'compiler': catalog.preparation_metadata.get('compiler_used'),
            'function_index_sha256': digest(getattr(catalog, 'function_index', None)),
            'preparation_sha256': implementation_hash(['direct_preparation', 'direct', 'context', 'catalog', 'function_index']),
            'sanitizer_sha256': implementation_hash(['direct_preparation'])}


def discovery_config(max_chars):
    from context_audit.direct_discovery import SYSTEM_PROMPT, DiscoveryResponse
    return {'model': os.environ.get('OPENAI_MODEL'), 'max_chars': max_chars,
            'prompt_sha256': digest(SYSTEM_PROMPT), 'schema_sha256': digest(DiscoveryResponse.model_json_schema()),
            'implementation_sha256': implementation_hash(['direct_discovery', 'function_index']), 'max_output_tokens': 8000}


def discovery_manifest(result, catalog, max_chars, executed):
    return {'version': 1, 'source': json.loads(json.dumps(getattr(catalog, 'source_identity', None))),
            'configuration': discovery_config(max_chars), 'executed': executed,
            'artifact_sha256': digest({k: v for k, v in result.items() if k != 'manifest'})}


def validate_discovery(result, contracts, catalog, *, expected_model=None):
    manifest = result.get('manifest', {})
    if manifest.get('version') != 1 or not manifest.get('executed'):
        raise ValueError('Saved discovery lacks an executed v2 provenance manifest')
    if not getattr(catalog, 'source_identity', None) or manifest.get('source') != catalog.source_identity:
        raise ValueError('Source, compiler, sanitizer, structure or catalog mismatch')
    if (catalog.source_identity['catalog_sha256'] != digest(catalog.fragments) or
            catalog.source_identity['locations_sha256'] != digest(catalog.fragment_locations) or
            catalog.source_identity['structure_sha256'] != digest(contracts)):
        raise ValueError('Prepared catalog or structure changed since preparation')
    if catalog.source_identity.get('function_index_sha256') != digest(getattr(catalog, 'function_index', None)):
        raise ValueError('Prepared function index changed since preparation')
    if result.get('function_index') != getattr(catalog, 'function_index', None):
        raise ValueError('Discovery function index mismatch')
    config = manifest.get('configuration', {})
    expected = discovery_config(config.get('max_chars'))
    if expected_model is not None:
        expected['model'] = expected_model
    if config != expected:
        raise ValueError('Discovery model, prompt or implementation mismatch')
    if manifest.get('artifact_sha256') != digest({k: v for k, v in result.items() if k != 'manifest'}):
        raise ValueError('Discovery artifact checksum mismatch')
    if result.get('contracts') != contracts:
        raise ValueError('Discovery structures do not match current preparation')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)
