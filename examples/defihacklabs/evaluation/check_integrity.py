"""Read-only validation of the incomplete local evaluation integration. No API calls."""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    hashes=json.loads((BASE/'integration_hashes.json').read_text())
    for path,value in hashes['protected_inputs'].items():
        assert sha(ROOT/path)==value, f'Protected input changed: {path}'
    for path,value in hashes['outputs'].items():
        assert sha(BASE/path)==value, f'Integration output changed: {path}'
    manifest=json.loads((BASE/'manifest.json').read_text())
    baseline=json.loads((BASE/'slither_baseline.json').read_text())
    targets=json.loads((BASE/'verification_targets.json').read_text())
    assert not manifest['primary_20_case_subset_frozen']
    assert manifest['actual_subset_size']==len(manifest['records'])==1
    assert manifest['missing_case_count']==19
    assert baseline['manifest_sha256']==targets['manifest_sha256']==sha(BASE/'manifest.json')
    for record in manifest['records']:
        assert sha(ROOT/record['source_path'])==record['source_sha256']
    forbidden={'known_root_cause','ground_truth_label','expected_detector_family',
               'expected_verdict','attack_tx','independent_validation_notes'}
    for target in targets['technical_targets']:
        assert forbidden.isdisjoint(target)
        assert forbidden.isdisjoint(target['finding'])
        assert target['already_completed_pilot']
        assert sha(ROOT/target['source_path'])==target['source_sha256']
        assert target['slither_finding_id']==baseline['records'][0]['corresponding_finding']['finding_id']
    assert targets['new_paid_targets']==0
    assert baseline['metrics']['recall']==baseline['metrics']['detected']/baseline['metrics']['analyzable']
    assert baseline['llm_calls_made']==0
    print('PASS: protected input hashes, frozen integration hashes, source snapshots, target identity, metadata separation, pilot-only counts.')

if __name__=='__main__': main()
