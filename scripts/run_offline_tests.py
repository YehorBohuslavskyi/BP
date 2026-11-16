"""Run unittest locally with model clients/network and research writes blocked."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def forbidden(*args,**kwargs):
    raise AssertionError('Offline tests forbid network and real model clients')


def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):
        forbidden()
    if event=='open' and isinstance(args[0],(str,bytes)):
        target=Path(os.fsdecode(args[0])).resolve()
        mode=args[1] or ''
        flags=args[2] or 0
        writing=any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)
        if writing and any(target.is_relative_to(ROOT/p) for p in ('runs','experiments','docs/reviews')):
            raise AssertionError('Preserved research evidence is read-only')
    if event=='subprocess.Popen':
        name=Path(os.fsdecode(args[0])).name.lower()
        if name.removesuffix('.exe') in ('codex','curl','wget','pip','pip3','npm','npx','ssh','scp'):
            forbidden()


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('tests',nargs='*',help='Optional unittest module/class names')
    parser.add_argument('--report',type=Path,help='Write a fresh JSON result outside preserved research folders')
    args=parser.parse_args()
    os.chdir(ROOT)
    os.environ['VIRTUAL_ENV']=str(ROOT/'.venv')
    os.environ['PATH']=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    sys.dont_write_bytecode=True
    sys.addaudithook(audit)
    with patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden), \
         patch('socket.create_connection',forbidden),patch('openai.OpenAI.__init__',forbidden), \
         patch('openai.AsyncOpenAI.__init__',forbidden),patch('openai.AzureOpenAI.__init__',forbidden), \
         patch('openai.AsyncAzureOpenAI.__init__',forbidden):
        suite=(unittest.defaultTestLoader.loadTestsFromNames(args.tests) if args.tests
               else unittest.defaultTestLoader.discover('tests'))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        data=dict(ran=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                  skipped=len(result.skipped),successful=result.wasSuccessful(),network_and_model_clients_blocked=True)
        with args.report.open('x') as stream:
            json.dump(data,stream,indent=2)
            stream.write('\n')
    return int(not result.wasSuccessful())


if __name__=='__main__':
    raise SystemExit(main())
