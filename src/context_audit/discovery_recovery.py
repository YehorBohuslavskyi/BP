"""Explicit import of a historical, identity-revalidated discovery response."""
import json
from pathlib import Path
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.v2_artifacts import digest, file_hash, implementation_hash


def build_import(path, contracts, catalog, model):
    path = Path(path).resolve()
    recovery = json.loads(path.read_text())
    original_path = Path(recovery['source_artifact']).resolve()
    original = json.loads(original_path.read_text())
    manifest = original.get('manifest', {})
    if (file_hash(original_path) != recovery['source_artifact_sha256'] or
            manifest != recovery['original_manifest'] or manifest.get('version') != 1 or
            manifest.get('executed') is not True or
            manifest.get('artifact_sha256') != digest({k: x for k, x in original.items() if k != 'manifest'})):
        raise ValueError('RECOVERY_ORIGINAL_PROVENANCE_MISMATCH')
    if (manifest['source'] != catalog.source_identity or
            recovery['current_source_identity'] != catalog.source_identity or
            original['contracts'] != contracts or
            digest(catalog.fragments) != catalog.source_identity['catalog_sha256'] or
            digest(catalog.fragment_locations) != catalog.source_identity['locations_sha256'] or
            digest(contracts) != catalog.source_identity['structure_sha256'] or
            digest(getattr(catalog, 'function_index', None)) != catalog.source_identity.get('function_index_sha256') or
            original.get('function_index') != getattr(catalog, 'function_index', None)):
        raise ValueError('RECOVERY_SOURCE_OR_CATALOG_MISMATCH')
    config = manifest['configuration']
    if (config['model'] != model or
            config['schema_sha256'] != digest(d.DiscoveryResponse.model_json_schema()) or
            recovery['normalizer_implementation_sha256'] != implementation_hash(['direct_discovery'])):
        raise ValueError('RECOVERY_MODEL_SCHEMA_OR_NORMALIZER_MISMATCH')
    # This narrowly scoped importer handles one completed historical batch only.
    batches, _ = d.make_batches(contracts, config['max_chars'])
    if len(batches) != 1 or original['batches'] != batches or len(original['rounds']) != 1:
        raise ValueError('RECOVERY_REQUIRES_ONE_MATCHING_BATCH')
    attempt = original['rounds'][0]
    if (attempt['response'].get('status') != 'completed' or
            attempt['response'].get('model') != model or
            digest(attempt['messages'][0]['content']) != config['prompt_sha256'] or
            attempt['messages'][1] != d.messages(batches[0])[1]):
        raise ValueError('RECOVERY_ORIGINAL_REQUEST_MISMATCH')
    diagnostics = []
    parsed = d.validate_response(attempt['response']['assessment'], batches[0], catalog,
                                 candidate_diagnostics=diagnostics)
    if (diagnostics != recovery['candidate_validation'] or
            [c.model_dump() for c in parsed.candidates] != recovery['accepted_candidates'] or
            [f.model_dump() for f in parsed.examined_functions] != recovery['examined_functions'] or
            any(x['status'] != 'accepted' for x in diagnostics) or
            recovery['api_calls_this_reprocessing'] != 0 or recovery['tokens_this_reprocessing'] != 0 or
            recovery['verification_verdicts']):
        raise ValueError('RECOVERY_REVALIDATION_MISMATCH')
    for fragment in catalog.fragments.values():
        v.safe_fragment(fragment)
    # Reuse normal coverage construction; this callback is local replay, never a client.
    imported = d.run_discovery(contracts, catalog, execute=True, max_chars=config['max_chars'],
                              analyze_fn=lambda _: attempt['response'])
    if imported['errors']:
        raise ValueError('RECOVERY_REPLAY_VALIDATION_FAILED')
    for candidate in imported['candidates']:
        v.validate_candidate(candidate, contracts, catalog)
    # Do not pretend that replay was inference under today's prompt/configuration.
    imported.pop('manifest')
    imported['mode'] = 'explicit_historical_discovery_import'
    imported['rounds'] = original['rounds']
    imported['recovery_import'] = {
        'version': 1, 'recovery_path': str(path), 'recovery_sha256': file_hash(path),
        'original_path': str(original_path), 'original_sha256': file_hash(original_path),
        'original_manifest': manifest, 'identity_audit': diagnostics,
        'importer_sha256': implementation_hash(['discovery_recovery']),
        'note': 'Historical discovery accounting and original prompt retained; zero new discovery requests.'}
    return imported


def validate_import(imported, path, contracts, catalog, model):
    if imported != build_import(path, contracts, catalog, model):
        raise ValueError('RECOVERY_IMPORT_CONTENT_MISMATCH')
