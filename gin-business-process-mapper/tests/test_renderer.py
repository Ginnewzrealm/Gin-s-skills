import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_process import render_markdown


class RenderMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "tests/fixtures/order_process.json").read_text(encoding="utf-8"))

    def test_contains_required_sections(self):
        output = render_markdown(self.data)
        for heading in [
            "流程概况与范围", "参与角色与使用载体", "现状流程概览",
            "节点详细说明", "决策与异常处理", "状态变化", "软件实现含义",
            "产品待设计事项", "待确认问题", "事实来源与确认状态",
        ]:
            self.assertIn(heading, output)

    def test_contains_same_nodes_as_source(self):
        output = render_markdown(self.data)
        for node in self.data["nodes"]:
            self.assertIn(node["id"], output)
            self.assertIn(node["name"], output)

    def test_marks_inferred_and_unknown_content(self):
        output = render_markdown(self.data)
        self.assertIn("推导", output)
        self.assertIn("待确认", output)
        self.assertIn("软件实现含义", output)

    def test_contains_exceptions_and_sources(self):
        output = render_markdown(self.data)
        self.assertIn("客户不回复", output)
        self.assertIn("S01", output)


if __name__ == "__main__":
    unittest.main()
