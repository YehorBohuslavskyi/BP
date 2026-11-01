"""Read existing static/adjudication evidence; no inference, analysis, or relabeling."""
from collections import Counter,defaultdict
import csv,hashlib,json,shutil
from pathlib import Path
from context_audit.findings import parse_slither_findings
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'examples/defihacklabs/evaluation/final20'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 names=['finding_inventory.json','finding_inventory.csv','finding_adjudication_candidates.md','finding_level_status.md']
 assert not any((BASE/n).exists() for n in names),'Refusing overwrite'
 before={str(p):sha(p) for p in (BASE.parent).rglob('*') if p.is_file()}
 status=json.loads((BASE/'source_status.json').read_text())
 cases=[r for g in ['records','supplemental_records'] for r in status.get(g,[]) if r['source_status']=='SOURCE_READY']
 baseline={r['incident_id']:r for r in json.loads((BASE/'slither_baseline.json').read_text())['records']}
 pilot=json.loads((BASE.parent/'slither_baseline.json').read_text())['records'][0]
 baseline['spankchain']=pilot
 label_path=ROOT/'test/defihacklabs/evidence/validation-record.json'
 labels={r['slither_id']:r for r in json.loads(label_path.read_text())['claims']}
 scope_notes={'B':'Creator/unopened equality guards only; not timeout function safety.',
              'C':'Comparison-level invariant only; excludes separate unchecked arithmetic and malicious token concerns.',
              'A':'Fixed-recipient claim versus separate reopen/replay payout issue remains disputed.',
              'D':'Applicable conservative historical assembly review flag versus actual mutability defect remains disputed.'}
 records=[];coverage=[];inputs=[]
 for case in cases:
  ident=case['incident_id'];b=baseline[ident];raws=[]
  if ident=='spankchain':
   raws=[BASE.parent.parent/'SpankChain_slither.json']
   extra=Path('/tmp/spank-validation-slither.json')
   if extra.exists():
    # Preserve the already-existing independent-validation analyzer output as a new read-only inventory input.
    dest=BASE/'finding_inventory_inputs/spankchain-validation-slither.json';dest.parent.mkdir(exist_ok=True);shutil.copyfile(extra,dest);raws.append(dest)
   matches={b['corresponding_finding']['finding_id']};expected=b['full_default_run']['total_findings']
  else:
   raws=[BASE/'contracts'/ident/'evidence/slither.json'];matches={x.get('id',x.get('finding_id')) for x in b.get('corresponding_findings',[])}
   expected=len(matches)+len(b['additional_findings'])
  found={}
  for path in raws:
   report=json.loads(path.read_text());assert report['success']
   inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
   for raw,f in zip(report['results']['detectors'],parse_slither_findings(report)):
    assert f.id
    if f.id in found:continue
    label='KNOWN_TP' if f.id in matches else 'UNLABELED';evidence=[];notes=None
    if f.id in matches:evidence.append(str((BASE.parent/'slither_baseline.json' if ident=='spankchain' else BASE/'slither_baseline.json').relative_to(ROOT)))
    if ident=='spankchain' and f.id in labels:
     independent=labels[f.id];assert label=='UNLABELED','Conflicting independent label'
     label=independent['independent_label'];evidence.append(str(label_path.relative_to(ROOT)));notes=scope_notes[independent['finding']]
    sf=Path(f.file or '')
    options=[ROOT/sf,BASE/'contracts'/ident/'analysis'/sf.name,BASE/'contracts'/ident/'raw'/sf.name]
    source=next((x for x in options if f.file and x.is_file()),None)
    found[f.id]=dict(case=ident,finding_id=f.id,detector=f.detector,impact=f.impact,confidence=f.confidence,
     contract=f.contract,function=f.function_signature,file=f.file,source_lines=f.lines,
     concise_description=f.description.strip().split('\n')[0],slither_description=f.description,
     existing_incident_relationship='EXACT_KNOWN_VULNERABILITY_MATCH' if f.id in matches else 'NO_MATCH_TO_KNOWN_INCIDENT_ESTABLISHED',
     current_label=label,label_evidence=evidence,label_scope=notes,
     source_available=source is not None,resolved_source_path=str(source.relative_to(ROOT)) if source else None,
     evidence_path=str(path.relative_to(ROOT)))
  records+=list(found.values());coverage.append(dict(case=ident,recorded_default_findings=expected,recovered_individual_findings=len(found),missing_individual_findings=max(0,expected-len(found)),complete=len(found)==expected))
 assert all(any(r['finding_id']==id for r in records) for id in labels),'Independent finding missing from inventory'
 counts=dict(Counter(r['current_label'] for r in records));bycase={c['incident_id']:dict(total=sum(r['case']==c['incident_id'] for r in records),labels=dict(Counter(r['current_label'] for r in records if r['case']==c['incident_id']))) for c in cases}
 detectors={d:dict(total=sum(r['detector']==d for r in records),labels=dict(Counter(r['current_label'] for r in records if r['detector']==d))) for d in sorted({r['detector'] for r in records})}
 eligible=[r for r in records if r['current_label']=='UNLABELED' and r['impact'] in ['High','Medium'] and r['source_available'] and r['function']]
 # Heuristic rank is only adjudication practicality, not vulnerability truth.
 eligible.sort(key=lambda r:(r['impact']!='High',(max(r['source_lines'])-min(r['source_lines'])) if r['source_lines'] else 100000,len(r['slither_description']),r['case'],r['finding_id']))
 candidates=[];case_counts=Counter();pair_counts=Counter();detector_counts=Counter()
 while eligible and len(candidates)<20:
  eligible.sort(key=lambda r:(case_counts[r['case']],pair_counts[(r['case'],r['detector'])],detector_counts[r['detector']],r['impact']!='High',max(r['source_lines'])-min(r['source_lines']) if r['source_lines'] else 100000,len(r['slither_description'])))
  r=eligible.pop(0);candidates.append(r);case_counts[r['case']]+=1;pair_counts[(r['case'],r['detector'])]+=1;detector_counts[r['detector']]+=1
 data=dict(experimental_unit='INDIVIDUAL_SLITHER_FINDING',inventory_complete=all(c['complete'] for c in coverage),total_recovered_findings=len(records),recorded_findings_total=sum(c['recorded_default_findings'] for c in coverage),coverage=coverage,label_counts=counts,by_case=bycase,by_detector=detectors,records=records,inputs=inputs,
 cohort=dict(status='INCOMPLETE_INDEPENDENT_LABELS',frozen=False,target_validated_fp_approx=10,target_known_tp_range=[5,10],available_validated_fp=counts.get('VALIDATED_FP',0),available_known_tp=counts.get('KNOWN_TP',0),eligible_findings=counts.get('VALIDATED_FP',0)+counts.get('KNOWN_TP',0)),
 limitations=['Recovered findings only; SpankChain full default JSON is absent. No missing rows invented.', 'Manual candidate ranking is heuristic; not a new TP/FP judgment.','Existing incident-level misses do not label individual warnings or become LLM failures.','No precision, FP reduction or LLM-performance metrics computed; no cohort/targets created.'])
 (BASE/'finding_inventory.json').write_text(json.dumps(data,indent=2)+'\n')
 fields=['case','finding_id','detector','impact','confidence','contract','function','file','source_lines','concise_description','existing_incident_relationship','current_label','label_evidence','label_scope']
 with (BASE/'finding_inventory.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(r[k]) if isinstance(r[k],list) else r[k] for k in fields} for r in records)
 lines=['# Manual adjudication candidates','', 'These are 20 unlabeled findings selected for review, not a final LLM cohort. Ranking rotates cases and detector classes, then favors High impact and compact reported line spans. Available source is checked; dependency completeness and testability must be confirmed by a human. A short reported span is not proof of small semantic scope. No inferred FP/TP labels.']
 for n,r in enumerate(candidates,1):
  lines += ['',f"## {n}. {r['case']} — {r['detector']}",'',f"- Finding ID: `{r['finding_id']}`",f"- Target: `{r['contract']}.{r['function']}`",f"- Impact/confidence: {r['impact']} / {r['confidence']}",f"- Source: `{r['resolved_source_path']}`",f"- Reported source lines: {r['source_lines']}",f"- Current label: **{r['current_label']}**",'- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.','', 'Slither description:','', '```text',r['slither_description'].strip(),'```']
 (BASE/'finding_adjudication_candidates.md').write_text('\n'.join(lines)+'\n')
 lines=['# Finding-level real-world evaluation status','',f"Recovered individual findings: **{len(records)}**. Recorded default-run totals: **{data['recorded_findings_total']}**. Inventory complete: **{data['inventory_complete']}**.",f'Label counts: `{json.dumps(counts)}`.','',
 'SpankChain has 126 recorded default findings, but only 14 recoverable individual warnings across its detector-scoped pilot and existing independent-validation JSON. The latter was copied unchanged from the existing local temporary evidence to finding_inventory_inputs/ for durable provenance. The full run is not rerun. Missing SpankChain rows cannot receive labels or be included in individual counts.','',
 '## By case','','| Case | Recovered findings | Labels |','|---|---:|---|']
 for c,v in bycase.items():lines.append(f'| {c} | {v["total"]} | {json.dumps(v["labels"])} |')
 lines+=['','## By detector','','| Detector | Findings | Labels |','|---|---:|---|']
 for d,v in detectors.items():lines.append(f'| {d} | {v["total"]} | {json.dumps(v["labels"])} |')
 lines+=['','## Cohort readiness','', 'Only **2 independently validated FPs** and **2 exact known TPs** are available. The approximate 10-FP and 5–10-TP target is not met. The two disputed SpankChain findings remain excluded. No final LLM cohort or verification targets are created. The validated SpankChain equality labels retain their narrow warning-level limitations; actual LLM rejections are not independent labels.', '',
 '## Best 20 candidates','','| Rank | Case | Detector | Target | Finding ID |','|---:|---|---|---|---|']
 for n,r in enumerate(candidates,1):lines.append(f"| {n} | {r['case']} | {r['detector']} | {r['contract']}.{r['function']} | {r['finding_id']} |")
 lines+=['','Full analyzer descriptions, source lines, current labels and review rationale appear in finding_adjudication_candidates.md.','',
 '## Workflow','', '1. Recover the missing full SpankChain JSON if available; do not manufacture finding rows.',
 '2. Independently adjudicate diverse candidates by exact finding ID; record evidence and label scope. Leave uncertainty unlabeled/disputed.',
 '3. Freeze a finding-level cohort only after sufficient independent FP/TP labels exist. Keep labels separate from production model inputs.',
 '4. Later compare before-LLM labeled TP/FP precision with retained TP, filtered FP, inconclusive outcomes, after-LLM precision, TP retention and FP reduction. State treatment of inconclusive outcomes explicitly. Exclude disputed/unlabeled findings from binary metrics.',
 '5. Incident-level Slither misses remain upstream misses, not LLM failures. Supplemental cases retain their roles; this finding-level experiment never rewrites incident-level classifications.',
 '', 'No LLM call, verify_request invocation, source analysis, target change or incident reclassification occurred. Existing files are hash checked.']
 (BASE/'finding_level_status.md').write_text('\n'.join(lines)+'\n')
 for p,h in before.items():assert sha(Path(p))==h,p
 print(json.dumps(dict(total=len(records),recorded_total=data['recorded_findings_total'],coverage=coverage,labels=counts,candidate_count=len(candidates)),indent=2))
 print('PASS: all pre-existing evaluation files unchanged.')
if __name__=='__main__':main()
