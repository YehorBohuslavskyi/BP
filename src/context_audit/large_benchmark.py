"""Offline-only DAppSCAN audit, grouped splits and atomic proposed benchmark preparation."""
import json
import os
import re
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from context_audit.datasets.dappscan import DAppSCAN
from context_audit.direct_preparation import TOKENS,sanitize_source,project_root,dependency_graph,PreparationError
from context_audit.app.compilers import compatible_compilers
from context_audit.v2_artifacts import digest,file_hash,atomic_json,implementation_hash,discovery_config
from context_audit import direct_discovery as discovery,direct_verification as verification
from context_audit.v2_dataset import LIMITS
from context_audit.v2_dataset_scoring import SCORING_PROTOCOL
from solc_select.solc_select import ARTIFACTS_DIR

LEX=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*|0[xX][0-9a-fA-F]+|\d+|[^\s]')


def source_tokens(text):
    clean=TOKENS.sub(lambda m:' ' if m.group().startswith(('//','/*')) else m.group(),sanitize_source(text))
    return tuple(LEX.findall(clean))


def family(project):
    name=unicodedata.normalize('NFKC',project).casefold().split('-',1)[-1]
    name=re.sub(r'\bv\d+(?:\.\d+)*\b',' ',name)
    words=re.findall(r'[^\W\d_]+',name,flags=re.UNICODE)
    return tuple(w for w in words if w not in {'security','audit','report','signed','smart','contract','contracts','token','network'})


class Union:
    def __init__(self,items):self.parent={x:x for x in items}
    def find(self,x):
        while self.parent[x]!=x:
            self.parent[x]=self.parent[self.parent[x]];x=self.parent[x]
        return x
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)


def grouped_splits(rows,history,seed,development_percent=20,validation_percent=20,threshold=.85):
    projects=sorted({r['project'] for r in rows});pu=Union(projects);fu=Union([r['file'] for r in rows]);links=[]
    families={};exact={};shingles={}
    for r in rows:
        f=family(r['project'])
        if f and f in families:pu.join(r['project'],families[f])
        elif f:families[f]=r['project']
        if r['token_sha256'] in exact:
            other=exact[r['token_sha256']];pu.join(r['project'],other['project']);fu.join(r['file'],other['file'])
            links.append({'a':other['file'],'b':r['file'],'reason':'exact_source_tokens','similarity':1.0})
        else:exact[r['token_sha256']]=r
        t=r['_tokens'];shingles[r['file']]={digest(t[i:i+5])[:16] for i in range(max(0,len(t)-4))}
    # Deterministic exact Jaccard, with a safe size-ratio prefilter. No approximate matches are dropped.
    for i,a in enumerate(rows):
        sa=shingles[a['file']]
        if len(sa)<50:continue
        for b in rows[i+1:]:
            sb=shingles[b['file']]
            if len(sb)<50 or a['token_sha256']==b['token_sha256']:continue
            if min(len(sa),len(sb))/max(len(sa),len(sb))<threshold:continue
            common=len(sa & sb);similarity=common/(len(sa)+len(sb)-common)
            if similarity>=threshold:
                pu.join(a['project'],b['project']);fu.join(a['file'],b['file'])
                links.append({'a':a['file'],'b':b['file'],'reason':'near_source_tokens','similarity':round(similarity,6)})
    groups=defaultdict(list)
    for p in projects:groups[pu.find(p)].append(p)
    assignment={};audit=[]
    for members in sorted(groups.values()):
        used=sorted(set(members)&set(history));key=digest(members);bucket=int(digest([seed,key])[:16],16)%100
        split='development' if used or bucket<development_percent else ('validation' if bucket<development_percent+validation_percent else 'held_out')
        for p in members:assignment[p]=split
        audit.append({'group_id':key,'projects':members,'split':split,'historical_projects':used})
    for r in rows:r['split']=assignment[r['project']];r['source_group']=fu.find(r['file'])
    return audit,links


