import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_process import lint, validate


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

    def test_decision_requires_decider_criteria_and_fallback(self):
        data = copy.deepcopy(self.fixture)
        del data["nodes"][1]["criteria"]
        self.assertTrue(any("criteria" in error for error in validate(data)))

    def test_decision_requires_two_distinct_conditions(self):
        data = copy.deepcopy(self.fixture)
        data["edges"][2]["condition"] = data["edges"][1]["condition"]
        self.assertTrue(any("不同条件" in error for error in validate(data)))

    def test_scene_rejects_missing_edge_reference(self):
        data = copy.deepcopy(self.fixture)
        data["scenes"][0]["edge_ids"].append("E99")
        self.assertTrue(any("E99" in error for error in validate(data)))

    def test_confirmed_process_requires_every_edge_in_a_scene(self):
        data = copy.deepcopy(self.fixture)
        data["scenes"][0]["edge_ids"].remove("E01")
        self.assertTrue(any("未归属场景" in error for error in validate(data)))

    def test_normal_cycle_is_rejected(self):
        data = copy.deepcopy(self.fixture)
        data["edges"].append({"id": "E05", "from": "N03", "to": "N01", "label": "返回", "condition": "重新开始", "kind": "normal", "evidence_status": "confirmed", "evidence_refs": ["S01"]})
        data["scenes"][0]["edge_ids"].append("E05")
        self.assertTrue(any("普通流程边不能形成循环" in error for error in validate(data)))

    def test_rework_cycle_is_allowed(self):
        data = json.loads((ROOT / "tests/fixtures/rework_process.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(data), [])

    def test_vague_business_wording_is_a_warning(self):
        data = copy.deepcopy(self.fixture)
        data["nodes"][2]["business_action"] = "处理一下"
        self.assertTrue(any("表达过于模糊" in warning for warning in lint(data)))


if __name__ == "__main__":
    unittest.main()
