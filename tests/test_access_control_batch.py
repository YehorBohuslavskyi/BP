import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_access_control_batch import run_batch
from context_audit.dataset import DatasetContract, GroundTruthVulnerability


class BatchTests(unittest.TestCase):
    def run_case(self, responses):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "vulnerabilities.json").write_text("[]")
            path = root / "sample.sol"
            path.write_text("contract Sample {}\n")
            contract = DatasetContract("sample.sol", path, "0.4.24", [
                GroundTruthVulnerability("access_control", [1]),
                GroundTruthVulnerability("reentrancy", [1]),
            ])
            with patch("check_access_control_batch.load_smartbugs_curated", return_value=[contract]), \
                 patch("check_access_control_batch.subprocess.run", side_effect=responses), \
                 contextlib.redirect_stdout(io.StringIO()):
                report = run_batch(root, root / "out")
            self.assertTrue((root / "out/baseline.csv").is_file())
            self.assertEqual(json.loads((root / "out/baseline.json").read_text()), report)
            self.assertEqual(report["summary"]["ground_truth_total"], 1)
            return report

    def test_compiler_failure_is_unanalyzed_not_missed(self):
        report = self.run_case([subprocess.CalledProcessError(1, ["solc"])])
        self.assertEqual(report["summary"]["ground_truth_unanalyzed"], 1)
        self.assertEqual(report["summary"]["missed"], 0)
        self.assertIsNone(report["summary"]["recall"])
        self.assertIsNone(report["vulnerabilities"][0]["detected"])

    def test_invalid_json_is_failure(self):
        report = self.run_case([subprocess.CompletedProcess([], 0, "compiler", ""),
                                subprocess.CompletedProcess([], 0, "invalid json", "")])
        self.assertEqual(report["summary"]["failed_contracts"], 1)

    def test_only_selected_category_is_evaluated(self):
        report = self.run_case([subprocess.CompletedProcess([], 0, "compiler", ""),
                               subprocess.CompletedProcess([], 0, json.dumps({
                                   "success": True, "results": {"detectors": []}}), "")])
        self.assertEqual(report["summary"]["missed"], 1)
        self.assertEqual(report["summary"]["recall"], 0.0)
        self.assertEqual(report["vulnerabilities"][0]["matching_methods"], ["none"])