def history_projects(roots,known):
    projects=set();evidence={}
    path_pattern=re.compile(r'(?:^|/)('+ '|'.join(re.escape(p) for p in sorted(known))+r')(?=/)') if known else None
    for root in roots:
        for path in sorted(Path(root).rglob('*.json')):
            if ('evaluation_only' in path.parts or any(word in path.name for word in ('screen','universe','selection_log','records','source_evidence','sanitization','history_provenance','split_groups','blockers','audit','inventory','cleanup'))):
                continue
            data=json.loads(path.read_text())
            if isinstance(data,dict) and data.get('approval_required') is True and data.get('purpose')=='Large Mode B v2 preparation proposal only; no live execution authorization':
                continue
            found=set()
            def walk(x):
                if isinstance(x,dict):
                    for v in x.values():walk(v)
                elif isinstance(x,list):
                    for v in x:walk(v)
                elif isinstance(x,str):
                    normalized=x.replace('\\','/')
                    if x in known:found.add(x)
                    if path_pattern:found.update(m.group(1) for m in path_pattern.finditer(normalized))
            walk(data)
            if found:projects.update(found);evidence[str(path)]={'sha256':file_hash(path),'projects':sorted(found)}
    return projects,evidence


def inventory(dataset):
    candidates=set();report_hashes={}
    for name in ('SWCsource','SWC_source','SWC-source'):
        directory=dataset.base/name
        for report in sorted(directory.rglob('*.json')):
            report_hashes[report.relative_to(dataset.base).as_posix()]=file_hash(report)
            file=report.relative_to(directory).with_suffix('.sol').as_posix()
            if (dataset.contracts/file).is_file():candidates.add(file)
            else:
                # Use the existing loader's non-mirrored report support, not a second label parser.
                project=report.relative_to(directory).parts[0].removesuffix('.json')
                if project in dataset.projects():candidates.update(dataset.files(project))
    rows=[]
    for file in sorted(candidates):
        labels=dataset.labels(file)
        if not labels:continue
        source=dataset.source_path(file);raw=source.read_bytes();tokens=source_tokens(raw.decode())
        rows.append({'file':file,'project':Path(file).parts[0],'source_sha256':file_hash(source),
            'source_bytes':len(raw),'token_sha256':digest(tokens),'_tokens':tokens,'labels':labels})
    return rows,report_hashes


def resolve_gt(labels,contracts,catalog,source):
    helper=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/prepare_v2_dataset.py'))['targets_for']
    result=[]
    for label in labels:
        targets=helper(label,contracts,catalog,source)
        alternatives=[]
        for contract in contracts:
            for function in contract['functions']:
                alternatives.extend(helper(label,[{**contract,'functions':[function]}],catalog,source))
        status='RESOLVED' if targets else ('AMBIGUOUS' if len(alternatives)>1 else 'UNRESOLVED')
        name_only={**label,'lines':[]}
        named=helper(name_only,contracts,catalog,source) if label.get('function') else []
        raw=str(label.get('raw',{}).get('lineNumber',''))
        interval=re.fullmatch(r'\s*L?(\d+)\s*-\s*L?(\d+)\s*',raw)
        loc_lines=label.get('lines',[]) or (list(range(int(interval[1]),int(interval[2])+1)) if interval and int(interval[2])-int(interval[1])<100000 else [])
        if named and loc_lines and not set(loc_lines)&set(named[0]['location']['lines']):
            status='CONTRADICTORY';targets=[]
        result.append({'label':label,'status':status,'targets':targets,'candidate_target_count':len(alternatives)})
    return result


