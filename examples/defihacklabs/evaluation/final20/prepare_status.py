"""Review only the user-nominated 20 source identities. No evaluation/network calls."""
from pathlib import Path
import csv,hashlib,json,re,shutil
BASE=Path(__file__).resolve().parent
EVAL=BASE.parent
ROOT=EVAL.parents[2]
CAT=Path('/home/coca-cola/projects/DeFiHackLabs')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
CASES=[
('spankchain','SpankChain',['2018-10/SpankChain_exp.sol'],'Ethereum','LedgerChannel','LCOpenTimeout(bytes32)','reentrancy','0xf91546835f756DA0c10cFa0CDA95b15577b84aA7'),
('sqtokenstaking','SQTokenStaking',['2026-05/SQTokenStaking_exp.sol'],'BSC',None,None,'access-control / validation',None),
('subquery-settings','SubQuery Settings',['2026-04/SubQuerySettings_exp.sol'],'Base','Settings','setBatchAddress','access control',None),
('giddyvaultv3','GiddyVaultV3',['2026-04/giddyvaultv3_compound_auth_exp.sol'],'Ethereum','GiddyVaultV3','compound','signature authorization',None),
('joeagent','JoeAgent',['2026-05/JoeAgent_exp.sol'],'BSC','Joe Agent','removeLiquidityViaContract','reentrancy',None),
('muredistribution','MureDistribution',['2026-05/MureDistribution_exp.sol'],'Ethereum',None,None,'UNAVAILABLE',None),
('xsurge','XSURGE',['2021-08/XSURGE_exp.sol'],'BSC',None,None,'reentrancy','0xE1E1Aa58983F6b8eE8E4eCD206ceA6578F036c21'),
('mapprotocol-butter','MAPProtocol / Butter',['2026-05/MAPProtocol_exp.sol'],'Ethereum',None,None,'UNAVAILABLE',None),
('grim-finance','Grim Finance',['2021-12/Grim_exp.sol'],'Fantom','GrimBoostVault','depositFor','reentrancy','0x660184CE8AF80e0B1e5A1172A16168b15f4136bF'),
('parity-walletlibrary','Parity WalletLibrary',['2017-11/Parity_kill_exp.sol'],'Ethereum','WalletLibrary','initWallet / kill','unprotected initialization','0x863DF6BFa4469f3ead0bE8f9F2AAE51c91A907b4'),
('bifi','BiFi',['2026-10/BiFi_exp.sol'],'Ethereum','TokenHandler / interestModel','_checkFirstAction / getInterestAmount','state/accounting lifecycle','0x808c3ba97268dbf9695b1ec10729e09c7e67a9e3'),
('newmarket-squid','NewMarketTrading / SquidRouterModule',['2026-05/NewMarketTrading_exp.sol','2026-05/SquidRouterModule_exp.sol'],'Ethereum','SquidRouterModule','expressExecuteWithToken / _executeWithToken','authorization',None),
('atm','ATM',['2024-04/ATM_exp.sol','2026-06/ATM_exp.sol','2026-06/ATM_LP_Burn_exp.sol'],None,None,None,'INCIDENT_IDENTITY_AMBIGUOUS',None),
('burgerswap','BurgerSwap',['2021-05/BurgerSwap_exp.sol'],'BSC',None,None,'reentrancy / validation','0x7ac55ac530f2c29659573bde0700c6758d69e677'),
('hundred-finance','Hundred Finance',['2022-03/HundredFinance_exp.sol','2023-04/HundredFinance_2_exp.sol'],None,None,None,'INCIDENT_IDENTITY_AMBIGUOUS',None),
('rari-fuse','Rari Capital Fuse',['2022-04/Rari_exp.sol'],'Ethereum',None,None,'reentrancy','0x26267e41CeCa7C8E0f143554Af707336f27Fa051'),
('visor-finance','Visor Finance',['2021-12/Visor_exp.sol'],'Ethereum',None,'deposit','reentrancy / authorization','0xC9f27A50f82571C1C8423A42970613b8dBDA14ef'),
('revest-finance','Revest Finance',['2022-03/Revest_exp.sol'],'Ethereum',None,None,'reentrancy','0x2320A28f52334d62622cc2EaFa15DE55F9987eD9'),
('lendfme','LendfMe',['2020-04/LendfMe_exp.sol'],'Ethereum',None,None,'reentrancy','0x0eEe3E3828A45f7601D5F54bF49bB01d1A9dF5ea'),
('popsicle-finance','Popsicle Finance',['2021-08/Popsicle_exp.sol'],'Ethereum',None,None,'reward-accounting state management',None)]

