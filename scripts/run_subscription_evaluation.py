"""Project-separated DAppSCAN evaluation using ChatGPT-authenticated Codex only.

prepare reads source/provenance, never evaluation labels. execute freezes code,
does not retry a case, and stops when the included-plan client reports a failure.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from unittest.mock import patch

if sys.prefix!=sys.base_prefix:os.environ.setdefault('VIRTUAL_ENV',sys.prefix)
os.environ['PATH']=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')
from context_audit import direct_discovery as d,direct_verification as v
from context_audit.catalog import FragmentCatalog
from context_audit.codex_transport import CodexTransport,clean_environment,DEFAULT_MODEL,INPUT_OVERHEAD_RESERVE
from context_audit.direct_preparation import dependency_graph,project_root
from context_audit.cgt_inference import estimated_tokens
from context_audit.v2_artifacts import atomic_json,digest,file_hash,implementation_hash
from context_audit.v2_pipeline import run_verification

from context_audit.verification_profiles import PROFILES, VERSION as LIMIT_PROFILE_VERSION, limits_for

ROOT=Path(__file__).resolve().parents[1]

def identity():
    return {'modules':implementation_hash(['direct_discovery','direct_verification','verdict_consistency',
        'codex_transport','v2_pipeline','v2_artifacts','payload','v2_response','direct_preparation','function_index','verification_profiles']),
        'entrypoint':file_hash(Path(__file__))}

def catalog_for(case,proposal):
    base=Path(proposal)
    prepared=base/case['prepared_artifact']
    structural=json.loads((prepared/'structure.json').read_text())
    provenance=json.loads((prepared/'provenance.json').read_text())
    source=Path(case['source']);root=project_root(source)
    source_id=provenance['source_identity']
    assert source_id==case['source_identity']==structural['manifest']['source']
    assert file_hash(source)==source_id['source_sha256']
    assert source_id['preparation_sha256']==implementation_hash(['direct_preparation','direct','context','catalog','function_index'])
    assert source_id['sanitizer_sha256']==implementation_hash(['direct_preparation'])
    assert structural['manifest']['executed'] is False and structural['usage']['api_calls']==0
    assert structural['manifest']['artifact_sha256']==digest({k:x for k,x in structural.items() if k!='manifest'})
    texts,_=dependency_graph(source,root)
    assert digest({p.relative_to(root).as_posix():hashlib.sha256(text.encode()).hexdigest()
                   for p,text in sorted(texts.items())})==source_id['sanitized_project_sha256']
    catalog=FragmentCatalog(root);locations={}
    for fid,meta in provenance['fragment_metadata'].items():
        loc=meta['location'];path=(root/loc['file']).resolve()
        assert path in texts
        code=texts[path].encode()[loc['start']:loc['start']+loc['length']].decode()
        assert digest(code)==meta['source_sha256']
        fragment={'id':fid,'kind':meta['kind'],'name':meta['name'],'file':loc['file'],'source':code}
        v.safe_fragment(fragment);catalog.fragments[fid]=fragment;locations[fid]=loc
    assert digest(catalog.fragments)==source_id['catalog_sha256']
    assert digest(locations)==source_id['locations_sha256']
    assert digest(structural['contracts'])==source_id['structure_sha256']
    catalog.fragment_locations=locations;catalog.source_identity=source_id
    catalog.preparation_metadata=provenance['metadata']
    catalog.discovery_contracts=structural['contracts']
    catalog.function_index=structural.get('function_index')
    assert digest(catalog.function_index)==source_id['function_index_sha256']
    catalog.full_source_estimated_tokens=estimated_tokens(texts[source.resolve()])
    return structural['contracts'],catalog

def known_source_hashes():
    values=set()
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('source_sha256'),str):values.add(value['source_sha256'])
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    # Actual run manifests only. Preparation universes/proposals are not exposure.
    for p in (ROOT/'runs').rglob('*manifest.json'):
        try:visit(json.loads(p.read_text()))
        except (OSError,ValueError):pass
    for name in ('dappscan-oracle-2026-11-16','scanner-live-2026-11-16'):
        for p in (ROOT/'docs/reviews'/name).rglob('*report.json'):
            try:visit(json.loads(p.read_text()))
            except (OSError,ValueError):pass
    # Separate public review registries record only actual model attempts,
    # including unknown outcomes. Frozen plans/unrun source sets are not exposure.
    for p in (ROOT/'docs/reviews').rglob('subscription-exposure.json'):
        registry=json.loads(p.read_text())
        if registry.get('kind')!='subscription_exposure':
            raise ValueError('Invalid subscription exposure registry')
        for row in registry['attempted_cases']:
            checksum=row['source_sha256']; attempts=row['attempted_codex_turns']
            if (not isinstance(checksum,str) or len(checksum)!=64 or
                any(c not in '0123456789abcdef' for c in checksum) or
                type(attempts) is not int or attempts<1):
                raise ValueError('Invalid subscription exposure record')
            values.add(checksum)
    return values

def prepare(proposal,output,development_pilot_size=None,limit_profile='baseline'):
    chosen_limits=limits_for(limit_profile)
    if limit_profile!='baseline' and development_pilot_size is None:
        raise ValueError('NONBASELINE_PROFILE_REQUIRES_DEVELOPMENT_PILOT')
    if output.exists():raise ValueError('Choose a fresh evaluation directory')
    manifest=json.loads((proposal/'manifest.json').read_text())
    seen=known_source_hashes();cases=[];excluded=[]
    for c in manifest['cases']:
        if c['source_identity']['source_sha256'] in seen:
            excluded.append({'id':c['id'],'reason':'Prior exposure; no automatic rerun'})
        else:cases.append(c)
    cases.sort(key=lambda c:({'development':0,'validation':1,'held_out':2}[c['split']],c['id']))
    if development_pilot_size is not None:
        if not 1<=development_pilot_size<=3:raise ValueError('Pilot size must be 1 to 3')
        cases=[c for c in cases if c['split']=='development'][:development_pilot_size]
        if len(cases)!=development_pilot_size:raise ValueError('Insufficient fresh development cases')
    # Separate Codex condition: budget includes CLI overhead, without changing the
    # frozen API proposal or raising its original candidate/round ceilings.
    cases=[{**c,'preparation_budget':c['budget'],'limits':{**c['limits'],'max_candidates':min(c['limits']['max_candidates'],2),
                         'max_total_tokens':200000}} for c in cases]
    for case in cases:
        if limit_profile!='baseline':
            case['limits']=chosen_limits.model_dump()
        contracts,_=catalog_for(case,proposal)
        batches,_=d.make_batches(contracts)
        case_cap=(400000 if limit_profile=='baseline' else
            max(400000,case['limits']['max_total_tokens']+len(batches)*(INPUT_OVERHEAD_RESERVE+case['limits']['max_input_tokens']+8000)))
        case['budget']={'max_discovery_turns':len(batches),
            'max_codex_turns':len(batches)+case['limits']['max_candidates']*case['limits']['max_rounds'],
            'token_count_requests':0,'api_key_requests':0,'max_observed_tokens':case_cap,
            'max_verification_tokens':case['limits']['max_total_tokens'],
            'input_overhead_reserve_tokens':INPUT_OVERHEAD_RESERVE}
    assert len({c['id'] for c in cases})==len(cases)
    projects={}
    for case in cases:
        assert projects.setdefault(case['project'],case['split'])==case['split']
    plan={'provider':'codex_chatgpt','model':DEFAULT_MODEL,'proposal':str(proposal.resolve()),
        'proposal_manifest_sha256':file_hash(proposal/'manifest.json'),'configuration':identity(),
        'output':str(output.resolve()),'cases':cases,'excluded_prior_cases':excluded,
        'limits':{'max_model_turns':20 if development_pilot_size else 300,
                  'max_observed_tokens':750000 if development_pilot_size else 5000000,
                  'max_case_observed_tokens':400000},
        'development_pilot_size':development_pilot_size,
        'limit_profile':limit_profile,'limit_profile_version':LIMIT_PROFILE_VERSION,
        'api_key_requests':0,'paid_fallback':False,'automatic_application_retries':0,
        'case_policy':'One pass; retain semantic failures; stop batch on provider/transport errors; never replay a finalized case.',
        'evaluation_labels_loaded':False,'purpose':'Fresh subscription-backend evaluation; not comparable to historical API results without qualification.'}
    if limit_profile!='baseline':
        plan['limits']={
            'max_model_turns':sum(c['budget']['max_codex_turns'] for c in cases),
            'max_observed_tokens':sum(c['budget']['max_observed_tokens'] for c in cases),
            'max_case_observed_tokens':max(c['budget']['max_observed_tokens'] for c in cases)}
    output.mkdir(parents=True)
    atomic_json(output/'plan.json',plan)
    (output/'PLAN.md').write_text('# Subscription-backed DAppSCAN evaluation\n\n'
        f"Sources: {len(cases)}; projects: {len(projects)}; excluded prior cases: {len(excluded)}.\n\n"
        f"Investigation profile: {limit_profile} ({LIMIT_PROFILE_VERSION}). Separate fresh approval required.\n\n"
        f"Splits: {dict(Counter(c['split'] for c in cases))}.\n\n"
        'Uses existing ChatGPT/Codex allowance only. No API key, API fallback, or credit purchases. '
        f"Stops at allowance/transport errors or {plan['limits']['max_model_turns']} turns / {plan['limits']['max_observed_tokens']:,} observed tokens. "
        'Output guidance is not a hard server token cap; the last turn can exceed the observed-token threshold. '
        'No automatic application retries. Codex may perform its builtin connection retries.\n\n'
        'The original project/duplicate split is preserved. Labels remain separate until post-inference review. '
        'All partial/unrun cases must be disclosed; no accuracy estimate is produced from raw finding counts.\n')
    print(json.dumps({'cases':len(cases),'projects':len(projects),'splits':dict(Counter(c['split'] for c in cases)),
        'excluded_prior':len(excluded),'plan_sha256':digest(plan),'api_cost':'No API-key billing'},indent=2),flush=True)

def execute(output,approved,resume=False):
    plan=json.loads((output/'plan.json').read_text())
    if digest(plan)!=approved or plan['configuration']!=identity():raise ValueError('Frozen plan/code mismatch')
    proposal=Path(plan['proposal'])
    if file_hash(proposal/'manifest.json')!=plan['proposal_manifest_sha256']:raise ValueError('Proposal changed')
    for key in ('OPENAI_API_KEY','CODEX_API_KEY','AZURE_OPENAI_API_KEY','OPENAI_BASE_URL'):
        os.environ.pop(key,None)
    os.environ['OPENAI_MODEL']=plan['model']
    # Complete source-only provenance checks before the first model invocation.
    for case in plan['cases']:
        prepared_contracts,_=catalog_for(case,proposal)
        prepared_batches,_=d.make_batches(prepared_contracts)
        limits=v.Limits(**case['limits'])
        if (case['budget']['max_discovery_turns']!=len(prepared_batches) or
            case['budget']['max_codex_turns']!=len(prepared_batches)+limits.max_candidates*limits.max_rounds or
            case['budget']['max_verification_tokens']!=limits.max_total_tokens):
            raise ValueError('CASE_CALL_OR_VERIFICATION_BUDGET_MISMATCH')
    rows=[];turns=0;tokens=0
    for index,case in enumerate(plan['cases']):
        if plan['configuration']!=identity():raise ValueError('Code changed during evaluation')
        destination=output/'cases'/case['id']
        seal=destination/'completed.json'
        if seal.exists():
            if not resume:raise ValueError('Existing case requires explicit resume')
            row=json.loads(seal.read_text());rows.append(row);turns+=row['model_turns'];tokens+=row['reported_tokens']
            continue
        if destination.exists():raise ValueError('Uncertain case is not automatically replayed')
        if turns>=plan['limits']['max_model_turns'] or tokens>=plan['limits']['max_observed_tokens']:break
        destination.mkdir(parents=True)
        atomic_json(destination/'started.json',{'case_id':case['id'],'plan_sha256':digest(plan)})
        started=monotonic()
        contracts,catalog=catalog_for(case,proposal)
        batches,_=d.make_batches(contracts)
        maximum=min(len(batches)+case['limits']['max_candidates']*case['limits']['max_rounds'],plan['limits']['max_model_turns']-turns)
        transport=CodexTransport(destination/'transport',plan['model'],max_calls=maximum,
            max_tokens=min(case['budget']['max_observed_tokens'],plan['limits']['max_case_observed_tokens'],plan['limits']['max_observed_tokens']-tokens))
        with patch('openai.OpenAI.__init__',side_effect=AssertionError('Paid API path forbidden')):
            found=d.run_discovery(contracts,catalog,execute=True,analyze_fn=transport.discover)
            atomic_json(destination/'analysis/discovery.json',found)
            report=run_verification(found,contracts,catalog,destination/'analysis',
                limits=v.Limits(**case['limits']),analyze_fn=transport.verify,input_token_estimator=transport.estimate_input_tokens)
        atomic_json(destination/'report.json',report)
        counts=report['coverage_counts']
        partial=bool(found['errors'] or counts['processing_failures'] or counts['skipped_candidates'] or counts['pending_candidates'])
        row={'case':case['id'],'source':case['source'],'source_sha256':case['source_identity']['source_sha256'],
            'split':case['split'],'status':'partial' if partial else 'completed',
            'model_turns':transport.state['calls'],'reported_tokens':transport.state['observed_tokens'],
            'counts':counts,'transport_stopped':transport.state['stopped'],
            'seconds':round(monotonic()-started,2),'report_sha256':digest(report)}
        atomic_json(seal,row);rows.append(row);turns+=row['model_turns'];tokens+=row['reported_tokens']
        summary={'planned_cases':len(plan['cases']),'finished_cases':len(rows),'cases':rows,
            'model_turns':turns,'reported_tokens':tokens,'api_key_requests':0,
            'provider':'codex_chatgpt','model':plan['model'],'evaluation_labels_loaded':False,
            'status':'running','confirmed_findings':sum(r['counts']['confirmed_candidates'] for r in rows),
            'partial_cases':sum(r['status']=='partial' for r in rows)}
        atomic_json(output/'run-status.json',summary)
        print(json.dumps({'finished':len(rows),'total':len(plan['cases']),'case':case['id'],
            'status':row['status'],'confirmed':counts['confirmed_candidates'],'turns':turns,'tokens':tokens}),flush=True)
        if transport.state['stopped']:break
    summary={'planned_cases':len(plan['cases']),'finished_cases':len(rows),'cases':rows,
        'model_turns':turns,'reported_tokens':tokens,'api_key_requests':0,'provider':'codex_chatgpt',
        'model':plan['model'],'evaluation_labels_loaded':False,
        'status':'finished' if len(rows)==len(plan['cases']) else 'stopped_before_all_cases',
        'confirmed_findings':sum(r['counts']['confirmed_candidates'] for r in rows),
        'partial_cases':sum(r['status']=='partial' for r in rows)}
    atomic_json(output/'run-status.json',summary)
    print(json.dumps({k:value for k,value in summary.items() if k!='cases'},indent=2),flush=True)

def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('action',choices=('prepare','execute'))
    parser.add_argument('--proposal',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--approved-plan-sha256')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--development-pilot-size',type=int)
    parser.add_argument('--limit-profile',choices=PROFILES,default='baseline')
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.proposal,args.output,args.development_pilot_size,args.limit_profile)
    else:execute(args.output,args.approved_plan_sha256,args.resume)

if __name__=='__main__':main()
