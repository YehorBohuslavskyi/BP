"""Freeze local B v2-only preparation and separate scoring metadata. No API clients."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from context_audit.datasets.dappscan import DAppSCAN
from context_audit import direct_discovery as d
from context_audit.direct_preparation import dependency_graph,project_root,TOKENS,sanitize_source,ANNOTATION,CATEGORY_LOCATION
from context_audit.v2_artifacts import atomic_json,digest,file_hash
from context_audit.v2_dataset import case_plan,identity,LIMITS
from context_audit.v2_dataset_scoring import SCORING_PROTOCOL
from context_audit.v2_artifacts import discovery_config
from context_audit.direct_verification import configuration


def targets_for(label,contracts,catalog,source):
    result=[]; source_file=source.relative_to(project_root(source)).as_posix()
    for contract in contracts:
        for f in contract['functions']:
            loc=catalog.fragment_locations.get(f['fragment_id'],{})
            if loc.get('file')!=source_file:continue
            name=(label.get('function') or '').replace(' ','')
            if name and (f['signature'] if '(' in name else f['signature'].split('(')[0])!=name:continue
            if label['lines'] and not set(label['lines']) & set(loc['lines']):continue
            if not name and not label['lines']:continue
            result.append({'contract':contract['contract'],'signature':f['signature'],'fragment_id':f['fragment_id'],'location':loc})
    return result if len(result)==1 else []


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--dataset-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--run-output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.run_output.exists():p.error('Use new preparation and execution directories')
    ds=DAppSCAN(a.dataset_root); model='gpt-5.4-mini-2026-03-17'; out=a.output
    dev=json.loads(Path('experiments/mode-b-v2-development-2026-11-09/selection.json').read_text())['cases']
    excluded_projects={Path(c['file']).parts[0] for c in dev}
    for path in Path('examples/dappscan/evaluation/direct_detection').rglob('pilot_manifest.json'):
        excluded_projects.update(c.get('project',Path(c['file']).parts[0]) for c in json.loads(path.read_text()).get('cases',[]) if c.get('file'))
    screen=[]; universe=[]
    for report in sorted((ds.base/'SWCsource').rglob('*.json')):
        file=report.relative_to(ds.base/'SWCsource').with_suffix('.sol').as_posix()
        if Path(file).parts[0] in excluded_projects:continue
        try:
            src=ds.source_path(file);text=src.read_text()
            if not re.search(r'SWC-(?:104|105|107|112|115)',report.read_text()):continue
            n=len(re.findall(r'\bfunction\s+(?:\w+\s*)?\(',text))
            if not 2<=n<=12 or len(text)>=22000:continue
            labels=ds.labels(file)
            if labels:universe.append({'file':file,'labels':labels})
        except (ValueError,OSError):continue
    atomic_json(out/'screening_universe.json',{'criteria':'mirrored labelled sources; 2..12 lexical functions; <22000 chars; historical/development projects excluded','excluded_projects':sorted(excluded_projects),'candidates':universe})
    cases=[];evaluation={};fingerprints=set();projects=set();picked=0
    selected=[{**c,'cohort':'development','labels':ds.labels(c['file'])} for c in dev]
    def add(candidate):
        file=candidate['file'];src=ds.source_path(file);cohort=candidate['cohort'];id=candidate['id']
        contracts,cat=d.prepare(src); batches,coverage=d.make_batches(contracts)
        labels=candidate['labels']
        if cohort=='held_out' and (len(coverage)>30 or len(batches)>2 or any(not x['included'] for x in coverage)):
            raise ValueError('SIZE_OR_COVERAGE_LIMIT')
        gt=[{'label_id':id+':'+str(i+1),'swc_id':l['swc_id'],'original_label':l,'targets':targets_for(l,contracts,cat,src)} for i,l in enumerate(labels)]
        if not any(l['targets'] for l in gt):raise ValueError('NO_UNAMBIGUOUS_GT_TARGET')
        # Reject contradictory named-function vs original raw range locations.
        if cohort=='held_out':
            for l in gt:
                raw=l['original_label'].get('raw',{}).get('lineNumber','')
                nums=[int(n) for n in re.findall(r'\d+',raw)]
                if l['targets'] and len(nums)==2 and not set(range(nums[0],nums[1]+1)) & set(l['targets'][0]['location']['lines']):
                    raise ValueError('CONTRADICTORY_GT_LOCATION')
        text=src.read_text();clean=TOKENS.sub(lambda m:'' if m.group().startswith(('//','/*')) else m.group(),sanitize_source(text))
        fingerprint=digest(re.sub(r'\s+','',clean))
        if fingerprint in fingerprints:raise ValueError('DUPLICATE_SOURCE_TOKENS')
        fingerprints.add(fingerprint)
        recovery='experiments/mode-b-v2-identity-fix-2026-11-09/offline_reprocessing.json' if id=='ixo-authoriser' else None
        plan=case_plan(src,model,a.run_output/cohort/id,recovery)
        plan.update(id=id,cohort=cohort,dataset_file=file)
        cases.append(plan); evaluation[id]={'labels':gt}
        structural=d.run_discovery(contracts,cat)
        atomic_json(out/'prepared'/id/'structure.json',structural)
        texts,_=dependency_graph(src,project_root(src))
        for f in cat.fragments.values():
            assert sanitize_source(f['source'])==f['source']
            assert not any(ANNOTATION.search(m.group()) or CATEGORY_LOCATION.search(m.group()) for m in TOKENS.finditer(f['source']) if m.group().startswith(('//','/*')))
        for b in batches:
            wire=json.dumps(d.messages(b));assert 'SWC-' not in wire and 'audit_reports' not in wire and 'ground_truth' not in wire
        atomic_json(out/'prepared'/id/'sanitization.json',{'dependency_sha256':{str(x):file_hash(x) for x in texts},
            'annotation_files_sanitized':sum(Path(x).read_text()!=v for x,v in texts.items()),
            'catalog_fragments_checked':len(cat.fragments),'source_identity':cat.source_identity,
            'source_token_fingerprint':fingerprint,'GT_isolated':True})
        print('READY',cohort,id,len(coverage),flush=True)
    with patch('openai.OpenAI.__init__',side_effect=AssertionError('OFFLINE_ONLY')):
        for c in selected:add(c)
        for row in universe:
            project=Path(row['file']).parts[0]
            if project in projects:continue
            try:
                add({**row,'cohort':'held_out','id':'held-'+str(picked+1).zfill(2)+'-'+Path(row['file']).stem})
                projects.add(project);picked+=1
                screen.append({'file':row['file'],'status':'selected'})
            except Exception as e:
                screen.append({'file':row['file'],'status':'excluded','reason':str(e)[:200]})
            if picked==7:break
    if picked!=7:raise ValueError('INSUFFICIENT_READY_HELD_OUT_CASES')
    atomic_json(out/'evaluation_only/labels.json',evaluation)
    atomic_json(out/'selection_log.json',screen)
    counts={cohort:{k:sum(c['budget'][k] for c in cases if c['cohort']==cohort) for k in ('max_generation_calls','max_count_calls','max_reserved_tokens')} for cohort in ('development','held_out')}
    manifest={'version':1,'purpose':'Mode B v2-only dataset performance evaluation','model':model,
        'configuration':identity(),'output':str(a.run_output.resolve()),'cases':cases,'cohort_budgets':counts,
        'evaluation_path':str((out/'evaluation_only/labels.json').resolve()),'evaluation_sha256':file_hash(out/'evaluation_only/labels.json'),
        'selection_rule':'Three development files fixed; first 7 lexicographic ready files, one per new project; source token dedup; <=30 summary rows and <=2 batches; no ambiguous/contradictory-only GT; stop before inference',
        'approval_policy':'development first; separate explicit held_out approval required; no live calls during preparation'}
    manifest.update(scoring_protocol=SCORING_PROTOCOL, preparation_script_sha256=file_hash(__file__),
        frozen_protocols={'discovery':{**discovery_config(24000),'model':model},'verification':{**configuration(LIMITS),'model':model}})
    atomic_json(out/'manifest.json',manifest)
    print('Manifest SHA256:',digest(manifest));print('SWC distribution',dict(Counter(l['swc_id'] for v in evaluation.values() for l in v['labels'])))


if __name__=='__main__':main()
