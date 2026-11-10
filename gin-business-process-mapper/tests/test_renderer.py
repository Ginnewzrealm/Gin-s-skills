import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_process import main, render_markdown


class RenderMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "tests/fixtures/order_process.json").read_text(encoding="utf-8"))

    def test_contains_only_title_scenes_and_flow_tree(self):
        output = render_markdown(self.data)
        self.assertIn("# 订单处理流程", output)
        self.assertIn("### 场景一：订单处理", output)
        self.assertNotIn("## 1.", output)
        self.assertNotIn("|---", output)
        self.assertNotIn("产品待设计", output)
        self.assertNotIn("事实来源", output)

    def test_renders_vertical_flow_tree(self):
        output = render_markdown(self.data)
        scene_tree = output.split("### 场景一：订单处理", 1)[1].split("```", 2)[1]
        self.assertIn("│\n▼", scene_tree)
        self.assertNotIn(" → ", scene_tree.replace(" → 闭环", ""))
        self.assertIn("客服在「订单平台／订单详情」打开订单详情并查看商品、地址和备注", scene_tree)
        self.assertIn("客服在「订单平台／订单详情」点击「确认接单」", scene_tree)
        self.assertIn("→ 闭环", scene_tree)

    def test_contains_every_decision_branch_in_one_scene(self):
        output = render_markdown(self.data)
        scene_tree = output.split("```text", 1)[1].split("```", 1)[0]
        self.assertIn("◇ 核对订单信息？", scene_tree)
        self.assertIn("├─ 正常（订单没有问题）", scene_tree)
        self.assertIn("└─ 有问题（订单信息需要确认）", scene_tree)
        self.assertIn("点击「确认接单」", scene_tree)
        self.assertIn("发送问题说明并等待客户回复", scene_tree)

    def test_decision_branch_and_target_are_on_separate_lines(self):
        output = render_markdown(self.data)
        self.assertNotRegex(output, r"├─[^\n]+→[^\n]+")
        self.assertNotRegex(output, r"└─[^\n]+→[^\n]+")

    def test_contains_each_node_operation(self):
        output = render_markdown(self.data)
        for node in self.data["nodes"]:
            self.assertIn(node["software_operation"] or node["business_action"], output)

    def test_empty_carrier_name_has_no_empty_parentheses(self):
        data = copy.deepcopy(self.data)
        data["nodes"][0]["software_location"] = ""
        data["nodes"][0]["carrier"] = "onsite"
        data["nodes"][0]["carrier_name"] = ""
        self.assertNotIn("线下现场（）", render_markdown(data))

    def test_cli_outputs_only_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            result = main([str(ROOT / "tests/fixtures/order_process.json"), "--output-dir", directory])
            files = sorted(path.name for path in Path(directory).iterdir())
        self.assertEqual(result, 0)
        self.assertEqual(files, ["订单处理流程-流程说明.md"])


if __name__ == "__main__":
    unittest.main()
