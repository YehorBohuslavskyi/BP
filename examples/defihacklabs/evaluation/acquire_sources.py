"""Read-only public source GETs and local metadata checks. No evaluation or execution.

Creates a new acquisition ledger; never overwrites an existing run. Successful HTTP
responses require provenance review before any verified snapshot is certified.
"""
import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
CAT=Path('/home/coca-cola/projects/DeFiHackLabs')
CHAINS={'mainnet':('Ethereum',1),'ethereum':('Ethereum',1),'bsc':('BSC',56),
        'polygon':('Polygon',137),'arbitrum':('Arbitrum',42161),'optimism':('Optimism',10),
        'avalanche':('Avalanche',43114),'fantom':('Fantom',250),'gnosis':('Gnosis',100),
        'base':('Base',8453),'blast':('Blast',81457),'linea':('Linea',59144),'celo':('Celo',42220)}
HOSTS={'etherscan.io':('Ethereum',1),'bscscan.com':('BSC',56),'polygonscan.com':('Polygon',137),
       'arbiscan.io':('Arbitrum',42161),'optimistic.etherscan.io':('Optimism',10),
       'snowtrace.io':('Avalanche',43114),'ftmscan.com':('Fantom',250),'basescan.org':('Base',8453),
       'gnosisscan.io':('Gnosis',100),'blastscan.io':('Blast',81457)}
