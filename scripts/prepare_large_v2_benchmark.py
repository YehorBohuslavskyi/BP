"""Offline large benchmark preparation v1. No inference or dependency installation commands."""
import argparse
import json
from pathlib import Path
from context_audit.large_benchmark import publish,worker


def main():
    parser=argparse.ArgumentParser(__doc__);sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--dataset-root',type=Path,required=True);prep.add_argument('--output',type=Path,required=True)
    prep.add_argument('--history-root',type=Path,action='append',default=None)
    for name,default in [('max-source-bytes',40000),('max-functions',30),('max-summary-functions',80),('max-batches',4),
                         ('max-per-project',3),('timeout-seconds',45),('development-percent',20),('validation-percent',20)]:
        prep.add_argument('--'+name,type=int,default=default)
    prep.add_argument('--near-duplicate-threshold',type=float,default=.85)
    prep.add_argument('--seed',default='mode-b-v2-large-preparation-v1')
    prep.add_argument('--resume-preparation-from',type=Path)
    w=sub.add_parser('_worker',help=argparse.SUPPRESS)
    w.add_argument('--source',type=Path,required=True);w.add_argument('--result',type=Path,required=True)
    for name in ('max-functions','max-summary-functions','max-batches'):w.add_argument('--'+name,type=int,required=True)
    w.add_argument('--compiler',required=True)
    args=parser.parse_args()
    if args.command=='_worker':
        worker(args.source,args.result,args.max_functions,args.max_summary_functions,args.max_batches,args.compiler)
    else:
        keys=('max_source_bytes','max_functions','max_summary_functions','max_batches','max_per_project','timeout_seconds',
              'development_percent','validation_percent','near_duplicate_threshold','seed')
        options={k:getattr(args,k) for k in keys}
        options['resume_preparation_from']=str(args.resume_preparation_from.resolve()) if args.resume_preparation_from else None
        if (any(options[k]<1 for k in keys[:6]) or not 0<=args.development_percent<=100 or
            not 0<=args.validation_percent<=100 or args.development_percent+args.validation_percent>100 or
            not 0<args.near_duplicate_threshold<=1):parser.error('Invalid limits, split percentages or similarity threshold')
        result=publish(args.dataset_root,args.output,options,args.history_root or [Path(p) for p in ('examples','experiments','runs','benchmarks','results','docs')])
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
