"""Read-only local DAppSCAN discovery and explicit evaluation metadata."""
import json
import os
import re
from pathlib import Path

CATEGORIES = {'SWC-107': 'Reentrancy', 'SWC-104': 'Unchecked Call Return Value',
              'SWC-105': 'Unprotected Ether Withdrawal', 'SWC-115': 'Authorization through tx.origin',
              'SWC-112': 'Delegatecall to Untrusted Callee'}


class DAppSCAN:
    def __init__(self, root=None):
        value = root or os.environ.get('DAPPSCAN_ROOT')
        if not value:
            raise ValueError('Set DAPPSCAN_ROOT or select a local dataset path')
        self.root = Path(value).expanduser().resolve()
        self.base = self.root / 'DAppSCAN-source' if (self.root / 'DAppSCAN-source').is_dir() else self.root
        self.contracts = self.base / 'contracts'
        if not self.contracts.is_dir():
            raise ValueError('Expected DAppSCAN-source/contracts in the local checkout')

    def projects(self):
        return sorted(p.name for p in self.contracts.iterdir() if p.is_dir())

    def files(self, project):
        folder = (self.contracts / project).resolve()
        if not folder.is_relative_to(self.contracts.resolve()):
            raise ValueError('Invalid project path')
        return sorted(p.relative_to(self.contracts).as_posix() for p in folder.rglob('*.sol') if p.resolve().is_relative_to(self.contracts.resolve()))

    def source_path(self, file):
        path = (self.contracts / file).resolve()
        if not path.is_relative_to(self.contracts.resolve()) or path.suffix != '.sol' or not path.is_file():
            raise ValueError('Invalid Solidity file')
        return path

    def labels(self, file):
        """Parse JSON reports. Free-form locations are retained, never guessed as reliable lines."""
        project = Path(file).parts[0]
        labels = []
        directories = [self.base / name for name in ('SWCsource', 'SWC_source', 'SWC-source')]
        reports = []
        for folder in directories:
            mirrored = folder / Path(file).with_suffix('.json')
            if mirrored.is_file():
                reports.append(mirrored)
            elif (folder / project).is_dir():
                reports.extend((folder / project).rglob('*.json'))
            elif (folder / (project + '.json')).is_file():
                reports.append(folder / (project + '.json'))
        def walk(node, inherited_file=None):
            if isinstance(node, list):
                for item in node:
                    yield from walk(item, inherited_file)
            elif isinstance(node, dict):
                name = node.get('filePath', node.get('file', node.get('path', node.get('filename', inherited_file))))
                swc = node.get('swc_id', node.get('SWC', node.get('swc', node.get('category'))))
                if swc and name:
                    yield name, swc, node
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        yield from walk(value, key if key.endswith('.sol') else name)
        for report in reports:
            if project not in report.as_posix():
                continue
            data = json.loads(report.read_text())
            for name, swc, raw in walk(data):
                normalized = str(name).replace('\\', '/').lstrip('./').removeprefix('DAppSCAN-source/contracts/')
                if normalized != file and not file.endswith('/' + normalized):
                    continue
                match = re.search(r'(\d{3})', str(swc))
                if not match:
                    continue
                code = 'SWC-' + match[1]
                lines = raw.get('lines', [])
                line_text = str(raw.get('lineNumber', ''))
                if not lines and re.fullmatch(r'L?\d+(?:-L?\d+)?', line_text):
                    numbers = [int(n) for n in re.findall(r'\d+', line_text)]
                    lines = list(range(numbers[0], numbers[-1]+1))
                reliable = isinstance(lines, list) and all(isinstance(x, int) and x > 0 for x in lines)
                labels.append({'project': project, 'file': file, 'swc_id': code,
                    'category': CATEGORIES.get(code, ''), 'function': None if raw.get('function') in (None, '', 'N/A') else raw['function'],
                    'lines': lines if reliable else [], 'report': str(report.relative_to(self.base)),
                    'audit_description': raw.get('description', ''), 'audit_reports': [str(p.relative_to(self.base)) for p in (self.base / 'audit_report' / project).glob('*.pdf')], 'raw': raw})
        return labels

    def cases(self):
        return [{'project': project, 'file': file, 'labels': self.labels(file)}
                for project in self.projects() for file in self.files(project)]


def select_pilot(cases, per_category=3):
    selected = {}
    for swc in CATEGORIES:
        candidates = sorted((c for c in cases if any(l['swc_id'] == swc for l in c['labels'])), key=lambda c: c['file'])
        for case in candidates[:per_category]:
            selected.setdefault(case['file'], {**case, 'selection_reason': 'Lexicographically first three source cases per prespecified SWC; before inference'})
    return list(selected.values())
