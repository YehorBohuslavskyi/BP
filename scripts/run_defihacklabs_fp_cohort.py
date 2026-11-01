#!/usr/bin/env python3
"""Freeze/prepare an adjudicated finding cohort; explicit --run invokes inference.

The worker reads technical targets only. Ground truth is joined only by summarize(),
after inference. Existing evidence/results are never overwritten or retried.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'examples/defihacklabs/evaluation/final20'
COHORT=BASE/'frozen_fp_cohort.json'
TARGETS=BASE/'frozen_fp_verification_targets.json'
RESULTS=BASE/'fp_llm_results'
LABELS={'KNOWN_TP':'TP','VALIDATED_TP':'TP','VALIDATED_FP':'FP'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):
    with path.open('x') as handle:json.dump(data,handle,indent=2);handle.write('\n')
@contextmanager
def preparation_environment(cwd,compiler):
    previous=Path.cwd();old=os.environ.get('SOLC_VERSION')
    try:
        os.chdir(cwd);os.environ['SOLC_VERSION']=compiler;yield
    finally:
        os.chdir(previous)
        if old is None:os.environ.pop('SOLC_VERSION',None)
        else:os.environ['SOLC_VERSION']=old

def verify_freeze():
    cohort=json.loads(COHORT.read_text())
    assert sha(BASE/'finding_adjudications.json')==cohort['adjudications_sha256']
    for path,digest in cohort['protected_inputs'].items():assert sha(ROOT/path)==digest,path
    audit_path=BASE/'fp_cohort_integrity.json'
    if audit_path.exists():
        audit=json.loads(audit_path.read_text())
        assert sha(COHORT)==audit['cohort_sha256']
        assert sha(BASE/'frozen_fp_cohort.csv')==audit['cohort_csv_sha256']
        assert sha(TARGETS)==audit['targets_sha256']
    return cohort

def freeze():
    import csv
    data=json.loads((BASE/'finding_adjudications.json').read_text())
    eligible=[r for r in data['records'] if r['final_label'] in LABELS]
    assert len(eligible)==15
    assert sum(LABELS[r['final_label']]=='TP' for r in eligible)==5
    inventory=json.loads((BASE/'finding_inventory.json').read_text())
    lookup={(r['case'],r['finding_id']):r for r in inventory['records']}
    # Protect historical inputs, raw/analysis sources, regression evidence and protocol.
    protected={}
    for folder in [BASE.parent,ROOT/'test/defihacklabs',ROOT/'src/context_audit']:
        for path in folder.rglob('*'):
            if not path.is_file() or any(s in path.parts for s in ['.generated','__pycache__']):continue
            if path in [COHORT,BASE/'frozen_fp_cohort.csv',TARGETS] or RESULTS in path.parents:continue
            if path.name in ['fp_reduction_results.json','fp_reduction_results.md']:continue
            protected[str(path.relative_to(ROOT))]=sha(path)
    rows=[]
    from context_audit.findings import parse_slither_findings
    status=json.loads((BASE/'source_status.json').read_text())
    cases={r['incident_id']:r for group in ['records','supplemental_records'] for r in status.get(group,[])}
    for n,r in enumerate(eligible,1):
        inv=lookup[r['case'],r['finding_id']]
        source=ROOT/inv['resolved_source_path'];assert source.is_file()
        evidence=ROOT/inv['evidence_path'];assert evidence.is_file()
        finding,=[f for f in parse_slither_findings(json.loads(evidence.read_text())) if f.id==r['finding_id']]
        # Original file identity is retained; cwd follows the evidence's relative filename.
        relative=Path(finding.file)
        cwd=ROOT if (ROOT/relative).is_file() and (ROOT/relative).resolve()==source.resolve() else source.parent
        rows.append(dict(target_id=f'fp-{n:02d}-{r["finding_id"][:12]}',case=r['case'],finding_id=r['finding_id'],detector=r['detector'],contract=r['contract'],function=r['function'],ground_truth_label=LABELS[r['final_label']],adjudication_label=r['final_label'],provenance=r['provenance'],evidence_references=r['evidence_references'],source_file=str(source.relative_to(ROOT)),source_sha256=sha(source),source_lines=r['source_lines'],slither_description=r['exact_slither_claim'],slither_evidence=str(evidence.relative_to(ROOT)),slither_evidence_sha256=sha(evidence),compiler=cases[r['case']]['compiler_version'],working_directory=str(cwd.relative_to(ROOT)) or '.'))
    result=dict(schema_version=1,experimental_unit='INDIVIDUAL_SLITHER_FINDING',frozen=True,adjudications_sha256=sha(BASE/'finding_adjudications.json'),records=rows,protected_inputs=protected,
        baseline=dict(tp=5,fp=10,fn_within_candidate_cohort=0,precision=5/15,candidate_retention=1.0),
        fixed_protocol=dict(max_rounds=4,selective_retries=False,provider_max_retries=0),
        limitations=['Includes source/mock-based findings and scoped human FP adjudications; labels frozen without re-adjudication.','Not a full-contract or incident vulnerability recall experiment.'])
    assert not COHORT.exists() and not (BASE/'frozen_fp_cohort.csv').exists()
    save(COHORT,result)
    columns=['target_id','case','finding_id','detector','contract','function','ground_truth_label','adjudication_label','provenance','source_file','source_sha256','source_lines','slither_description']
    with (BASE/'frozen_fp_cohort.csv').open('x',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader()
        writer.writerows({k:json.dumps(r[k]) if isinstance(r[k],list) else r[k] for k in columns} for r in rows)

def prepare():
    from context_audit.findings import parse_slither_findings
    from context_audit.verifier import prepare_finding
    cohort=verify_freeze();targets=[]
    for row in cohort['records']:
        source=ROOT/row['source_file'];report=json.loads((ROOT/row['slither_evidence']).read_text())
        finding,=[f for f in parse_slither_findings(report) if f.id==row['finding_id']]
        technical=dict(target_id=row['target_id'],case=row['case'],finding_id=finding.id,detector=finding.detector,source_path=row['source_file'],source_sha256=sha(source),compiler=row['compiler'],finding=asdict(finding),max_rounds=4)
        try:
            with preparation_environment(ROOT/row['working_directory'],row['compiler']):
                payload,catalog=prepare_finding(source,source.parent,finding)
            technical.update(preparation_status='READY',initial_payload=payload,catalog=catalog.to_dict())
        except Exception as error:
            technical.update(preparation_status='ERROR',preparation_error=f'{type(error).__name__}: {error}')
        targets.append(technical)
        print(row['target_id'],technical['preparation_status'],flush=True)
    save(TARGETS,dict(schema_version=1,cohort_sha256=sha(COHORT),targets=targets,
        payload_policy='Only production initial_payload and requested catalog source fragments are sent; no ground-truth file is read by inference worker.'))
    verify_freeze()

def worker(target_id):
    # Do not read cohort/adjudication files in this inference process.
    from context_audit.catalog import FragmentCatalog
    from context_audit.findings import Finding
    from context_audit.llm import analyze,SYSTEM_PROMPT
    from context_audit.verifier import verify_prepared_finding,summarize_verification
    from context_audit.app.presentation import source_context_efficiency
    target,=[r for r in json.loads(TARGETS.read_text())['targets'] if r['target_id']==target_id]
    path=RESULTS/f'{target_id}.json'
    assert not path.exists(),'Existing attempt will not be retried'
    payload=target.get('initial_payload');completed=[];attempts=[]
    record=dict(target_id=target_id,case=target['case'],finding_id=target['finding_id'],detector=target['detector'],status='ERROR',verdict=None,explanation=None,evidence_ids=[],rounds=[],requested_fragments=None,input_tokens=0,output_tokens=0,total_tokens=0,api_calls_attempted=0,model=os.environ.get('OPENAI_MODEL'))
    def adapter(initial,context):
        # Exactly the same system/user messages constructed by production analyze().
        messages=[dict(role='system',content=SYSTEM_PROMPT),dict(role='user',content=json.dumps({**initial,'provided_context':context},ensure_ascii=False))]
        save(RESULTS/f'{target_id}.prompt-{len(attempts)+1}.json',dict(messages=messages))
        attempts.append(1)
        result=analyze(initial,context)
        completed.append(result)
        # Journal successful rounds before later calls can fail.
        save(RESULTS/f'{target_id}.round-{len(completed)}.json',result)
        return result
    try:
        assert target['preparation_status']=='READY',target.get('preparation_error')
        assert os.environ.get('OPENAI_MODEL') and os.environ.get('OPENAI_API_KEY'),'Missing API configuration'
        assert sha(ROOT/target['source_path'])==target['source_sha256']
        catalog=FragmentCatalog((ROOT/target['source_path']).parent);catalog.fragments=target['catalog']
        result=verify_prepared_finding(Finding(**target['finding']),payload,catalog,4,analyze_fn=adapter)
        summary=summarize_verification(result)
        record.update(status='COMPLETED',verdict=result['assessment']['verdict'],explanation=result['assessment']['explanation'],evidence_ids=result['assessment']['evidence_ids'],result=result,summary=summary,rounds=result['rounds'],requested_fragments=summary['requested_fragments'],context_efficiency=source_context_efficiency((ROOT/target['source_path']).read_text(),payload,result),initial_payload=payload)
    except Exception as error:
        # Exception text can contain provider request data; preserve type only.
        record.update(error_type=type(error).__name__,error='Preparation, configuration, provider, or validation failure; no automatic retry.',completed_round_results=completed,rounds=[{'round':n,'result':r} for n,r in enumerate(completed,1)],usage_may_be_incomplete=bool(attempts and len(completed)<len(attempts)))
        record['requested_fragments']=len({identity for r in completed for identity in r['assessment'].get('requested_ids',[])})
    for key in ['input_tokens','output_tokens','total_tokens']:
        record[key]=sum((r.get('usage') or {}).get(key,0) for r in completed)
    record['api_calls_attempted']=len(attempts)
    save(path,record)

def run():
    verify_freeze()
    assert os.environ.get('OPENAI_API_KEY') and os.environ.get('OPENAI_MODEL'),'Set OPENAI_API_KEY and OPENAI_MODEL; no API calls made'
    targets=json.loads(TARGETS.read_text());assert targets['cohort_sha256']==sha(COHORT)
    RESULTS.mkdir(exist_ok=True)
    configuration=dict(model=os.environ['OPENAI_MODEL'],max_rounds=4,cohort_sha256=sha(COHORT),targets_sha256=sha(TARGETS),runner_sha256=sha(Path(__file__).resolve()))
    config_path=RESULTS/'run_configuration.json'
    if config_path.exists():assert json.loads(config_path.read_text())==configuration,'Run configuration changed; refusing mixed-model/protocol run'
    else:save(config_path,configuration)
    # Run serially with identical fixed protocol, independent of label/correctness.
    for target in targets['targets']:
        out=RESULTS/f'{target["target_id"]}.json'
        if out.exists():
            print('Existing result retained; no retry:',target['target_id'],flush=True);continue
        # A partial attempt is never silently resumed/retried.
        assert not list(RESULTS.glob(f'{target["target_id"]}.prompt-*.json')),'Partial attempt exists; manual audit required'
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',target['target_id']],cwd=ROOT,check=True)
    verify_freeze()

def replace_summary(path,content):
    """Atomically refresh a derived report; never rewrite result/evidence inputs."""
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix=f'.{path.name}.',delete=False) as handle:
            temporary=Path(handle.name)
            handle.write(content)
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def summarize():
    cohort=verify_freeze();targets={r['target_id']:r for r in json.loads(TARGETS.read_text())['targets']};rows=[]
    counts={k:0 for k in ['tp_retained','tp_lost','tp_inconclusive','fp_filtered','fp_retained','fp_inconclusive','errors','not_run']}
    results=[]
    for frozen in cohort['records']:
        path=RESULTS/f'{frozen["target_id"]}.json';result=json.loads(path.read_text()) if path.exists() else None
        verdict=result.get('verdict') if result else None;status=result['status'] if result else 'NOT_RUN'
        truth=frozen['ground_truth_label'];correct='not evaluated'
        if status=='COMPLETED':
            assert verdict in ['confirmed','false_positive','inconclusive']
            if verdict=='inconclusive':key='tp_inconclusive' if truth=='TP' else 'fp_inconclusive';correct='abstain'
            elif truth=='TP':key='tp_retained' if verdict=='confirmed' else 'tp_lost';correct='yes' if verdict=='confirmed' else 'no'
            else:key='fp_filtered' if verdict=='false_positive' else 'fp_retained';correct='yes' if verdict=='false_positive' else 'no'
            counts[key]+=1
        else:counts['errors' if result else 'not_run']+=1
        if result:results.append(result)
        rows.append(dict(case=frozen['case'],finding_id=frozen['finding_id'],detector=frozen['detector'],ground_truth=truth,llm_verdict=verdict,status=status,correct=correct,rounds=len(result['rounds']) if result else None,requested_fragments=result.get('requested_fragments') if result else None,total_tokens=result.get('total_tokens') if result else None,preparation_status=targets[frozen['target_id']]['preparation_status']))
    finalized=sum(r['status']=='COMPLETED' for r in rows)
    all_final=finalized==15 and counts['errors']==0 and counts['not_run']==0
    binary_den=counts['tp_retained']+counts['fp_retained']
    conservative_den=binary_den+counts['tp_inconclusive']+counts['fp_inconclusive']
    api_calls=sum(r['api_calls_attempted'] for r in results)
    metrics=dict(**counts,tp_retention=counts['tp_retained']/5 if all_final else None,fp_reduction=counts['fp_filtered']/10 if all_final else None,
        precision_after_llm_binary=counts['tp_retained']/binary_den if all_final and binary_den else None,
        conservative_precision=(counts['tp_retained']+counts['tp_inconclusive'])/conservative_den if all_final and conservative_den else None,
        inconclusive_rate=(counts['tp_inconclusive']+counts['fp_inconclusive'])/15 if all_final else None,
        total_api_calls_attempted=api_calls,total_tokens=sum(r['total_tokens'] for r in results),
        average_rounds=sum(len(r['rounds']) for r in results)/len(results) if results else None,
        average_requested_fragments=sum(r.get('requested_fragments') or 0 for r in results)/len(results) if results else None,
        usage_may_be_incomplete=any(r.get('usage_may_be_incomplete',False) for r in results))
    saved_models=sorted({r['model'] for r in results if r.get('model')})
    result=dict(status='COMPLETE' if all_final else 'INCOMPLETE',cohort_sha256=sha(COHORT),adjudications_sha256=cohort['adjudications_sha256'],model=saved_models[0] if len(saved_models)==1 else None,models=saved_models,baseline=cohort['baseline'],llm_metrics=metrics,records=rows,
        configuration_ready=bool(os.environ.get('OPENAI_MODEL') and os.environ.get('OPENAI_API_KEY')),
        methodological_notes=['Candidate-level evaluation only: denominator 15; unrelated incident misses/421 findings excluded.','Errors and NOT_RUN are not fabricated inconclusive verdicts; performance rates withheld until all 15 final results exist.','Binary precision = retained TP / (retained TP + retained FP).','Conservative precision = (retained TP + inconclusive TP) / (retained TP + retained FP + inconclusive TP + inconclusive FP).','Four-round production protocol; no selective retries. Prompt journals contain production messages only.'])
    # Canonical summaries are derived views; regenerate them without touching inputs.
    lines=['# Frozen finding-level FP-reduction evaluation','',f"Status: **{result['status']}**. Current API configuration ready: {result['configuration_ready']} (not required for summarization).",
        '', 'Frozen baseline: TP 5, FP 10, candidate-level FN 0; precision 5/15 = 33.33%; candidate retention 100%.','',
        '## LLM outcomes','','```json',json.dumps(metrics,indent=2),'```','',
        'NOT_RUN is not an LLM error, false negative, or abstention. Null rates mean the experiment has not completed; zero observed calls/tokens is not zero retention. No earlier pilot results are substituted for this frozen run.','',
        '| Case | Detector | Finding ID | Ground truth | LLM verdict/status | Correct? | Rounds | Requested fragments | Total tokens |','|---|---|---|---|---|---|---:|---:|---:|']
    for row in rows:lines.append('| '+' | '.join(str(row[k]) if row[k] is not None else '—' for k in ['case','detector','finding_id','ground_truth'])+' | '+str(row['llm_verdict'] or row['status'])+' | '+' | '.join(str(row[k]) if row[k] is not None else '—' for k in ['correct','rounds','requested_fragments','total_tokens'])+' |')
    lines+=['','## Methodology','',*result['methodological_notes'],'','Ground truth is stored only in the frozen cohort and post-inference reports. Technical targets contain production findings/payload/catalog only; workers do not read adjudication or ground-truth files. Source and finding names/comments remain normal production data. No expected outcome, regression result or historical explanation is appended to prompts. Per-call prompt journals enable audit after a real run.']
    replace_summary(BASE/'fp_reduction_results.json',json.dumps(result,indent=2)+'\n')
    replace_summary(BASE/'fp_reduction_results.md','\n'.join(lines)+'\n')
    print(json.dumps(metrics,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--freeze-and-prepare',action='store_true');parser.add_argument('--run',action='store_true');parser.add_argument('--summarize',action='store_true');parser.add_argument('--worker');args=parser.parse_args()
    if args.worker:worker(args.worker);return
    if args.freeze_and_prepare:freeze();prepare()
    if args.run:run()
    if args.summarize:summarize()
if __name__=='__main__':main()
