"""Prepare offline or explicitly execute the seven-source development pilot."""
import argparse,json
from pathlib import Path
from context_audit.development_pilot import prepare,execute
from context_audit.v2_artifacts import digest


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--parent-manifest',type=Path,required=True)
    prep.add_argument('--output',type=Path,required=True);prep.add_argument('--run-output',type=Path,required=True)
    run=sub.add_parser('execute');run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--approved-plan-sha256',required=True);run.add_argument('--run',action='store_true');run.add_argument('--resume',action='store_true')
    run.add_argument('--acknowledge-partial',action='append',default=[])
    a=p.parse_args()
    if a.command=='prepare':print('Prepared offline. Approval SHA256:',digest(prepare(a.parent_manifest,a.output,a.run_output)))
    else:
        plan=json.loads(a.plan.read_text())
        if not a.run or digest(plan)!=a.approved_plan_sha256:p.error('Explicit --run and exact approved pilot checksum required')
        print(json.dumps(execute(plan,resume=a.resume,acknowledge_partial=a.acknowledge_partial),indent=2))


if __name__=='__main__':main()
