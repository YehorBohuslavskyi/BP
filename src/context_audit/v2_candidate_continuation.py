"""Explicit retry of failed candidates; retain completed historical verdicts separately."""
import json
import os
from pathlib import Path
from openai import OpenAI
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.discovery_recovery import build_import
from context_audit.development_experiment import JournalTransport
from context_audit.v2_dataset import identity as dataset_identity, validate_finalized
from context_audit.v2_pipeline import groups_for, aggregate, markdown
from context_audit.v2_artifacts import atomic_json, digest, file_hash, implementation_hash


def identity():
    return {**dataset_identity(), 'continuation':implementation_hash(['v2_candidate_continuation']),
        'continuation_cli':file_hash(Path(__file__).resolve().parents[2]/'scripts/run_v2_candidate_continuation.py')}


def load_parent(path, case_id):
    manifest=json.loads(Path(path).read_text())
    case=next(c for c in manifest['cases'] if c['id']==case_id)
    root=Path(case['output']);validate_finalized(case,manifest['configuration'])
    contracts,catalog=d.prepare(Path(case['source']))
    if catalog.source_identity!=case['source_identity']:raise ValueError('PARENT_SOURCE_MISMATCH')
    if not case['recovery_path'] or file_hash(case['recovery_path'])!=case['recovery_sha256']:
        raise ValueError('PARENT_RECOVERY_MISMATCH')
    imported=build_import(case['recovery_path'],contracts,catalog,case['model'])
    if digest(imported)!=case['import_sha256']:raise ValueError('PARENT_IMPORT_MISMATCH')
    report=json.loads((root/'analysis/report.json').read_text())
    ledger=json.loads((root/'budget_ledger.json').read_text())
    verification_manifest=json.loads((root/'analysis/verification_manifest.json').read_text())
    if verification_manifest['configuration']['model']!=case['model']:raise ValueError('PARENT_VERIFICATION_MODEL_MISMATCH')
    if ledger['stopped'] or any(e.get('status')!='returned' for e in ledger['events']):
        raise ValueError('UNCERTAIN_PARENT_TRANSPORT_NO_REPLAY')
    groups=groups_for(imported['candidates'])
    if {i['issue_id'] for i in report['issues']}!={g['issue_id'] for g in groups}:raise ValueError('PARENT_ISSUE_MISMATCH')
    for group in groups:
        issue=next(i for i in report['issues'] if i['issue_id']==group['issue_id'])
        result=issue['result'];v.validate_saved_result(result,contracts,catalog,historical=True)
        if result['status']=='completed' and not v.replay_consistency(result,contracts,catalog)['consistency_validation']['passed']:
            raise ValueError('PARENT_SEMANTIC_CONSISTENCY_FAILED')
        if result['candidate']!=group['candidate']:raise ValueError('PARENT_CANDIDATE_MISMATCH')
        saved=json.loads((root/'analysis'/issue['session_artifact']).read_text())
        if (saved['result']!=result or saved['result_sha256']!=digest(result) or
            saved['manifest_sha256']!=digest(verification_manifest)):
            raise ValueError('PARENT_SESSION_MISMATCH')
        for attempt in result['rounds']:
            p=json.loads(attempt['messages'][1]['content'])
            if p['target']!=v.safe_fragment(catalog.get(group['candidate']['primary_fragment_id'])):
                raise ValueError('PARENT_TARGET_SOURCE_MISMATCH')
            if digest(attempt['messages'][0]['content'])!=verification_manifest['configuration']['prompt_sha256']:
                raise ValueError('PARENT_PROMPT_MISMATCH')
            for fragment in p['provided_context']:
                if fragment!=v.safe_fragment(catalog.get(fragment['id'])):raise ValueError('PARENT_CONTEXT_SOURCE_MISMATCH')
    return case,contracts,catalog,imported,report,ledger


def prepare(path,case_id,output):
    case,contracts,catalog,imported,report,ledger=load_parent(path,case_id)
    if Path(output).exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    retry=[i['result']['candidate_id'] for i in report['issues'] if i['result']['status']=='processing_failed' and
           any(e['code']=='UNSEEN_EVIDENCE_ID' for e in i['result']['errors'])]
    retained=[i['result']['candidate_id'] for i in report['issues'] if i['result']['status']=='completed']
    if len(retry)!=2 or len(retained)!=1:raise ValueError('EXPECTED_TWO_FAILED_AND_ONE_COMPLETED_CANDIDATES')
    budget={**case['budget'],'max_discovery_calls':0,
        'max_generation_calls':min(6,case['budget']['max_generation_calls']-ledger['generation_calls']),
        'max_count_calls':min(6,case['budget']['max_count_calls']-ledger['count_calls']),
        'max_reserved_tokens':min(40000,case['budget']['max_reserved_tokens']-ledger['reserved_tokens'])}
    if min(budget['max_generation_calls'],budget['max_count_calls'],budget['max_reserved_tokens'])<=0:
        raise ValueError('NO_REMAINING_PARENT_BUDGET')
    return {'version':1,'purpose':'Explicit candidate continuation after evidence protocol failures',
        'parent_manifest':str(Path(path).resolve()),'parent_manifest_sha256':file_hash(path),'case_id':case_id,
        'parent_report_sha256':digest(report),'parent_ledger_sha256':digest(ledger),
        'import_sha256':digest(imported),'source_identity':catalog.source_identity,'model':case['model'],
        'configuration':identity(),'retry_candidate_ids':retry,'retained_candidate_ids':retained,
        'output':str(Path(output).resolve()),'budget':budget,
        'limits':{**case['limits'],'max_total_tokens':budget['max_reserved_tokens']},
        'context_policy':'Primary source initially; additional source only after request_context. No automatic preload.',
        'prompt_sha256':digest(v.SYSTEM_PROMPT)}


