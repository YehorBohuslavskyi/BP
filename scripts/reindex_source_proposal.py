"""Build a fresh development source/index proposal offline, without label files.

Existing proposal files, source, case identities, splits and frozen limits are
preserved. This prepares source metadata only and grants no inference approval.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

if sys.prefix != sys.base_prefix:
    os.environ.setdefault('VIRTUAL_ENV',sys.prefix)
os.environ['PATH']=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')

from solc_select.solc_select import ARTIFACTS_DIR
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.v2_artifacts import atomic_json, digest, file_hash, implementation_hash

ROOT=Path(__file__).resolve().parents[1]


def prepare(parent, output, case_ids):
    parent=Path(parent).resolve()
    output=Path(output).resolve()
    if output.exists():
        raise ValueError('FRESH_OUTPUT_REQUIRED')
    if output.is_relative_to(parent) or any(output.is_relative_to(ROOT/name) for name in ('runs','experiments')):
        raise ValueError('HISTORICAL_OR_PARENT_OUTPUT_FORBIDDEN')
    if not 1 <= len(case_ids) <= 3 or len(case_ids)!=len(set(case_ids)):
        raise ValueError('ONE_TO_THREE_EXACT_CASE_IDS_REQUIRED')
    manifest_path=parent/'manifest.json'
    original=json.loads(manifest_path.read_text())
    selected=[c for c in original['cases'] if c['id'] in case_ids]
    if len(selected)!=len(case_ids) or len({c['id'] for c in selected})!=len(selected):
        raise ValueError('UNKNOWN_OR_AMBIGUOUS_CASE_ID')
    for case in selected:
        if case['split']!='development':
            raise ValueError('DEVELOPMENT_ONLY')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',case['id']):
            raise ValueError('INVALID_CASE_ID')
    output.parent.mkdir(parents=True,exist_ok=True)
    proofs=[]
    refreshed=[]
    with tempfile.TemporaryDirectory(prefix='.source-reindex-',dir=output.parent) as directory:
        stage=Path(directory)
        with patch('socket.socket.connect',side_effect=AssertionError('OFFLINE_ONLY')), \
             patch('socket.create_connection',side_effect=AssertionError('OFFLINE_ONLY')), \
             patch('openai.OpenAI.__init__',side_effect=AssertionError('OFFLINE_ONLY')):
            for case in selected:
                source=Path(case['source']).resolve()
                old_identity=case['source_identity']
                if file_hash(source)!=old_identity['source_sha256']:
                    raise ValueError('FROZEN_SOURCE_CHANGED')
                contracts,catalog=d.prepare(source)
                for key in ('source_sha256','sanitized_project_sha256','compiler'):
                    if catalog.source_identity[key]!=old_identity[key]:
                        raise ValueError('SOURCE_DEPENDENCY_OR_COMPILER_CHANGED')
                structural=d.run_discovery(contracts,catalog)
                if not structural['coverage'] or any(not r['included'] for r in structural['coverage']):
                    raise ValueError('REINDEX_INCOMPLETE_COVERAGE')
                for fragment in catalog.fragments.values():
                    v.safe_fragment(fragment)
                relative='prepared/'+case['id']
                atomic_json(stage/relative/'structure.json',structural)
                provenance=dict(source_identity=catalog.source_identity,metadata=catalog.preparation_metadata,
                    fragment_metadata={fid:dict(kind=f['kind'],name=f['name'],source_sha256=digest(f['source']),
                        location=catalog.fragment_locations[fid]) for fid,f in catalog.fragments.items()})
                atomic_json(stage/relative/'provenance.json',provenance)
                # Whitelist source-side execution metadata; no evaluation payload
                # or old inference output can enter the new preparation bundle.
                keys=('id','source','dataset_file','project','split','cohort','model','limits','budget')
                new={key:copy.deepcopy(case[key]) for key in keys if key in case}
                new.update(source=str(source),source_identity=catalog.source_identity,prepared_artifact=relative)
                refreshed.append(new)
                compiler=catalog.source_identity['compiler']
                binary=Path(ARTIFACTS_DIR)/('solc-'+compiler)/('solc-'+compiler)
                proofs.append(dict(case_id=case['id'],source_sha256=file_hash(source),
                    compiler_binary=str(binary),compiler_binary_sha256=file_hash(binary),
                    source_identity_matches_except_protocol=True,original_case_sha256=digest(case),
                    functions=len(structural['coverage']),discovery_batches=len(structural['batches']),
                    API_calls=0,inference_calls=0,token_count_calls=0))
        result=dict(version=1,purpose='Fresh development source-only reindex; no inference authorization',
            parent_proposal=str(parent),parent_manifest_sha256=file_hash(manifest_path),cases=refreshed,
            preparation_implementation_sha256=implementation_hash(['direct_preparation','direct','context','catalog','function_index']),
            entrypoint_sha256=file_hash(__file__),compiler_proofs=proofs,
            original_case_order_preserved=True,evaluation_labels_loaded=False,execution_authorized=False)
        atomic_json(stage/'manifest.json',result)
        atomic_json(stage/'source-preparation-audit.json',dict(parent_manifest_sha256=file_hash(manifest_path),
            cases=proofs,evaluation_labels_loaded=False,source_or_budget_changes=False))
        if output.exists():
            raise ValueError('OUTPUT_APPEARED')
        os.rename(stage,output)
    return result


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--parent-proposal',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case-id',action='append',required=True)
    args=parser.parse_args()
    result=prepare(args.parent_proposal,args.output,args.case_id)
    print(json.dumps(dict(cases=len(result['cases']),manifest_sha256=digest(result),
                         inference_calls=0,evaluation_labels_loaded=False),indent=2))


if __name__=='__main__':
    main()