def worker(source,result_path,max_functions,max_summary_functions,max_batches,expected_compiler):
    from unittest.mock import patch
    with patch('openai.OpenAI.__init__',side_effect=AssertionError('OFFLINE_ONLY')),patch('socket.socket.connect',side_effect=AssertionError('NETWORK_DISABLED')):
        contracts,catalog=discovery.prepare(Path(source))
        if catalog.preparation_metadata['compiler_used']!=expected_compiler:raise ValueError('PINNED_COMPILER_CHANGED')
        result=discovery.run_discovery(contracts,catalog)
        status='READY'
        if catalog.preparation_metadata['total_source_functions']==0 or catalog.preparation_metadata['preparation_status']=='NO_ANALYZABLE_FUNCTIONS':status='UNEVALUABLE'
        elif catalog.preparation_metadata['total_source_functions']>max_functions or len(result['coverage'])>max_summary_functions:status='FUNCTION_LIMIT'
        elif len(result['batches'])>max_batches:status='SUMMARY_LIMIT'
        elif not result['coverage'] or any(not r['included'] for r in result['coverage']):status='UNEVALUABLE'
        for fragment in catalog.fragments.values():verification.safe_fragment(fragment)
        for batch in result['batches']:
            wire=json.dumps(discovery.messages(batch))
            if 'SWC-' in wire or 'audit_reports' in wire or 'ground_truth' in wire:raise ValueError('GT_TRANSPORT_LEAK')
        locations=catalog.fragment_locations
        for fid,fragment in catalog.fragments.items():
            if fid not in locations:raise ValueError('MISSING_SOURCE_LOCATION')
            file=Path(source).resolve()
            staged_file=project_root(file)/locations[fid]['file']
            sanitized=sanitize_source(staged_file.read_text()).encode()
            loc=locations[fid]
            if sanitized[loc['start']:loc['start']+loc['length']].decode()!=fragment['source']:
                raise ValueError('SOURCE_SPAN_MISMATCH')
        atomic_json(result_path,{'status':status,'structural':result,'source_identity':catalog.source_identity,
            'metadata':catalog.preparation_metadata,'contracts':contracts,
            'fragment_metadata':{fid:{'kind':f['kind'],'name':f['name'],'source_sha256':digest(f['source']),'location':locations[fid]} for fid,f in catalog.fragments.items()}})


def restore_preparation(cache, dataset, row, target, compiler, options):
    """Revalidate unpublished compiler-backed cache, never infer missing provenance."""
    original=Path(cache)/'prepared'/digest(row['file'])[:20]
    if not (original/'structure.json').is_file() or not (original/'provenance.json').is_file():return None
    structural=json.loads((original/'structure.json').read_text())
    provenance=json.loads((original/'provenance.json').read_text())
    identity=provenance['source_identity'];source=dataset.source_path(row['file'])
    texts,_=dependency_graph(source,project_root(source))
    expected_preparation=implementation_hash(['direct_preparation','direct','context','catalog','function_index'])
    if (identity['source_sha256']!=file_hash(source) or identity['compiler']!=compiler or
        provenance['metadata']['compiler_used']!=compiler or identity['preparation_sha256']!=expected_preparation or
        identity.get('function_index_sha256')!=digest(structural.get('function_index')) or
        identity['sanitizer_sha256']!=implementation_hash(['direct_preparation']) or
        structural['manifest']['configuration']['implementation_sha256']!=implementation_hash(['direct_discovery','function_index']) or
        structural['manifest']['executed'] or structural['usage']['api_calls']!=0 or
        structural['manifest']['source']!=identity or identity['structure_sha256']!=digest(structural['contracts']) or
        structural['manifest']['artifact_sha256']!=digest({k:v for k,v in structural.items() if k!='manifest'}) or
        identity['sanitized_project_sha256']!=digest({p.relative_to(project_root(source)).as_posix():
            __import__('hashlib').sha256(text.encode()).hexdigest() for p,text in sorted(texts.items())})):
        raise RuntimeError('PREPARATION_CACHE_PROVENANCE_MISMATCH')
    fragments={};locations={}
    for fid,metadata in provenance['fragment_metadata'].items():
        loc=metadata['location'];p=project_root(source)/loc['file']
        if p.resolve() not in texts:raise RuntimeError('CACHE_FRAGMENT_OUTSIDE_DEPENDENCY_GRAPH')
        content=texts[p.resolve()].encode()[loc['start']:loc['start']+loc['length']].decode()
        if digest(content)!=metadata['source_sha256']:raise RuntimeError('CACHE_SOURCE_SPAN_MISMATCH')
        fragments[fid]={'id':fid,'kind':metadata['kind'],'name':metadata['name'],'file':loc['file'],'source':content}
        verification.safe_fragment(fragments[fid]);locations[fid]=loc
    if digest(fragments)!=identity['catalog_sha256'] or digest(locations)!=identity['locations_sha256']:
        raise RuntimeError('CACHE_CATALOG_MISMATCH')
    status='READY'
    if provenance['metadata']['total_source_functions']==0 or provenance['metadata']['preparation_status']=='NO_ANALYZABLE_FUNCTIONS':status='UNEVALUABLE'
    elif provenance['metadata']['total_source_functions']>options['max_functions'] or len(structural['coverage'])>options['max_summary_functions']:status='FUNCTION_LIMIT'
    elif len(structural['batches'])>options['max_batches']:status='SUMMARY_LIMIT'
    elif not structural['coverage'] or any(not r['included'] for r in structural['coverage']):status='UNEVALUABLE'
    data={**provenance,'status':status,'structural':structural,'contracts':structural['contracts']}
    original_binary=None
    registry=Path(cache)/'evaluation_only/records.json'
    if registry.is_file():
        entry=next((r for r in json.loads(registry.read_text()) if r['file']==row['file']),None)
        if entry:
            original_binary=entry.get('cache_provenance',{}).get('original_compiler_binary_sha256') if entry.get('cache_provenance') else entry.get('compiler_binary_sha256')
    return data,{'structure_sha256':file_hash(original/'structure.json'),'provenance_sha256':file_hash(original/'provenance.json'),
        'validated':True,'original_compiler_binary_sha256':original_binary,
        'note':'Exact compiler version is validated. Original binary hash is retained when present in cache records; otherwise it remains unknown. Current binary hash is recorded separately.'}