def execute(plan,*,resume=False,client_factory=None):
    if plan['configuration']!=identity():raise ValueError('CONTINUATION_IMPLEMENTATION_CHANGED')
    if os.environ.get('OPENAI_MODEL')!=plan['model'] or not os.environ.get('OPENAI_API_KEY'):
        raise ValueError('MODEL_OR_CREDENTIAL_MISSING')
    if os.environ.get('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')!='https://api.openai.com/v1':
        raise ValueError('OFFICIAL_ENDPOINT_REQUIRED')
    if file_hash(plan['parent_manifest'])!=plan['parent_manifest_sha256']:raise ValueError('PARENT_MANIFEST_CHANGED')
    case,contracts,catalog,imported,parent,ledger=load_parent(plan['parent_manifest'],plan['case_id'])
    if (digest(parent)!=plan['parent_report_sha256'] or digest(ledger)!=plan['parent_ledger_sha256'] or
        digest(imported)!=plan['import_sha256'] or catalog.source_identity!=plan['source_identity']):
        raise ValueError('CONTINUATION_PROVENANCE_MISMATCH')
    output=Path(plan['output']);manifest={'plan':plan,'sha256':digest(plan)}
    if resume:
        if json.loads((output/'continuation_manifest.json').read_text())!=manifest:raise ValueError('CONTINUATION_RESUME_MISMATCH')
    else:
        output.mkdir(parents=True,exist_ok=False);atomic_json(output/'continuation_manifest.json',manifest)
    transport=JournalTransport(output,plan,client_factory or OpenAI,resume)
    groups=groups_for(imported['candidates']);sessions={};reused=set()
    for group in groups:
        cid=group['candidate']['candidate_id'];path=output/'sessions'/(group['key']+'.json')
        if cid in plan['retained_candidate_ids']:
            sessions[group['key']]=next(i['result'] for i in parent['issues'] if i['result']['candidate_id']==cid)
            reused.add(group['key'])
        elif cid not in plan['retry_candidate_ids']:raise ValueError('UNSCHEDULED_CANDIDATE')
        elif resume and path.exists():
            saved=json.loads(path.read_text())
            if saved['plan_sha256']!=digest(plan) or saved['result_sha256']!=digest(saved['result']):raise ValueError('CONTINUATION_SESSION_MISMATCH')
            v.validate_saved_result(saved['result'],contracts,catalog)
            if saved['result']['status']=='running':raise ValueError('UNCERTAIN_CANDIDATE_CANNOT_REPLAY')
            sessions[group['key']]=saved['result'];reused.add(group['key'])
    def report_now():
        report=aggregate(imported,contracts,catalog,groups,sessions,reused)
        report['continuation_provenance']={'parent_report_sha256':digest(parent),'retained_original_prompt_results':plan['retained_candidate_ids'],
            'prior_all_verification_usage':parent['efficiency']['verification'],
            'note':'Standard efficiency includes retained rejection + current candidate sessions, excludes superseded failed attempts; all historical attempts are separately retained.'}
        ledger_path=output/'budget_ledger.json'
        if ledger_path.exists():
            current=json.loads(ledger_path.read_text());report['transport_this_continuation']=current
            known={k:sum(e.get('usage',{}).get(k,0) for e in current['events']) for k in ('input_tokens','output_tokens','total_tokens')}
            report['actual_all_attempts_usage_including_history']={k:parent['efficiency']['total'][k]+known[k] for k in known}
            report['unknown_usage_generation_calls_this_continuation']=current['generation_calls']-sum('usage' in e for e in current['events'])
        atomic_json(output/'report.json',report);(output/'report.md').write_text(markdown(report));return report
    report_now()
    try:
        for group in groups:
            if group['key'] in sessions:continue
            def save(result):
                sessions[group['key']]=result
                atomic_json(output/'sessions'/(group['key']+'.json'),{'plan_sha256':digest(plan),'result_sha256':digest(result),'result':result})
                report_now()
            v.verify_candidate(group['candidate'],contracts,catalog,limits=v.Limits(**plan['limits']),checkpoint=save,
                token_budget=plan['budget']['max_reserved_tokens']-sum(r['usage']['total_tokens'] for k,r in sessions.items() if k not in reused),
                analyze_fn=lambda p,s,**kw:transport.call('verification',v.messages(p,s),v.VerificationResponse,kw['max_output_tokens'],p['candidate']['candidate_id']))
    finally:
        return_report=report_now()
    return return_report
