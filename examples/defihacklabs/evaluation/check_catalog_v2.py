"""Read-only checks for the versioned local incident catalog; no inference."""
from pathlib import Path
import csv,hashlib,json,subprocess
BASE=Path(__file__).resolve().parent
OUT=BASE/'catalog_v2'
ROOT=BASE.parents[2]
CAT=Path('/home/coca-cola/projects/DeFiHackLabs')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    r=json.loads((OUT/'integrity_hashes.json').read_text())
    assert subprocess.check_output(['git','-C',str(CAT),'rev-parse','HEAD'],text=True).strip()==r['catalog_commit']
    for p,h in r['catalog_inputs'].items():assert sha(CAT/p)==h,p
    for p,h in r['outputs'].items():assert sha(OUT/p)==h,p
    m=json.loads((OUT/'manifest.json').read_text())
    rows=list(csv.DictReader((OUT/'incident_inventory.csv').open()))
    assert len(rows)==m['catalog_entries_screened']==907
    assert m['actual_subset_size']==1 and not m['primary_20_case_subset_frozen']
    for x in m['records']:
        assert sha(ROOT/x['source_path'])==x['source_sha256']
        assert sha(Path(x['poc_path']))==x['local_poc_sha256']
    b=json.loads((OUT/'slither_baseline.json').read_text())
    t=json.loads((OUT/'verification_targets.json').read_text())
    assert b['manifest_sha256']==t['manifest_sha256']==sha(OUT/'manifest.json')
    assert t['new_paid_targets']==0 and b['llm_calls_made']==0
    assert all(x['already_completed_pilot'] for x in t['technical_targets'])
    print('PASS: local catalog provenance, 907 metadata rows, versioned output hashes, unchanged victim source, pilot-only targets.')
if __name__=='__main__':main()