def prepare_one(dataset,row,stage,options):
    source=dataset.source_path(row['file']);base={'source_sha256':row['source_sha256'],'sanitizer_sha256':implementation_hash(['direct_preparation'])}
    if row['source_bytes']>options['max_source_bytes']:return {**base,'status':'SOURCE_SIZE_LIMIT'}
    try:
        texts,_=dependency_graph(source,project_root(source))
        base['dependency_sha256']={str(p):file_hash(p) for p in sorted(texts)}
        versions=compatible_compilers('\n'.join(texts.values()))
        if not versions:return {**base,'status':'COMPILER_VERSION_UNAVAILABLE','blocker':'No installed compiler satisfies all source/dependency pragmas'}
        compiler=versions[0];binary=Path(ARTIFACTS_DIR)/('solc-'+compiler)/('solc-'+compiler)
        if not binary.is_file():return {**base,'status':'COMPILER_VERSION_UNAVAILABLE','blocker':'Installed compiler binary missing'}
        base.update(compiler=compiler,compiler_binary_sha256=file_hash(binary))
        target=stage/'prepared'/digest(row['file'])[:20];target.mkdir(parents=True)
        response=target/'worker.json'
        cached=restore_preparation(options['resume_preparation_from'],dataset,row,target,compiler,options) if options.get('resume_preparation_from') else None
        if cached:
            data,cache_provenance=cached
            base['cache_provenance']=cache_provenance
        else:
            data=None
        command=[sys.executable,str(Path(__file__).resolve().parents[2]/'scripts/prepare_large_v2_benchmark.py'),'_worker',
            '--source',str(source),'--result',str(response),'--max-functions',str(options['max_functions']),
            '--max-summary-functions',str(options['max_summary_functions']),'--max-batches',str(options['max_batches']),
            '--compiler',compiler]
        env={k:v for k,v in os.environ.items() if k not in ('OPENAI_API_KEY','OPENAI_ORG_ID','OPENAI_PROJECT_ID')}
        if data is None:
            proc=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
            try:
                stdout,stderr=proc.communicate(timeout=options['timeout_seconds'])
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
                raise
            if proc.returncode:
                shutil.rmtree(target)
                return {**base,'status':'COMPILATION_FAILED','blocker':'Compiler-backed worker failed; no alternate compiler attempted',
                    'diagnostic':re.sub(r'/tmp/direct-sanitized-[^/\s]+','<sanitized-stage>',stderr[-1600:])}
            data=json.loads(response.read_text());response.unlink()
        if data['metadata']['compiler_used']!=compiler or file_hash(binary)!=base['compiler_binary_sha256']:raise RuntimeError('COMPILER_PIN_MISMATCH')
        if {str(p):file_hash(p) for p in texts}!=base['dependency_sha256']:raise RuntimeError('SOURCE_CHANGED_DURING_PREPARATION')
        gt=resolve_gt(row['labels'],data['contracts'],type('Catalog',(),{'fragment_locations':{fid:f['location'] for fid,f in data['fragment_metadata'].items()}})(),source)
        base.update(status=data['status'],metadata=data['metadata'],source_identity=data['source_identity'],gt_resolution=gt,
            summary_rows=len(data['structural']['coverage']),batches=len(data['structural']['batches']))
        atomic_json(target/'structure.json',data['structural'])
        atomic_json(target/'provenance.json',{k:v for k,v in data.items() if k not in ('structural','contracts')})
        base['prepared_artifact']=target.relative_to(stage).as_posix()
        return base
    except PreparationError as exc:return {**base,'status':exc.metadata['preparation_status'],'blocker':str(exc)}
    except subprocess.TimeoutExpired:
        if 'target' in locals():shutil.rmtree(target,ignore_errors=True)
        return {**base,'status':'PREPARATION_TIMEOUT','blocker':'Worker deadline exceeded; no retry'}


