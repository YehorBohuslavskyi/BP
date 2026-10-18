import tempfile
import unittest
from pathlib import Path

from context_audit.dataset import DatasetContract, GroundTruthVulnerability
from context_audit.evaluation import (
    _source_range_to_lines, evaluate_ground_truth_detection,
    match_findings_to_ground_truth, EvaluationMatch,
)
from context_audit.findings import parse_slither_findings


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "test.sol"
        self.path.write_bytes(b"// UTF-8: \xc3\xa9\nfunction f() {\n  unsafe();\n  other();\n}\n")
        self.contract = DatasetContract("test.sol", self.path, "0.4.24", [])

    def mapping(self, first, last=None, empty=False, path=None):
        chunks = self.path.read_bytes().splitlines(keepends=True)
        last = last or first
        return {"filename_absolute": str(path or self.path),
                "start": sum(map(len, chunks[:first-1])),
                "length": sum(map(len, chunks[first-1:last])),
                "lines": [] if empty else list(range(first, last+1))}

    def element(self, kind, first, last=None, empty=False, path=None):
        return {"type": kind, "source_mapping": self.mapping(first, last, empty, path)}

    def match(self, elements, gt, detector="suicidal"):
        self.contract.vulnerabilities = [GroundTruthVulnerability("access_control", [gt])]
        findings = parse_slither_findings({"success": True, "results": {"detectors": [
            {"check": detector, "elements": elements, "id": "test"}]}})
        return match_findings_to_ground_truth(self.contract, findings)[0]

    def test_contract_range_never_matches(self):
        self.assertFalse(self.match([self.element("contract", 1, 5)], 3))

    def test_node_over_function_even_when_node_lines_empty(self):
        function = self.element("function", 2, 5)
        node = self.element("node", 3, empty=True)
        node["type_specific_fields"] = {"parent": function}
        self.assertFalse(self.match([function, node], 4))
        self.assertEqual(self.match([function, node], 3)[0].finding_lines, [3])

    def test_old_function_offsets_remain_supported(self):
        function = self.element("function", 2, 5, empty=True)
        function["source_mapping"]["filename_absolute"] = ""
        self.assertEqual(self.match([function], 2)[0].matching_method, "exact_line")

    def test_function_scope_is_opt_in(self):
        node = self.element("node", 3)
        node["type_specific_fields"] = {"parent": self.element("function", 2, 5)}
        self.assertFalse(self.match([node], 4))
        self.assertEqual(self.match([node], 4, "controlled-array-length")[0].matching_method,
                         "function_scope")

    def test_other_file_does_not_match(self):
        self.assertFalse(self.match([self.element("node", 3, path=self.path.with_name("other.sol"))], 3))

    def test_node_priority_is_preserved_across_files(self):
        self.assertFalse(self.match([self.element("function", 2, 5),
                                    self.element("node", 3, path=self.path.with_name("other.sol"))], 3))

    def test_category_compatibility_required(self):
        self.assertFalse(self.match([self.element("node", 3)], 3, "unchecked-lowlevel"))

    def test_half_open_utf8_byte_range(self):
        mapping = self.mapping(3, empty=True)
        self.assertEqual(_source_range_to_lines(self.contract, mapping["start"], mapping["length"]), [3])
        self.assertEqual(_source_range_to_lines(self.contract, 0, 9999), [])

    def test_gt_annotations_do_not_leak_matches(self):
        self.contract.vulnerabilities = [GroundTruthVulnerability("access_control", [3]),
                                         GroundTruthVulnerability("access_control", [3, 4])]
        match = EvaluationMatch("access_control", [3], "suicidal", [3], [3])
        results = evaluate_ground_truth_detection(self.contract, [match])
        self.assertEqual([r.detected for r in results], [True, False])


if __name__ == "__main__":
    unittest.main()
