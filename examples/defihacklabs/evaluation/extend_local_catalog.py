"""Local metadata screening only. Does not execute PoCs, compile test code or call APIs."""
from pathlib import Path
import collections,csv,hashlib,json,re,subprocess

BASE=Path(__file__).resolve().parent
CAT=Path('/home/coca-cola/projects/DeFiHackLabs')
OUT=BASE/'catalog_v2'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open('x') as f: f.write(data)
def dump(name,data): write(name,json.dumps(data,indent=2)+'\n')

def main():
    if OUT.exists(): raise SystemExit('catalog_v2 already exists; refusing overwrite')
    commit=subprocess.check_output(['git','-C',str(CAT),'rev-parse','HEAD'],text=True).strip()
    static=re.compile(r'reentran|access.?control|authoriz|unchecked|tx.origin|delegatecall|arbitrary.{0,20}call|external.call|validation|initializ|signature|state.management|storage.collision|public.{0,10}(function|call)',re.I)
    economic=re.compile(r'oracle|price.manipulat|market.manipulat|flash.?loan|reserve.manipulat|governance|economic|tokenomic|compromis|private.key|phishing|frontend|credential|consensus|malicious.proposal|sandwich|rug.pull',re.I)
    rows=[];seen=set();inputs={};review=[]
    documents=[CAT/'README.md',*sorted((CAT/'past').glob('*/README.md'))]
    for doc in documents:
        text=doc.read_text();inputs[str(doc.relative_to(CAT))]=sha(doc)
        headings=list(re.finditer(r'^#{2,4}\s+(\d{8})\s*(?:-\s*)?(.+)$',text,re.M))
        for n,m in enumerate(headings):
            title=m[2].strip(); key=(m[1],title.lower())
            if key in seen: continue
            seen.add(key)
            block=text[m.end():headings[n+1].start() if n+1<len(headings) else len(text)]
            split=re.split(r'\s+-\s+',title,maxsplit=1)
            project=split[0];category=split[1] if len(split)>1 else ''
            paths=re.findall(r'(?:\./|\.\./)*src/test/[^\s)`\]<>]+\.sol',block)
            paths=list(dict.fromkeys('src/test/'+p.split('src/test/',1)[1] for p in paths))
            poc=next((CAT/p for p in paths if (CAT/p).is_file()),None)
            header='';source_url='';address='';tx='';chain='';root=''
            if poc:
                # Inspect documentation header only, before first import/interface/contract.
                content=poc.read_text(errors='replace')
                header='\n'.join(line for line in content.splitlines()[:100] if line.lstrip().startswith('//'))
                inputs[str(poc.relative_to(CAT))]=sha(poc)
                v=re.search(r'(?im)//\s*(?:Vulnerable|Victim) Contract\s*:\s*(.*)',header)
                if v:
                    a=re.search(r'0x[a-fA-F0-9]{40}',v[1]);address=a[0] if a else ''
                t=re.search(r'(?im)//\s*Attack Tx\s*:\s*(.*)',header)
                if t:
                    a=re.search(r'0x[a-fA-F0-9]{64}',t[1]);tx=a[0] if a else ''
                u=re.search(r'(?im)//\s*Vulnerable Contract Code\s*:\s*(https?://\S+)',header)
                source_url=u[1] if u else ''
                r=re.search(r'(?im)//\s*(?:Root cause|reason)\s*:\s*(.+)',header)
                root=r[1] if r else ''
                for host,label in [('bscscan','BSC'),('etherscan','Ethereum'),('polygonscan','Polygon'),('arbiscan','Arbitrum'),('ftmscan','Fantom'),('optimistic.etherscan','Optimism')]:
                    if host in header.lower():chain=label;break
            suitable=bool(static.search(category+' '+root))
            econ=bool(economic.search(category))
            reason='SOURCE_UNAVAILABLE' if suitable else ('EXCLUDED_CATEGORY' if econ else 'CATEGORY_REVIEW_REQUIRED')
            incident_id=m[1]+'-'+re.sub(r'[^a-z0-9]+','-',project.lower()).strip('-')
            ispilot=project.lower().strip()=='spankchain'
            if ispilot: reason='SELECTED_EXISTING_PILOT';suitable=True
            rows.append(dict(incident_id=incident_id,project=project,date=f'{m[1][:4]}-{m[1][4:6]}-{m[1][6:]}',chain=chain or 'UNAVAILABLE',
                catalog_document=str(doc.relative_to(CAT)),catalog_line=text[:m.start()].count('\n')+1,
                catalog_heading=title,poc_path=str(poc.relative_to(CAT)) if poc else '',
                referenced_poc_paths=';'.join(paths),attack_tx=tx,victim_address=address,
                affected_contract='LedgerChannel' if ispilot else 'UNAVAILABLE',affected_function='LCOpenTimeout(bytes32)' if ispilot else 'UNAVAILABLE',
                documented_category=category or 'UNAVAILABLE',documented_root_cause=root or category or 'UNAVAILABLE',
                source_url=source_url,source_availability='AVAILABLE_LOCAL_ARCHIVE' if ispilot else 'SOURCE_UNAVAILABLE',
                compiler_version='0.4.25' if ispilot else 'UNAVAILABLE',
                static_suitability='SUITABLE_DOCUMENTED_CATEGORY' if suitable else ('EXCLUDED_DOCUMENTED_CATEGORY' if econ else 'REQUIRES_MANUAL_CATEGORY_REVIEW'),
                status=reason,exclusion_reason='' if ispilot else ('No faithful victim source with incident provenance established locally; PoC is evidence only.' if suitable else ('Documented primary category falls outside static subset screening rules.' if econ else 'Category not sufficiently specific for automatic suitability judgment.')),
                limitations='Metadata screening, not exploit or code analysis; blank values unavailable. Chain inferred only from documented explorer hostname; multichain incidents require review.'))
    # Audit local Solidity file roles, without interpreting exploit behavior.
    audit=[]
    for p in sorted((CAT/'src').rglob('*.sol')):
        content=p.read_text(errors='replace')
        foundry=bool(re.search(r'import[^;]*(?:forge-std|basetest|Test\.sol)|\bis\s+(?:Test|BaseTest)',content))
        role='TEST_OR_POC' if foundry or re.search(r'exp|exploit',p.name,re.I) else ('INTERFACE_OR_LIBRARY_SUPPORT' if '/KyberSwap/' in str(p) or p.name in ['interface.sol','tokenhelper.sol','StableMath.sol'] else 'UNVERIFIED_ROLE_REQUIRES_REVIEW')
        audit.append(dict(path=str(p.relative_to(CAT)),sha256=sha(p),role=role))
    OUT.mkdir()
    with (OUT/'incident_inventory.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    dump('source_role_audit.json',audit)
    old=json.loads((BASE/'manifest.json').read_text())
    record=old['records'][0].copy()
    pilot=next((r for r in rows if r['status']=='SELECTED_EXISTING_PILOT'),None)
    if pilot:
        record['poc_path']=str(CAT/pilot['poc_path'])
        record['local_poc_sha256']=sha(Path(record['poc_path']))
    record['limitations']=[x for x in record['limitations'] if 'checkout' not in x]+['Checkout provides incident evidence; additional faithful victim sources have not been established.']
    manifest=dict(schema_version=2,status='INCOMPLETE_VICTIM_SOURCES',catalog_root=str(CAT),catalog_commit=commit,
        requested_subset_size=20,actual_subset_size=1,missing_case_count=19,primary_20_case_subset_frozen=False,
        selection_before_new_slither=True,new_slither_runs=0,records=[record],
        screening_counts=dict(collections.Counter(r['status'] for r in rows)),catalog_entries_screened=len(rows),
        limitations=['Catalog rows are deterministic metadata screens, not independent adjudications of every incident.',
        'No faithful additional victim sources were established. Candidate source status is not a statement that verified source is unavailable on the internet.',
        'No 20-case recall claimed; pilot outcome was already known.'])
    dump('manifest.json',manifest)
    baseline=json.loads((BASE/'slither_baseline.json').read_text())
    baseline['manifest_sha256']=sha(OUT/'manifest.json');baseline['status']='IMPORTED_PILOT_ONLY_NO_NEW_EVALUATIONS'
    dump('slither_baseline.json',baseline)
    with (OUT/'slither_baseline.csv').open('x',newline='') as f:
        f.write((BASE/'slither_baseline.csv').read_text())
    targets=json.loads((BASE/'verification_targets.json').read_text());targets['manifest_sha256']=sha(OUT/'manifest.json')
    dump('verification_targets.json',targets)
    counts=manifest['screening_counts']
    write('manifest.md',f'''# Local catalog screening, version 2

Catalog commit: `{commit}`. Metadata entries screened: **{len(rows)}**.
Screening decisions: `{json.dumps(counts)}`.

**20-case cohort not frozen: 1 source-backed pilot, 19 cases missing.**
PoCs were used only as documentation. No exploit execution or new Slither/LLM run occurred.
The checkout is primarily a reproduction catalog, not a verified victim-source archive.
`source_role_audit.json` records the local Solidity file-role screen. Non-test support
and unresolved file roles are not silently certified as faithful vulnerable contracts.
Victim sources still require incident/address/version provenance and their dependencies.

The source-backed case remains SpankChain: reentrancy, LedgerChannel.LCOpenTimeout(bytes32),
solc 0.4.25. The local official PoC linkage is now recorded in manifest.json.
The unchanged source snapshot remains in `../contracts/spankchain/SpankChain.sol`.
Imported baseline: compiled 1; analyzable 1; DETECTED 1; MISSED 0; AMBIGUOUS 0;
NOT_ANALYZABLE 0. Pilot-only recall 1/1; new LLM-ready targets 0. Additional available
warnings retain their previous unlabeled status. Raw full-default baseline limitations
remain as recorded in the original integration.

No 20 cases are selected solely to fill slots, and no source-unavailable candidate is
counted as MISSED or NOT_ANALYZABLE in a selected cohort. SOURCE_UNAVAILABLE applies
locally, not globally. Deterministic category matching is preliminary screening;
mixed categories and unknown metadata require manual review before future selection.

The original six integration files and their integrity hashes are preserved. This
versioned directory holds the extended inventory and metadata. Check both with:

```bash
.venv/bin/python examples/defihacklabs/evaluation/check_integrity.py
.venv/bin/python examples/defihacklabs/evaluation/check_catalog_v2.py
```

A new paid verification command is not applicable: the sole technical target is the
already-completed pilot. Obtain faithful victim sources locally, then select and freeze
a prospective cohort before running new default Slither analyses or preparing new
inference jobs. No ground-truth manifest is to be passed as an LLM payload.
''')
    dump('integrity_hashes.json',dict(catalog_commit=commit,catalog_inputs=inputs,
        outputs={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
    print(json.dumps(dict(entries_screened=len(rows),screening_counts=counts,solidity_files_audited=len(audit),selected=1,new_llm_targets=0),indent=2))

if __name__=='__main__': main()
