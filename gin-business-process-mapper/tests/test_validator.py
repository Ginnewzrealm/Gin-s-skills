import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_process import validate


class ValidateProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "tests/fixtures/order_process.json").read_text(encoding="utf-8"))

    def test_valid_process_has_no_errors(self):
        self.assertEqual(validate(copy.deepcopy(self.fixture)), [])

    def test_rejects_duplicate_node_ids(self):
        data = copy.deepcopy(self.fixture)
        data["nodes"][1]["id"] = "N01"
        self.assertTrue(any("重复" in error for error in validate(data)))

    def test_rejects_edge_to_missing_node(self):
        data = copy.deepcopy(self.fixture)
        data["edges"][0]["to"] = "N99"
        self.assertTrue(any("N99" in error for error in validate(data)))

    def test_rejects_missing_scope_boundary(self):
        data = copy.deepcopy(self.fixture)
        data["scope_end"] = ""
        self.assertTrue(any("scope_end" in error for error in validate(data)))

    def test_rejects_invalid_evidence_status(self):
        data = copy.deepcopy(self.fixture)
        data["nodes"][0]["evidence_status"] = "probably"
        self.assertTrue(any("evidence_status" in error for error in validate(data)))

    def test_confirmed_fact_requires_evidence_reference(self):
        data = copy.deepcopy(self.fixture)
        data["nodes"][0]["evidence_refs"] = []
        self.assertTrue(any("evidence_refs" in error for error in validate(data)))

    def test_node_ids_must_be_continuous(self):
        data = copy.deepcopy(self.fixture)
        data["nodes"][2]["id"] = "N09"
        self.assertTrue(any("连续" in error for error in validate(data)))


if __name__ == "__main__":
    unittest.main()