ADDRESS=re.compile(r'0x[a-fA-F0-9]{40}(?![a-fA-F0-9])')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def get(url):
    try:
        with urlopen(Request(url,headers={'User-Agent':'BP-academic-source-acquisition/1.0'}),timeout=8) as r:
            return {'status':'HTTP_SUCCESS_REQUIRES_PROVENANCE_REVIEW','http_status':r.status,'url':url},r.read(32*1024*1024)
    except HTTPError as e:return {'status':'NOT_FOUND' if e.code==404 else 'HTTP_ERROR','http_status':e.code,'url':url},None
    except (URLError,OSError,TimeoutError) as e:return {'status':'TRANSPORT_ERROR','url':url,'error':str(e)},None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=BASE);args=parser.parse_args()
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['source_acquisition.csv','source_acquisition_summary.md','source_acquisition_evidence.json']:
        if (out/name).exists():raise SystemExit(f'Refusing overwrite: {out/name}')
    rows=[r for r in csv.DictReader((BASE/'catalog_v2/incident_inventory.csv').open()) if r['status']=='SOURCE_UNAVAILABLE']
    assert len(rows)==277
    # Preserve all existing acquisition-independent research files with hashes.
    protected={str(p.relative_to(ROOT)):sha(p) for folder in [ROOT/'results',ROOT/'examples',ROOT/'src',ROOT/'test/defihacklabs']
               for p in folder.rglob('*') if p.is_file() and 'source_pool' not in p.parts and '.generated' not in p.parts
               and '__pycache__' not in p.parts and '.git' not in p.parts}
    archive_files=list((ROOT/'datasets/cgt/source').glob('*.sol'))+list((ROOT/'datasets/smartbugs-curated/dataset').rglob('*.sol'))
    # Address references are leads, not proof of deployment/source equivalence.
    wanted={r['victim_address'].lower() for r in rows if r['victim_address']}
    archive_hits=collections.defaultdict(list)
    for p in archive_files:
        for address in {a.lower() for a in ADDRESS.findall(p.read_text(errors='replace'))}&wanted:
            archive_hits[address].append(str(p.relative_to(ROOT)))
    def process(row):
        evidence={'incident_id':row['incident_id'],'metadata_source':row['poc_path']}
        p=CAT/row['poc_path'] if row['poc_path'] else None
        text=p.read_text(errors='replace') if p and p.is_file() else ''
        comments=[line for line in text.splitlines() if line.lstrip().startswith('//')]
        victim_refs=[];impl=[];proxy=[];function=[];source_links=[]
        for line in comments:
            if re.search(r'(?i)(vulnerable|victim).{0,12}contract\s*:',line): victim_refs+=ADDRESS.findall(line)
            if re.search(r'(?i)implementation|logic.address',line):impl+=ADDRESS.findall(line)
            if re.search(r'(?i)proxy',line):proxy+=ADDRESS.findall(line)
            if re.search(r'(?i)affected.function\s*:',line):function.append(line.split(':',1)[-1].strip())
            if re.search(r'(?i)(vulnerable.contract.code|source.code)\s*:',line):source_links+=re.findall(r'https?://[^\s<>]+',line)
        victims=list(dict.fromkeys(victim_refs or ([row['victim_address']] if row['victim_address'] else [])))
        implementations=list(dict.fromkeys(impl));proxies=list(dict.fromkeys(proxy))
        links=list(dict.fromkeys(source_links or ([row['source_url']] if row['source_url'] else [])))
        networks=set()
        for link in links:
            host=urlparse(link).hostname or '';host=host.removeprefix('www.')
            if host in HOSTS:networks.add(HOSTS[host])
        # Fork name used solely as chain metadata, never execute the PoC.
        if not networks:
            for name in re.findall(r'createSelectFork\(\s*"([^"]+)"',text):
                if name.lower() in CHAINS:networks.add(CHAINS[name.lower()])
        chain,chain_id=next(iter(networks)) if len(networks)==1 else ('UNAVAILABLE',None)
        evidence.update(victim_addresses=victims,proxy_references=proxies,implementation_references=implementations,
            affected_functions=function,source_links=links,chain_id=chain_id,
            proxy_relationship_status='DOCUMENTED_REFERENCE_REQUIRES_HISTORICAL_VALIDATION' if proxies or implementations else 'UNKNOWN_NOT_ASSUMED_NON_PROXY',
            local_archive_leads=archive_hits.get(victims[0].lower(),[]) if len(victims)==1 else [])
        attempts=[]
        for address in list(dict.fromkeys(victims+implementations)) if chain_id else []:
            result,body=get(f'https://sourcify.dev/server/v2/contract/{chain_id}/{address}?fields=all')
            attempts.append(result)
            if body:
                evidence.setdefault('retrieved_responses',[]).append({'provider':'Sourcify','address':address,'body_sha256':hashlib.sha256(body).hexdigest()})
                dest=out/'source_pool'/row['incident_id']/'pending_provider_responses';dest.mkdir(parents=True,exist_ok=True)
                (dest/f'sourcify-{address}.json').write_bytes(body)
        evidence['sourcify_attempts']=attempts
        sourcify='METADATA_INSUFFICIENT' if not attempts else ('TRANSPORT_ERROR' if all(a['status']=='TRANSPORT_ERROR' for a in attempts) else 'REVIEW_RESPONSE_REQUIRED' if evidence.get('retrieved_responses') else 'LOOKUP_UNSUCCESSFUL')
        # A documented source link is not itself evidence that a page is verified.
        # GET only the explicitly referenced explorer page; never extract decompiled code.
        explorer=[]
        for link in links:
            if (urlparse(link).hostname or '').removeprefix('www.') in HOSTS:
                result,body=get(link);explorer.append(result)
                if body:
                    dest=out/'source_pool'/row['incident_id']/'pending_provider_responses';dest.mkdir(parents=True,exist_ok=True)
                    (dest/f'explorer-{len(explorer)}.html').write_bytes(body)
        evidence['explorer_attempts']=explorer
        archive='REFERENCE_ONLY_EQUIVALENCE_UNESTABLISHED' if evidence['local_archive_leads'] else 'NO_EXACT_PROVENANCE_ESTABLISHED'
        reason='; '.join(filter(None,[
            'Missing or ambiguous chain metadata' if chain_id is None else '',
            'No explicit victim address recovered' if not victims else '',
            'Provider transport failure; verification status unknown' if sourcify=='TRANSPORT_ERROR' else '',
            'Retrieved response requires verified-match and historical implementation review' if evidence.get('retrieved_responses') else '',
            'Multiple victim addresses require role review' if len(victims)>1 else '',
            'Historical proxy/implementation equivalence not established' if proxies or implementations else '',
            'No faithful exact local archive established']))
        ledger=dict(incident_id=row['incident_id'],project=row['project'],vulnerability_category=row['documented_category'],
            chain=chain,victim_address=';'.join(victims),implementation_address=';'.join(implementations),
            sourcify_status=sourcify,explorer_status='NOT_DOCUMENTED' if not explorer else 'TRANSPORT_ERROR' if all(a['status']=='TRANSPORT_ERROR' for a in explorer) else 'VERIFIED_SOURCE_EXTRACTION_REQUIRES_REVIEW',
            local_archive_status=archive,final_source_status='SOURCE_UNAVAILABLE',compiler_version='',reason=reason,snapshot_path='')
        return ledger,evidence
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(process,rows))
    ledger=[x[0] for x in results]; evidence=[x[1] for x in results]
    with (out/'source_acquisition.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
    counts=dict(collections.Counter(r['sourcify_status'] for r in ledger))
    data=dict(candidate_records_attempted=len(rows),sourcify_candidate_attempts=sum(bool(e['sourcify_attempts']) for e in evidence),
        sourcify_http_requests=sum(len(e['sourcify_attempts']) for e in evidence),
        explorer_candidate_attempts=sum(bool(e['explorer_attempts']) for e in evidence),
        sourcify_status_counts=counts,verified_snapshots=0,records=evidence,
        protected_input_hashes=protected,limitations=['No network failure is classified as unverified bytecode or absent verification.','Responses, if any, remain pending review and do not become certified sources automatically.'])
    (out/'source_acquisition_evidence.json').write_text(json.dumps(data,indent=2)+'\n')
    summary=f'''# Source acquisition attempt

Candidates attempted (metadata and archive screening): {len(rows)}.
Sourcify candidate requests: {data['sourcify_candidate_attempts']} ({data['sourcify_http_requests']} HTTP GETs).
Explorer candidate requests: {data['explorer_candidate_attempts']}.
Sourcify outcomes: {json.dumps(counts)}.

New verified source-backed snapshots: **0**. Sourcify successes: 0;
explorer-source successes: 0; exact archive-source successes: 0.
Unverified-bytecode failures: **0 established**. Proxy-only failures: **not established**.
Ambiguous implementation failures: not independently established; documented references
are retained for review in source_acquisition_evidence.json. Do not conflate unreachable
providers with absent/unverified sources. All final SOURCE_UNAVAILABLE statuses are
local acquisition outcomes, not statements about public verification availability.

No successful incident list, compiler versions or certified proxy/implementation pairs
can be reported. Existing SpankChain remains the sole previous source-backed pilot,
not a new acquisition and not included in the 277-candidate denominator.
At least 25 strong source-backed candidates: **NO**.

Main bottleneck: provider connectivity and incomplete/unambiguous chain/address metadata.
Shell HTTPS requests fail DNS in this environment; the web-tool Sourcify contract
lookup was also inaccessible. No source bytes were reconstructed from rendered pages,
bytecode or PoCs. Local archive address references are leads only; no exact deployment
identity has been established. Proxy lookup, if later reachable, must be checked against
the incident-time implementation, not merely the current proxy implementation.

This run does not freeze a cohort, compile, run Slither, invoke a verifier or compute
any detection metrics. Existing research files are preserved and hash checked.
The acquisition script refuses overwrites; a retry must use a fresh directory:

```bash
.venv/bin/python examples/defihacklabs/evaluation/acquire_sources.py --output-dir /tmp/bp-source-acquisition-retry
```

The script records downloaded provider responses as pending review; a successful HTTP
response alone never earns SOURCE_VERIFIED_AND_SNAPSHOTTED. Review must establish a
verified match, complete source content, root unit, compiler/settings and historical
proxy linkage before certifying an immutable raw snapshot. No guessed ABI or victim
function is used to certify identity.
'''
    (out/'source_acquisition_summary.md').write_text(summary)
    for name,h in protected.items():assert sha(ROOT/name)==h, name
    print(json.dumps({k:v for k,v in data.items() if k not in ['records','protected_input_hashes']},indent=2))

if __name__=='__main__':main()