def publish(dataset_root,output,options,history_roots):
    output=Path(output).resolve()
    if output.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    dataset=DAppSCAN(dataset_root);rows,report_hashes=inventory(dataset)
    print(f'Inventory: {len(rows)} labelled source files; scanning prior experiment references',flush=True)
    history,evidence=history_projects(history_roots,set(dataset.projects()))
    print(f'Historical project references: {len(history)}; grouping duplicate/variant projects',flush=True)
    groups,links=grouped_splits(rows,history,options['seed'],options['development_percent'],options['validation_percent'],options['near_duplicate_threshold'])
    if options['development_percent']+options['validation_percent']>100:raise ValueError('INVALID_SPLIT_PERCENTAGES')
    with tempfile.TemporaryDirectory(prefix='.large-benchmark-staging-',dir=output.parent) as temp:
        stage=Path(temp);records=[];cases=[];used_source=set();per_project=Counter()
        for number,row in enumerate(rows,1):
            outcome=prepare_one(dataset,row,stage,options)
            record={k:v for k,v in row.items() if k!='_tokens'};record.update(outcome)
            selected=outcome['status']=='READY' and any(g['status']=='RESOLVED' for g in outcome['gt_resolution'])
            if outcome['status']=='READY':
                if not selected:record['selection_exclusion']='NO_RESOLVABLE_GT'
                elif row['source_group'] in used_source:selected=False;record['selection_exclusion']='DUPLICATE_OR_NEAR_DUPLICATE_SOURCE'
                elif per_project[row['project']]>=options['max_per_project']:selected=False;record['selection_exclusion']='PROJECT_CASE_LIMIT'
            if selected:
                used_source.add(row['source_group']);per_project[row['project']]+=1
                count=outcome['batches']+LIMITS.max_candidates*LIMITS.max_rounds
                cases.append({'id':'case-'+digest(row['file'])[:20],'project':row['project'],'split':row['split'],'source':str(dataset.source_path(row['file'])),
                    'dataset_file':row['file'],'source_identity':outcome['source_identity'],'prepared_artifact':outcome['prepared_artifact'],
                    'limits':LIMITS.model_dump(),'budget':{'max_discovery_calls':outcome['batches'],'max_generation_calls':count,
                        'max_count_calls':count,'max_reserved_tokens':LIMITS.max_total_tokens,'max_input_tokens_per_call':LIMITS.max_input_tokens}})
            record['selected']=selected;records.append(record)
            if number%25==0:print(f'Audited {number}/{len(rows)}; prepared {sum(r["status"]=="READY" for r in records)}; proposed {len(cases)}',flush=True)
        # Invariants enforced before any final directory is published.
        for group in groups:
            splits={c['split'] for c in cases if c['project'] in group['projects']}
            if len(splits)>1:raise RuntimeError('GROUP_SPLIT_LEAKAGE')
            if group['historical_projects'] and splits-{'development'}:raise RuntimeError('HISTORICAL_PROJECT_LEAKAGE')
        if len({next(r['source_group'] for r in records if r['file']==c['dataset_file']) for c in cases})!=len(cases):raise RuntimeError('SOURCE_DUPLICATION')
        for r in records:
            if file_hash(dataset.source_path(r['file']))!=r['source_sha256']:raise RuntimeError('SOURCE_INVENTORY_CHANGED')
        counts=Counter(r['status'] for r in records);swcs=Counter(l['swc_id'] for r in rows for l in r['labels'])
        gt_counts=Counter(g['status'] for r in records for g in r.get('gt_resolution',[]))
        budgets={s:{k:sum(c['budget'][k] for c in cases if c['split']==s) for k in ('max_generation_calls','max_count_calls','max_reserved_tokens')} for s in ('development','validation','held_out')}
        audit={'unit':'labelled Solidity source file; one file may define several contracts','total_labelled_files':len(rows),
            'unique_source_projects':len({r['project'] for r in rows}),'SWC_label_distribution':dict(swcs),
            'status_counts':dict(counts),'successful_compiler_preparations':sum(r['status'] in ('READY','FUNCTION_LIMIT','SUMMARY_LIMIT','UNEVALUABLE') for r in records),
            'ready_within_limits':counts['READY'],'GT_resolution_counts_among_compiled_files':dict(gt_counts),
            'GT_labels_not_compiler_resolved':sum(len(r['labels']) for r in records if 'gt_resolution' not in r),
            'proposed_cases':len(cases),'proposed_resolvable_GT_labels':sum(sum(g['status']=='RESOLVED' for g in r.get('gt_resolution',[])) for r in records if r['selected']),
            'proposed_splits':dict(Counter(c['split'] for c in cases)),'historical_projects':len(history),
            'source_duplicate_links':len(links),'project_groups':len(groups),'cohort_budget_caps':budgets,
            'total_budget_caps':{k:sum(b[k] for b in budgets.values()) for k in ('max_generation_calls','max_count_calls','max_reserved_tokens')},
            'api_calls':0,'note':'GT ambiguity counts cover compiler-prepared files only; unprepared labels remain explicitly unresolved.'}
        model='gpt-5.4-mini-2026-03-17'
        manifest={'version':1,'purpose':'Large Mode B v2 preparation proposal only; no live execution authorization',
            'dataset_root':str(dataset.root),'dataset_report_sha256':report_hashes,'options':options,'model':model,
            'protocols':{'discovery':{**discovery_config(24000),'model':model},'verification':{**verification.configuration(LIMITS),'model':model}},
            'scoring_protocol':SCORING_PROTOCOL,'sanitizer_sha256':implementation_hash(['direct_preparation']),
            'installed_compilers':{p.parent.name.removeprefix('solc-'):file_hash(p) for p in sorted(Path(ARTIFACTS_DIR).glob('solc-*/solc-*')) if p.is_file()},
            'preparation_sha256':implementation_hash(['large_benchmark','direct','direct_preparation','direct_discovery','catalog','context','function_index']),
            'cache_policy':'Unpublished cache requires complete source/catalog/indexer revalidation; original missing binary hashes remain unknown',
            'entrypoint_sha256':file_hash(Path(__file__).resolve().parents[2]/'scripts/prepare_large_v2_benchmark.py'),
            'inventory_sha256':digest([{k:v for k,v in r.items() if k!='_tokens'} for r in rows]),
            'cases':cases,'budget_caps':budgets,'approval_required':True,
            'compiler_policy':'Pinned to existing deterministic installed-compatible selection before compilation; no installation, substitution or fallback retry.'}
        atomic_json(stage/'manifest.json',manifest);atomic_json(stage/'audit.json',audit)
        atomic_json(stage/'evaluation_only/records.json',records)
        atomic_json(stage/'split_groups.json',{'groups':groups,'source_similarity_links':links})
        atomic_json(stage/'history_provenance.json',evidence)
        atomic_json(stage/'blockers.json',[{'file':r['file'],'status':r['status'],'blocker':r.get('blocker'),'diagnostic':r.get('diagnostic')} for r in records if r['status'] not in ('READY','SOURCE_SIZE_LIMIT','FUNCTION_LIMIT','SUMMARY_LIMIT','UNEVALUABLE')])
        (stage/'audit.md').write_text('# Mode B v2 large benchmark preparation v1\n\nOffline proposal only. No inference executed.\n\n```json\n'+json.dumps(audit,indent=2)+'\n```\n\nManifest SHA256: `'+digest(manifest)+'`\n\nDetailed exclusions and GT resolution are in evaluation_only/records.json; blockers.json lists dependency/compiler/runtime blockers.\n')
        if output.exists():raise ValueError('OUTPUT_APPEARED_DURING_PREPARATION')
        os.rename(stage,output)
    return audit
