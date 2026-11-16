"""Explicit frozen-cohort B v2 execution or separate post-inference scoring."""
import argparse
import json
from pathlib import Path
from context_audit.v2_artifacts import digest,file_hash
from context_audit.v2_dataset import execute_cohort,validate_finalized


def main():
    p=argparse.ArgumentParser(__doc__); sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('execute'); run.add_argument('--manifest',type=Path,required=True)
    run.add_argument('--cohort',choices=['development','held_out'],required=True)
    run.add_argument('--approved-plan-sha256',required=True);run.add_argument('--run',action='store_true');run.add_argument('--resume',action='store_true');run.add_argument('--acknowledge-partial',action='append',default=[])
    score=sub.add_parser('summarize');score.add_argument('--manifest',type=Path,required=True)
    score.add_argument('--reviews',type=Path);score.add_argument('--output',type=Path,required=True);score.add_argument('--cohort',choices=['development','held_out','all'],default='development')
    a=p.parse_args();manifest=json.loads(a.manifest.read_text())
    if a.command=='execute':
        if not a.run or digest({'manifest_sha256':digest(manifest),'cohort':a.cohort})!=a.approved_plan_sha256:p.error('Exact cohort-bound approval checksum and --run required')
        print(json.dumps(execute_cohort(manifest,a.cohort,resume=a.resume,acknowledge_partial=a.acknowledge_partial),indent=2))
    else:
        from context_audit.v2_dataset_scoring import summarize,write_summary
        evaluation_path=Path(manifest['evaluation_path'])
        if file_hash(evaluation_path)!=manifest['evaluation_sha256']:p.error('Evaluation metadata changed')
        manifest={**manifest,'cases':[c for c in manifest['cases'] if a.cohort=='all' or c['cohort']==a.cohort]}
        reports={};ledgers={}
        for case in manifest['cases']:
            root=Path(case['output'])
            if (root/'budget_ledger.json').exists():ledgers[case['id']]=json.loads((root/'budget_ledger.json').read_text())
            if (root/'finalized.json').exists():
                validate_finalized(case,manifest['configuration'])
                reports[case['id']]=json.loads((root/'analysis/report.json').read_text())
        summary=summarize(manifest,json.loads(evaluation_path.read_text()),reports,
            json.loads(a.reviews.read_text()) if a.reviews else None,ledgers=ledgers)
        write_summary(a.output,summary)


if __name__=='__main__':main()
