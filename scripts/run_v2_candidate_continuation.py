"""Prepare an explicit candidate retry offline; execute only after checksum approval."""
import argparse
import json
from pathlib import Path
from context_audit.v2_candidate_continuation import prepare,execute
from context_audit.v2_artifacts import digest


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--parent-manifest',type=Path,required=True)
    prep.add_argument('--case-id',required=True);prep.add_argument('--output',type=Path,required=True);prep.add_argument('--plan',type=Path,required=True)
    run=sub.add_parser('execute');run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--approved-plan-sha256',required=True);run.add_argument('--run',action='store_true');run.add_argument('--resume',action='store_true')
    a=p.parse_args()
    if a.command=='prepare':
        plan=prepare(a.parent_manifest,a.case_id,a.output);a.plan.parent.mkdir(parents=True,exist_ok=True)
        with a.plan.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
        print('Prepared offline; approval SHA256:',digest(plan))
    else:
        plan=json.loads(a.plan.read_text())
        if not a.run or digest(plan)!=a.approved_plan_sha256:p.error('Explicit --run and approved plan checksum required')
        result=execute(plan,resume=a.resume);print(json.dumps(result['coverage_counts'],indent=2))


if __name__=='__main__':main()
