"""Offline cohort preparation. Evaluation labels are saved separately, never sent to workers."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from context_audit.datasets.dappscan import DAppSCAN
from context_audit import direct, direct_discovery as d
from context_audit.development_experiment import prepare
from context_audit.direct_preparation import dependency_graph, project_root, sanitize_source, ANNOTATION, CATEGORY_LOCATION, TOKENS
from context_audit.direct_evaluation import relevant_sessions
from context_audit.v2_artifacts import atomic_json, digest, file_hash


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Offline artifacts already exist; choose a new output')
    config = json.loads(args.selection.read_text())
    dataset = DAppSCAN(config['dataset_root'])
    summaries = []
    with patch('openai.OpenAI.__init__', side_effect=AssertionError('Offline preparation forbids API clients')):
        for case in config['cases']:
            source = dataset.source_path(case['file'])
            contracts, catalog = d.prepare(source)
            payloads, _ = direct.prepare(source)
            structural = d.run_discovery(contracts, catalog)
            root = args.output / case['id']
            atomic_json(root / 'structure.json', structural)
            (root / 'structure.md').write_text(d.markdown(structural))
            texts, _ = dependency_graph(source, project_root(source))
            annotations_removed = sum(Path(path).read_text() != text for path, text in texts.items())
            for fragment in catalog.fragments.values():
                text = fragment.get('source', '')
                assert sanitize_source(text) == text
                assert not any((ANNOTATION.search(m.group()) or CATEGORY_LOCATION.search(m.group()))
                    for m in TOKENS.finditer(text) if m.group().startswith(('//', '/*')))
            for batch in structural['batches']:
                wire = json.dumps(d.messages(batch))
                assert 'SWC-' not in wire and 'ground_truth' not in wire and 'audit_reports' not in wire
            labels = dataset.labels(case['file'])
            resolution = []
            for label in labels:
                matches, status = relevant_sessions(label, payloads)
                resolution.append({'label': label, 'resolution': status,
                    'functions': [m['target']['signature'] for m in matches],
                    'modes': [m['target']['preparation_mode'] for m in matches]})
            atomic_json(args.output / 'evaluation_only' / (case['id'] + '.json'),
                        {'file': case['file'], 'labels': labels, 'readiness': resolution})
            plans = {}
            for method in ('b1', 'b2'):
                output = Path('runs/mode-b-v2-development-2026-11-09') / case['id'] / method
                plan = prepare(source, config['model'], output, method,
                               case['max_calls_per_method'], case['max_tokens_per_method'])
                atomic_json(root / (method + '-plan.json'), plan)
                plans[method] = {'path': str(root / (method + '-plan.json')), 'sha256': digest(plan), 'output': str(output)}
            atomic_json(root / 'sanitization.json', {'source_sha256': file_hash(source),
                'dependency_hashes': {str(path): file_hash(path) for path in texts},
                'dependency_files': len(texts), 'files_with_annotations_removed': annotations_removed,
                'catalog_fragments_checked': len(catalog.fragments), 'catalog_sanitization_idempotent': True,
                'discovery_transport_no_labels': True, 'source_identity': catalog.source_identity})
            summaries.append({**case, 'source': str(source), 'v1_functions': len(payloads),
                'v2_functions': len(structural['coverage']), 'batches': len(structural['batches']),
                'preparation': catalog.preparation_metadata, 'estimates': plan['initial_prompt_estimated_tokens'],
                'plans': plans})
            print(case['id'],len(payloads),len(structural['coverage']),len(structural['batches']),flush=True)
    atomic_json(args.output / 'cohort.json', {'cases': summaries, 'status': 'OFFLINE_ONLY_AWAITING_APPROVAL'})


if __name__ == '__main__':
    main()
