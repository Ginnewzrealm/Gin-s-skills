import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_process import _layout_nodes, render_html, render_markdown


class RenderMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "tests/fixtures/order_process.json").read_text(encoding="utf-8"))

    def test_contains_required_sections(self):
        output = render_markdown(self.data)
        for heading in [
            "流程概况与范围", "参与角色与使用载体", "场景流程",
            "软件操作与状态变化", "产品待设计及待确认事项",
            "事实来源与确认状态", "节点明细附录",
        ]:
            self.assertIn(heading, output)

    def test_renders_spacious_scenario_tree_with_roles(self):
        output = render_markdown(self.data)
        self.assertLess(output.index("正常接单"), output.index("订单信息异常确认"))
        for text in ["场景一", "◇", "├─", "└─", "岗位角色", "软件位置", "软件操作", "状态变化"]:
            self.assertIn(text, output)
        self.assertIn("主责：客服", output)
        self.assertNotIn("执行者", output)

    def test_does_not_duplicate_pending_sections(self):
        output = render_markdown(self.data)
        self.assertEqual(output.count("## 5. 产品待设计及待确认事项"), 1)
        self.assertNotIn("## 9. 待确认问题", output)

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


class RenderHtmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "tests/fixtures/order_process.json").read_text(encoding="utf-8"))
        cls.template = (ROOT / "assets/process-report-template.html").read_text(encoding="utf-8")
        cls.rework_data = json.loads((ROOT / "tests/fixtures/rework_process.json").read_text(encoding="utf-8"))

    def test_rework_layout_terminates(self):
        levels, rows = _layout_nodes(self.rework_data)
        self.assertEqual(set(levels), {"N01", "N02", "N03"})
        self.assertEqual(set(rows), {"N01", "N02", "N03"})

    def test_contains_svg_nodes_and_details(self):
        output = render_html(self.data, self.template)
        self.assertIn("<svg", output)
        self.assertIn("流程说明", output)
        for node in self.data["nodes"]:
            self.assertIn(f'data-node="{node["id"]}"', output)
            self.assertIn(f'id="detail-{node["id"]}"', output)

    def test_is_offline_and_escapes_user_text(self):
        data = copy.deepcopy(self.data)
        data["nodes"][0]["business_fact"] = "客户输入 <script>alert(1)</script>"
        output = render_html(data, self.template)
        self.assertNotIn("<script>alert(1)</script>", output)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", output)
        self.assertNotRegex(output, r"https?://")

    def test_includes_accessible_and_responsive_styles(self):
        output = render_html(self.data, self.template)
        self.assertIn('tabindex="0"', output)
        self.assertIn("@media(max-width:", output)
        self.assertIn("@media print", output)
        self.assertIn("prefers-reduced-motion", output)

    def test_marks_fact_inference_and_open_questions(self):
        output = render_html(self.data, self.template)
        self.assertIn("已确认事实", output)
        self.assertIn("软件实现含义", output)
        self.assertIn("产品待设计事项", output)

    def test_renders_scene_tabs_decision_shape_and_software_details(self):
        output = render_html(self.data, self.template)
        self.assertIn('class="scene-tab', output)
        self.assertIn('class="scene-panel', output)
        self.assertIn('class="decision-shape"', output)
        self.assertIn("岗位角色", output)
        self.assertIn("软件位置", output)
        self.assertIn("软件操作", output)
        self.assertIn("print-all-scenes", output)


if __name__ == "__main__":
    unittest.main()
