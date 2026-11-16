"""Prepare or execute exactly one frozen source through the budgeted B v2 case runner."""
import argparse
import json
from pathlib import Path
from context_audit import direct_verification as v
from context_audit.v2_artifacts import digest,file_hash,discovery_config
from context_audit.v2_dataset import identity,preflight_case,execute_case
from context_audit.v2_dataset_scoring import SCORING_PROTOCOL


def prepare(parent_path,case_id):
    parent=json.loads(Path(parent_path).read_text())
    matches=[c for c in parent['cases'] if c['id']==case_id]
    if len(matches)!=1:raise ValueError('EXACTLY_ONE_CASE_REQUIRED')
    case=matches[0]
    if case['cohort']!='development':raise ValueError('THIS_ENTRY_POINT_IS_DEVELOPMENT_ONLY')
    if case['model']!='gpt-5.4-mini-2026-03-17':raise ValueError('UNEXPECTED_MODEL')
    if parent['scoring_protocol']!=SCORING_PROTOCOL:raise ValueError('SCORING_RULES_CHANGED')
    if 'compiler_proofs' in parent:
        proofs=[p for p in parent['compiler_proofs'] if p['case_id']==case_id]
        if len(proofs)!=1 or file_hash(proofs[0]['compiler_binary'])!=proofs[0]['compiler_binary_sha256']:
            raise ValueError('COMPILER_BINARY_CHANGED')
    if Path(case['output']).exists():raise ValueError('OUTPUT_EXISTS_NO_STAGE_REPLAY')
    preflight_case(case)
    return {'version':1,'scope':'one development contract only','parent_manifest':str(Path(parent_path).resolve()),
        'parent_manifest_sha256':file_hash(parent_path),'case':case,'configuration':identity(),
        'entrypoint_sha256':file_hash(__file__),
        'frozen_protocols':{'discovery':{**discovery_config(24000),'model':case['model']},
            'verification':{**v.configuration(v.Limits(**case['limits'])),'model':case['model']}},
        'scoring_protocol':SCORING_PROTOCOL}


def execute(plan,*,client_factory=None):
    if (plan['version']!=1 or plan['scope']!='one development contract only' or
        plan['entrypoint_sha256']!=file_hash(__file__) or plan['configuration']!=identity()):
        raise ValueError('SINGLE_CASE_CONFIGURATION_CHANGED')
    if file_hash(plan['parent_manifest'])!=plan['parent_manifest_sha256']:
        raise ValueError('PARENT_MANIFEST_CHANGED')
    # Reconstruct the entire approved single-case plan before the existing runner can create a client.
    if prepare(plan['parent_manifest'],plan['case']['id'])!=plan:
        raise ValueError('SINGLE_CASE_PLAN_MISMATCH')
    return execute_case(plan['case'],plan['configuration'],client_factory=client_factory)


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--parent-manifest',type=Path,required=True)
    prep.add_argument('--case-id',required=True);prep.add_argument('--plan',type=Path,required=True)
    run=sub.add_parser('execute');run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--approved-plan-sha256',required=True);run.add_argument('--run',action='store_true')
    a=p.parse_args()
    if a.command=='prepare':
        plan=prepare(a.parent_manifest,a.case_id);a.plan.parent.mkdir(parents=True,exist_ok=True)
        with a.plan.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
        print('Prepared offline; approval SHA256:',digest(plan))
    else:
        plan=json.loads(a.plan.read_text())
        if not a.run or digest(plan)!=a.approved_plan_sha256:p.error('Exact single-case approval checksum and --run required')
        report=execute(plan);print(json.dumps(report['coverage_counts'],indent=2))
        print('Stopped after the approved single contract. No cohort advancement.')


if __name__=='__main__':main()
