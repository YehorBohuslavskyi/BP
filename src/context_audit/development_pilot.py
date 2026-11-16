"""Development-only deterministic pilot export; no outcome-based selection or new detector."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from context_audit import direct_discovery as d,direct_verification as v
from context_audit.direct_preparation import dependency_graph,project_root,sanitize_source
from context_audit.v2_artifacts import digest,file_hash,atomic_json,implementation_hash
from context_audit.v2_dataset import LIMITS,identity as dataset_identity,execute_cohort
from context_audit.v2_dataset_scoring import SCORING_PROTOCOL
from solc_select.solc_select import ARTIFACTS_DIR

RULE={'cases':7,'development_only':True,'preparation_status':'READY','max_declared_functions':16,
      'max_summary_rows':25,'max_batches':2,'all_GT_resolved':True,'one_case_per_project':True,
      'rank':['most previously uncovered resolvable SWC categories','fewest declared functions',
              'fewest summary rows','lexicographic dataset path'],'uses_model_verdicts':False}


def select_cases(parent,records,count=7):
    by={r['file']:r for r in records};candidates=[]
    for c in parent['cases']:
        r=by[c['dataset_file']]
        if (c['split']=='development' and r['metadata']['preparation_status']=='READY' and
            0<r['metadata']['total_source_functions']<=16 and r['summary_rows']<=25 and r['batches']<=2 and
            r['gt_resolution'] and all(g['status']=='RESOLVED' for g in r['gt_resolution'])):
            candidates.append(c)
    chosen=[];projects=set();categories=set();trace=[]
    while len(chosen)<count:
        options=[c for c in candidates if c['project'] not in projects]
        if not options:raise ValueError('INSUFFICIENT_ELIGIBLE_DEVELOPMENT_CASES')
        def types(c):return {g['label']['swc_id'] for g in by[c['dataset_file']]['gt_resolution']}
        c=min(options,key=lambda c:(-len(types(c)-categories),by[c['dataset_file']]['metadata']['total_source_functions'],
                                   by[c['dataset_file']]['summary_rows'],c['dataset_file']))
        trace.append({'case_id':c['id'],'new_SWCs':sorted(types(c)-categories),'all_SWCs':sorted(types(c))})
        chosen.append(c);projects.add(c['project']);categories|=types(c)
    return chosen,trace


def validate_parent(path):
    path=Path(path).resolve();root=path.parent;parent=json.loads(path.read_text())
    bundle=json.loads((root/'bundle_provenance.json').read_text())
    if bundle['manifest_sha256']!=digest(parent):raise ValueError('PARENT_BUNDLE_MANIFEST_MISMATCH')
    for relative,expected in bundle['files_sha256'].items():
        p=(root/relative).resolve()
        if not p.is_relative_to(root) or file_hash(p)!=expected:raise ValueError('PARENT_BUNDLE_CHANGED')
    if parent['scoring_protocol']!=SCORING_PROTOCOL:raise ValueError('SCORING_RULE_MISMATCH')
    if parent['protocols']['discovery']['prompt_sha256']!=digest(d.SYSTEM_PROMPT) or parent['protocols']['verification']['prompt_sha256']!=digest(v.SYSTEM_PROMPT):
        raise ValueError('PARENT_PROMPTS_CHANGED')
    return parent,json.loads((root/'evaluation_only/records.json').read_text())


def audit_reuse(selected,exclude_output=None):
    """Audit identity/stage completion only. Security verdicts never influence selection."""
    rows=[]
    for report_path in sorted(Path('runs').rglob('report.json')):
        if exclude_output and report_path.resolve().is_relative_to(Path(exclude_output).resolve()):continue
        report=json.loads(report_path.read_text())
        if report.get('mode')!='direct_detection_v2':continue
        root=report_path.parent.parent if report_path.parent.name=='analysis' else report_path.parent
        source=None;model=None;source_identity={}
        for name in ('run_manifest.json','experiment_manifest.json','smoke_manifest.json','continuation_manifest.json'):
            meta=root/name
            if not meta.exists():continue
            plan=json.loads(meta.read_text())['plan'];case=plan.get('case',plan)
            if 'source' not in case and plan.get('parent_manifest'):
                old=json.loads(Path(plan['parent_manifest']).read_text())
                case=next(c for c in old['cases'] if c['id']==plan['case_id'])
            source=case.get('source');model=case.get('model',plan.get('model'));source_identity=case.get('source_identity',{})
            break
        matched=[c['id'] for c in selected if source and Path(source).resolve()==Path(c['source']).resolve()]
        rows.append({'report':str(report_path.resolve()),'report_sha256':file_hash(report_path),'source':source,
          'source_identity':source_identity,'model':model,'matched_selected_cases':matched,
          'completed_sessions':sum(i['result']['status']=='completed' for i in report.get('issues',[])),
          'processing_failures':report.get('coverage_counts',{}).get('processing_failures',0),
          'reuse_decision':'NOT_SELECTED_SOURCE_NO_REUSE' if not matched else 'EXPLICIT_SELECTED_RESULT_IMPORT_REQUIRED'})
    return rows


def identity():
    return {'pilot':implementation_hash(['development_pilot']),
            'entrypoint':file_hash(Path(__file__).resolve().parents[2]/'scripts/run_development_pilot.py'),
            'dataset_runner':dataset_identity()}


def prepare(parent_path,output,run_output):
    parent_path=Path(parent_path).resolve();output=Path(output).resolve();run_output=Path(run_output).resolve()
    if output.exists() or run_output.exists():raise ValueError('NEW_OUTPUT_DIRECTORIES_REQUIRED')
    parent,records=validate_parent(parent_path);selected,trace=select_cases(parent,records)
    reuse=audit_reuse(selected,run_output)
    if any(r['matched_selected_cases'] for r in reuse):raise ValueError('SELECTED_SOURCE_HAS_PRIOR_INFERENCE_REQUIRES_EXPLICIT_REUSE_IMPORT')
    by={r['file']:r for r in records};cases=[];preflights=[];evaluation={}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.pilot-prepare-',dir=output.parent) as tmp:
        stage=Path(tmp)
        with patch('openai.OpenAI.__init__',side_effect=AssertionError('OFFLINE_ONLY')):
            for c in selected:
                old=by[c['dataset_file']];source=Path(c['source'])
                binary=Path(ARTIFACTS_DIR)/('solc-'+old['compiler'])/('solc-'+old['compiler'])
                binary_hash=file_hash(binary)
                if binary_hash!=old['compiler_binary_sha256']:raise ValueError('COMPILER_BINARY_CHANGED')
                version=subprocess.run([str(binary),'--version'],capture_output=True,text=True,timeout=10,check=True).stdout.strip()
                if old['compiler'] not in version:raise ValueError('COMPILER_VERSION_MISMATCH')
                contracts,catalog=d.prepare(source)
                if catalog.source_identity!=c['source_identity'] or file_hash(binary)!=binary_hash:raise ValueError('FRESH_PREPARATION_MISMATCH')
                texts,_=dependency_graph(source,project_root(source))
                if {str(p):file_hash(p) for p in texts}!=old['dependency_sha256']:raise ValueError('DEPENDENCY_HASH_MISMATCH')
                for fragment in catalog.fragments.values():v.safe_fragment(fragment)
                batches,coverage=d.make_batches(contracts)
                if any(not r['included'] or r['incomplete_metadata'] for r in coverage):raise ValueError('PILOT_METADATA_INCOMPLETE')
                for b in batches:
                    wire=json.dumps(d.messages(b))
                    if any(marker in wire for marker in ('SWC-','audit_reports','ground_truth')):raise ValueError('GT_TRANSPORT_LEAK')
                if c['limits']!=LIMITS.model_dump() or c['budget']['max_generation_calls']!=len(batches)+9:raise ValueError('FROZEN_BUDGET_MISMATCH')
                case={**c,'cohort':'development','model':parent['model'],'output':str(run_output/c['id']),
                    'recovery_path':None,'recovery_sha256':None,'import_sha256':None,'coverage':coverage,'preparation':catalog.preparation_metadata}
                cases.append(case)
                structural=d.run_discovery(contracts,catalog)
                atomic_json(stage/'prepared'/c['id']/'structure.json',structural)
                proof={'case_id':c['id'],'compiler_binary':str(binary),'compiler_binary_sha256':binary_hash,
                    'compiler_version_output':version,'source_identity':catalog.source_identity,
                    'dependency_sha256':old['dependency_sha256'],'declared_functions':old['metadata']['total_source_functions'],
                    'summary_rows':len(coverage),'batches':len(batches),'all_full_index':True,'fresh_compilation':True,
                    'catalog_fragments_checked':len(catalog.fragments),'API_calls':0,
                    'summary_prompt_estimated_tokens':sum(len(json.dumps(d.messages(b)))//4+1 for b in batches)}
                preflights.append(proof);atomic_json(stage/'prepared'/c['id']/'preflight.json',proof)
                evaluation[c['id']]={'file':c['dataset_file'],'labels':[{'label_id':c['id']+':'+str(i+1),
                    'swc_id':g['label']['swc_id'],'original_label':g['label'],'targets':g['targets']} for i,g in enumerate(old['gt_resolution'])]}
        caps={k:sum(c['budget'][k] for c in cases) for k in ('max_generation_calls','max_count_calls','max_reserved_tokens')}
        execution={'version':1,'configuration':dataset_identity(),'model':parent['model'],'output':str(run_output),
                   'cases':cases,'cohort_budgets':{'development':caps}}
        plan={'version':1,'scope':'seven selected development sources only','parent_manifest':str(parent_path),
            'parent_manifest_sha256':file_hash(parent_path),'parent_bundle_sha256':file_hash(parent_path.parent/'bundle_provenance.json'),
            'selection_rule':RULE,'selection_trace':trace,'configuration':identity(),'execution':execution,
            'scoring_protocol':SCORING_PROTOCOL,'preflights':preflights,'reuse_audit':reuse,
            'prior_inference_reuse':'No selected source has a completed matching inference. No stage or verdict is imported.'}
        atomic_json(stage/'plan.json',plan);atomic_json(stage/'reuse_audit.json',reuse)
        atomic_json(stage/'evaluation_only/labels.json',evaluation)
        if output.exists():raise ValueError('OUTPUT_APPEARED')
        os.rename(stage,output)
    return plan


def execute(plan,*,resume=False,acknowledge_partial=(),client_factory=None):
    if plan['configuration']!=identity():raise ValueError('PILOT_IMPLEMENTATION_CHANGED')
    if file_hash(plan['parent_manifest'])!=plan['parent_manifest_sha256'] or file_hash(Path(plan['parent_manifest']).parent/'bundle_provenance.json')!=plan['parent_bundle_sha256']:
        raise ValueError('PARENT_CHANGED')
    parent,records=validate_parent(plan['parent_manifest']);selected,trace=select_cases(parent,records)
    if trace!=plan['selection_trace'] or [c['id'] for c in selected]!=[c['id'] for c in plan['execution']['cases']]:raise ValueError('PILOT_SELECTION_CHANGED')
    if plan['execution']['model']!=parent['model'] or any(c['model']!=parent['model'] for c in plan['execution']['cases']):raise ValueError('FROZEN_MODEL_CHANGED')
    if any(c['split']!='development' or c['cohort']!='development' for c in plan['execution']['cases']):raise ValueError('NON_DEVELOPMENT_CASE_FORBIDDEN')
    for original,current in zip(selected,plan['execution']['cases']):
        if any(current[k]!=original[k] for k in ('source','source_identity','limits','budget','dataset_file','project','split')):
            raise ValueError('FROZEN_CASE_OR_BUDGET_CHANGED')
        if current['output']!=str(Path(plan['execution']['output'])/current['id']):raise ValueError('PILOT_OUTPUT_SCOPE_CHANGED')
    if audit_reuse(selected,plan['execution']['output'])!=plan['reuse_audit']:raise ValueError('REUSE_STATE_CHANGED_REVIEW_REQUIRED')
    for proof in plan['preflights']:
        if file_hash(proof['compiler_binary'])!=proof['compiler_binary_sha256']:raise ValueError('COMPILER_BINARY_CHANGED')
    return execute_cohort(plan['execution'],'development',resume=resume,acknowledge_partial=acknowledge_partial,client_factory=client_factory)
