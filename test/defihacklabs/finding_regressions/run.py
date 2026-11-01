"""Compile immutable original sources and a test-only internal-function adapter."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
COMP=ROOT/'.venv/.solc-select/artifacts'
SOURCES={'LedgerChannel.sol':ROOT/'examples/defihacklabs/SpankChain.sol',
         'Victim.sol':ROOT/'examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol',
         'Eleven.sol':ROOT/'examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compile(version,sources):
 request={'language':'Solidity','sources':{k:{'content':v} for k,v in sources.items()},'settings':{'optimizer':{'enabled':True,'runs':200},'outputSelection':{'*':{'*':['evm.bytecode']}}}}
 result=subprocess.run([str(COMP/f'solc-{version}'/f'solc-{version}'),'--standard-json'],input=json.dumps(request),text=True,capture_output=True,check=True)
 data=json.loads(result.stdout)
 assert not [e for e in data.get('errors',[]) if e['severity']=='error'],data.get('errors')
 return data['contracts']
def main():
 hashes={k:sha(p) for k,p in SOURCES.items()}
 legacy=compile('0.4.25',{'LedgerChannel.sol':SOURCES['LedgerChannel.sol'].read_text(),
   'Probe.sol':'pragma solidity ^0.4.23; import "LedgerChannel.sol"; contract ProofProbe is LedgerChannel { function check(bytes32 leaf, bytes proof, bytes32 root) public pure returns(bool) { return _isContained(leaf,proof,root); } }'})
 pool=compile('0.6.8',{'Victim.sol':SOURCES['Victim.sol'].read_text(), 'PaymentProbe.sol':(HERE/'fixtures/PaymentProbe.sol.txt').read_text()})
 reward=compile('0.6.12',{'Eleven.sol':SOURCES['Eleven.sol'].read_text(), 'RewardProbe.sol':(HERE/'fixtures/RewardProbe.sol.txt').read_text()})
 proof=legacy['Probe.sol']['ProofProbe']['evm']['bytecode'];binary=proof['object'];offsets=[]
 for libs in proof['linkReferences'].values():
  for name,refs in libs.items():
   assert name=='ECTools'
   for r in refs:
    assert r['length']==20
    offset=r['start'];offsets.append(offset);binary=binary[:offset*2]+'00'*20+binary[(offset+20)*2:]
 artifact=dict(library='0x'+legacy['LedgerChannel.sol']['ECTools']['evm']['bytecode']['object'],proof='0x'+binary,offsets=offsets,pool='0x'+pool['Victim.sol']['Pool']['evm']['bytecode']['object'],source_hashes=hashes, payment='0x'+pool['PaymentProbe.sol']['PaymentProbe']['evm']['bytecode']['object'], reward='0x'+reward['RewardProbe.sol']['RewardProbe']['evm']['bytecode']['object'])
 generated=HERE/'.generated';generated.mkdir(exist_ok=True)
 (generated/'contracts.json').write_text(json.dumps(artifact))
 result=subprocess.run(['forge','test','--root',str(HERE),'--use',str(COMP/'solc-0.8.24/solc-0.8.24'),'--offline','-vv',*sys.argv[1:]],cwd=ROOT)
 assert hashes=={k:sha(p) for k,p in SOURCES.items()}
 print('PASS: original source hashes unchanged:',json.dumps(hashes))
 return result.returncode
if __name__=='__main__':raise SystemExit(main())