def main():
    if (BASE/'source_status.json').exists():raise SystemExit('Refusing overwrite')
    protected={str(p.relative_to(ROOT)):sha(p) for folder in [ROOT/'examples/defihacklabs',ROOT/'results',ROOT/'test/defihacklabs'] for p in folder.rglob('*') if p.is_file() and BASE not in p.parents and '.generated' not in p.parts}
    inventory=list(csv.DictReader((EVAL/'catalog_v2/incident_inventory.csv').open()))
    rows=[]
    for ident,project,paths,chain,contract,function,category,victim in CASES:
        evidence=[];links=[];impl=[];dates=[]
        for short in paths:
            p=CAT/'src/test'/short
            if not p.exists():continue
            text=p.read_text(errors='replace')
            comments='\n'.join(l for l in text.splitlines()[:100] if l.lstrip().startswith('//'))
            addr=re.search(r'(?im)//\s*Vulnerable(?: Contract| proxy)?\s*:\s*(?:https?://[^\s]*/address/)?(0x[a-fA-F0-9]{40})',comments)
            if not victim and addr and ident not in ['atm','hundred-finance']:victim=addr[1]
            for l in comments.splitlines():
                if re.search(r'Implementation\s*:|Handler logic\s*:',l,re.I):impl+=re.findall(r'0x[a-fA-F0-9]{40}',l)
                if re.search(r'Contract Code|Verified source|Handler logic|Interest model',l,re.I):links+=re.findall(r'https?://\S+',l)
            matched=next((x for x in inventory if x['poc_path']==str(p.relative_to(CAT))),None)
            if matched:
                dates.append(matched['date'])
                if category=='UNAVAILABLE':category=matched['documented_category']
            evidence.append({'path':str(p),'sha256':sha(p),'role':'INCIDENT_EVIDENCE_ONLY_NOT_VICTIM_SOURCE'})
        status='SOURCE_UNAVAILABLE';reason='No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.'
        if ident in ['joeagent','bifi','rari-fuse']:
            status='PROXY_HISTORY_UNRESOLVED';reason='Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally.'
        if ident=='parity-walletlibrary':
            status='SOURCE_NEEDS_REVIEW';reason='Local SmartBugs parity_wallet_bug_2.sol is an annotated archive lead; exact equivalence to this library deployment/version not established. Not certified or copied as ready.'
        if ident in ['atm','hundred-finance']:
            status='SOURCE_NEEDS_REVIEW';reason='Multiple distinct local incidents match this project name; exact incident must be resolved before assigning a victim/source. Alternate PoC references retained.'
        if ident=='newmarket-squid':
            status='SOURCE_NEEDS_REVIEW';reason='Ethereum incident documents verified source at the same address on Base; cross-chain deployed-code equivalence is not established and no raw verified snapshot is local.'
        source_files=[];compiler='0.6.12' if ident=='bifi' else None
        if ident=='spankchain':
            status='SOURCE_READY';reason='Reuse previously accepted complete pilot unchanged; byte-identical local archived source and license copied. Archived-source/deployed-bytecode limitations retained.'
            raw=BASE/'contracts'/ident/'raw';raw.mkdir(parents=True)
            for name in ['SpankChain.sol','LICENSE-SpankChain.txt']:
                src=EVAL.parent/name;dest=raw/name;shutil.copyfile(src,dest)
                source_files.append({'path':str(dest.relative_to(ROOT)),'sha256':sha(dest),'origin':str(src.relative_to(ROOT))})
            compiler='0.4.25'
        record=dict(incident_id=ident,project=project,source_status=status,documented_incident_dates=sorted(set(dates)),
            poc_evidence=evidence,chain=chain,victim_address=victim,proxy_address=victim if ident in ['joeagent','bifi','rari-fuse'] else None,
            implementation_address=list(dict.fromkeys(impl)) or None,
            incident_time_implementation_verified=False if ident in ['joeagent','bifi','rari-fuse'] else None,
            affected_contract=contract,affected_function=function,documented_vulnerability_category=category,
            source_provider_references=links,source_files=source_files,compiler_version=compiler,
            compiler_evidence='Existing pilot compilation' if ident=='spankchain' else 'PoC header explicitly states solc 0.6.12' if ident=='bifi' else 'UNAVAILABLE; PoC pragma is not victim compiler evidence',
            deployment_version_correspondence='Previously accepted archived pilot; fresh deployed-bytecode verification not established' if ident=='spankchain' else 'NOT_ESTABLISHED',
            compilation_reproducibility='Previously compiled unchanged using installed 0.4.25' if ident=='spankchain' else 'NOT_ESTABLISHED_WITHOUT_EXACT_SOURCE_AND_DEPENDENCIES',
            main_reason=reason,limitations=['Metadata/source-readiness review only; no compilation, Slither, inference or exploit execution.', 'Unknown proxy status is not an assertion of direct deployment.'])
        rows.append(record)
    counts={s:sum(r['source_status']==s for r in rows) for s in ['SOURCE_READY','SOURCE_NEEDS_REVIEW','SOURCE_UNAVAILABLE','PROXY_HISTORY_UNRESOLVED','WRONG_SOURCE_VERSION']}
    data={'cohort_frozen':False,'nominated_count':20,'status_counts':counts,'records':rows,
        'protected_input_hashes':protected,'limitations':['Only the 20 nominated candidates reviewed. No silent replacement.','No new external acquisition performed: prior DNS failures remain unresolved.','No source hash or compiler inferred from exploit PoC code.']}
    (BASE/'source_status.json').write_text(json.dumps(data,indent=2)+'\n')
    fields=['incident_id','project','source_status','chain','victim_address','implementation_address','affected_contract','affected_function','compiler_version','main_reason']
    with (BASE/'source_status.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
    lines=['# Nominated 20-case source readiness','',f'Frozen: **NO**. Counts: `{json.dumps(counts)}`.','',
        'Only SpankChain meets the previously accepted pilot source requirements. Its original documentation and integrity hashes remain unchanged. Raw source is copied without modification, including the pre-existing formatting/provenance note. This is not a fresh deployed-bytecode verification.','',
        '| Incident | Status | Victim | Implementation reference (unvalidated) | Compiler | Main reason |','|---|---|---|---|---|---|']
    for r in rows:lines.append('| '+' | '.join(str(x or 'Unavailable').replace('|','/') for x in [r['project'],r['source_status'],r['victim_address'],r['implementation_address'],r['compiler_version'],r['main_reason']])+' |')
    lines+=['','## Cases preventing freeze','',*['- '+r['project']+': '+r['main_reason'] for r in rows if r['source_status']!='SOURCE_READY'],'',
        'Source-provider links are documentary references, not evidence of successful retrieval. PoC source pragmas are deliberately excluded from victim compiler identification. BiFi compiler 0.6.12 is explicitly reported by its documentation; it is not locally compiled or independently verified here. For multi-contract cases, a single victim address may be only an entrypoint; the complete vulnerable implementation/dependency set remains to be established.',
        '', 'Parity archive lead: `datasets/smartbugs-curated/dataset/access_control/parity_wallet_bug_2.sol`. It is not copied into the ready pool without deployment equivalence. ATM retains 2024-04, 2026-06 token and 2026-06 LP-burn references; Hundred retains both 2022-03 and 2023-04 references. The cohort nomination has not silently selected among these incidents.',
        '', 'No new source was certified from a different-chain deployment or current proxy implementation. Existing evaluation, source-acquisition and research files were read only. No final metrics are computed.']
    (BASE/'source_status.md').write_text('\n'.join(lines)+'\n')
    for p,h in protected.items():assert sha(ROOT/p)==h,p
    print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
