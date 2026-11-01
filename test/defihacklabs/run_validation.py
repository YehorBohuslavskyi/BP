#!/usr/bin/env python3
"""Compile unchanged 0.4.25 victim, then run modern Foundry tests on that bytecode.

No RPC, downloads, model calls, or writes to existing experiment artifacts.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SUITE = Path(__file__).resolve().parent
SOURCE = ROOT / 'examples/defihacklabs/SpankChain.sol'
EXPECTED_SHA = '501119bb522ddd4fe4fd7b08f4f9591d2197991b53aba06f9bb50ac4362f56a0'


def main():
    content = SOURCE.read_bytes()
    assert hashlib.sha256(content).hexdigest() == EXPECTED_SHA, 'Original source changed'
    generated = SUITE / '.generated'
    generated.mkdir(exist_ok=True)
    compiler_root = ROOT / '.venv/.solc-select/artifacts'
    old = compiler_root / 'solc-0.4.25/solc-0.4.25'
    modern = compiler_root / 'solc-0.8.24/solc-0.8.24'
    for compiler in (old, modern):
        assert compiler.is_file(), f'Local compiler required: {compiler}'
    request = {'language': 'Solidity', 'sources': {'SpankChain.sol': {'content': content.decode()},
                          'HistoricalMutabilityControl.sol': {'content': (SUITE / 'fixtures/HistoricalMutabilityControl.sol.txt').read_text()}},
               'settings': {'optimizer': {'enabled': True, 'runs': 200}, 'evmVersion': 'byzantium',
                            'outputSelection': {'*': {'*': ['evm.bytecode', 'abi']}}}}
    process = subprocess.run([str(old), '--standard-json'], input=json.dumps(request),
                             text=True, capture_output=True, check=True)
    result = json.loads(process.stdout)
    errors = [item for item in result.get('errors', []) if item['severity'] == 'error']
    assert not errors, errors
    contracts = result['contracts']['SpankChain.sol']
    ledger = contracts['LedgerChannel']['evm']['bytecode']
    offsets = []
    binary = ledger['object']
    for file, libraries in ledger['linkReferences'].items():
        for name, references in libraries.items():
            assert file == 'SpankChain.sol' and name == 'ECTools'
            for ref in references:
                assert ref['length'] == 20
                offset = ref['start']
                offsets.append(offset)
                binary = binary[:offset*2] + '00'*20 + binary[(offset+20)*2:]
    assert offsets and re.fullmatch('[0-9a-fA-F]+', binary)
    artifact = {'libraryCreation': '0x' + contracts['ECTools']['evm']['bytecode']['object'],
                'ledgerCreation': '0x' + binary, 'libraryLinkOffsets': offsets,
                'tokenCreation': '0x' + contracts['HumanStandardToken']['evm']['bytecode']['object'],
                'mutabilityControlCreation': '0x' + result['contracts']['HistoricalMutabilityControl.sol']['HistoricalMutabilityControl']['evm']['bytecode']['object'],
                'source_sha256': EXPECTED_SHA}
    (generated / 'legacy.json').write_text(json.dumps(artifact))
    (generated / 'compiler_output.json').write_text(json.dumps(result))
    print('Original source SHA-256:', EXPECTED_SHA, flush=True)
    print('Victim compiled unchanged with solc 0.4.25; standard ECTools linking at deployment.', flush=True)
    completed = subprocess.run(['forge', 'test', '--root', str(SUITE), '--use', str(modern),
                                '--offline', '-vv', *sys.argv[1:]], cwd=ROOT)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
