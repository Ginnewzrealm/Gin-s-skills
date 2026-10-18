import copy
import json
import sys
import unittest
import re
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
        self.assertIn("# 订单处理流程", output)
        self.assertIn("### 场景一：正常接单", output)
        self.assertNotIn("## 1.", output)
        self.assertNotIn("|---", output)

    def test_renders_spacious_scenario_tree_with_roles(self):
        output = render_markdown(self.data)
        self.assertLess(output.index("正常接单"), output.index("订单信息异常确认"))
        for text in ["场景一", "◇", "└─"]:
            self.assertIn(text, output)
        self.assertNotIn("主责：客服", output)

    def test_tree_contains_node_names_and_decision_details(self):
        output = render_markdown(self.data)
        self.assertIn("核对订单信息", output)
        self.assertNotIn("判断人：", output)
        self.assertIn("→ 闭环", output)

    def test_empty_carrier_name_has_no_empty_parentheses(self):
        data = copy.deepcopy(self.data)
        data["nodes"][0]["software_location"] = ""
        data["nodes"][0]["carrier"] = "onsite"
        data["nodes"][0]["carrier_name"] = ""
        self.assertNotIn("线下现场（）", render_markdown(data))

    def test_does_not_duplicate_pending_sections(self):
        output = render_markdown(self.data)
        self.assertNotIn("产品待设计", output)
        self.assertNotIn("待确认问题", output)

    def test_contains_same_nodes_as_source(self):
        output = render_markdown(self.data)
        for node in self.data["nodes"]:
            self.assertIn(node["software_operation"] or node["business_action"], output)

    def test_marks_inferred_and_unknown_content(self):
        output = render_markdown(self.data)
        self.assertNotIn("软件实现含义", output)
        self.assertNotIn("事实来源", output)

    def test_contains_exceptions_and_sources(self):
        output = render_markdown(self.data)
        self.assertIn("发送问题说明并等待客户回复", output)
        self.assertNotIn("S01", output)

    def test_markdown_contains_rules_and_evidence_references(self):
        output = render_markdown(self.data)
        self.assertNotIn("证据引用", output)
        self.assertNotIn("业务规则", output)

    def test_scene_tree_uses_vertical_action_flow(self):
        output = render_markdown(self.data)
        scene_tree = output.split("### 场景一：正常接单", 1)[1].split("```", 2)[1]
        self.assertIn("│\n▼", scene_tree)
        self.assertNotIn(" → ", scene_tree.replace(" → 闭环", ""))
        self.assertIn("客服在「订单平台／订单详情」打开订单详情并查看商品、地址和备注", scene_tree)
        self.assertIn("客服在「订单平台／订单详情」点击「确认接单」", scene_tree)
        self.assertIn("└─", scene_tree)

    def test_decision_branch_and_target_are_on_separate_lines(self):
        output = render_markdown(self.data)
        self.assertNotRegex(output, r"├─[^\n]+→[^\n]+")
        self.assertNotRegex(output, r"└─[^\n]+→[^\n]+")


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

    def test_layout_finds_scene_root_when_first_node_is_unrelated(self):
        data = copy.deepcopy(self.data)
        edges = [data["edges"][1], data["edges"][2]]
        data["nodes"] = [data["nodes"][0], data["nodes"][1], data["nodes"][2], data["nodes"][3]]
        data["edges"] = edges
        levels, rows = _layout_nodes(data)
        self.assertEqual(levels["N03"], levels["N04"])
        self.assertNotEqual(rows["N03"], rows["N04"])
        self.assertLessEqual(max(levels.values()) - min(levels.values()) + 1, 6)

    def test_contains_svg_nodes_without_detail_tables(self):
        output = render_html(self.data, self.template)
        self.assertIn("<svg", output)
        for node in self.data["nodes"]:
            self.assertIn(f'data-node="{node["id"]}"', output)
        self.assertNotIn('id="detail-', output)
        self.assertNotIn("<table", output)

    def test_is_offline_and_escapes_user_text(self):
        data = copy.deepcopy(self.data)
        data["nodes"][0]["name"] = "客户输入 <script>alert(1)</script>"
        output = render_html(data, self.template)
        self.assertNotIn("<script>alert(1)</script>", output)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", output)
        self.assertNotRegex(output, r"https?://")

    def test_includes_accessible_and_responsive_styles(self):
        output = render_html(self.data, self.template)
        self.assertIn('role="img"', output)
        self.assertIn("@media(max-width:", output)
        self.assertIn("@media print", output)
        self.assertIn("prefers-reduced-motion", output)

    def test_marks_fact_inference_and_open_questions(self):
        output = render_html(self.data, self.template)
        self.assertNotIn("软件实现含义", output)
        self.assertNotIn("产品待设计事项", output)

    def test_html_marks_draft_status(self):
        data = copy.deepcopy(self.data)
        data["status"] = "draft"
        output = render_html(data, self.template)
        self.assertNotIn('class="document-status draft"', output)

    def test_html_contains_sources_rules_and_edge_evidence(self):
        output = render_html(self.data, self.template)
        self.assertNotIn("事实来源", output)
        self.assertNotIn("<table", output)
        self.assertNotIn('<text class="node-id"', output)
        self.assertNotIn(">E01 ·", output)

    def test_long_svg_names_use_tspans(self):
        data = copy.deepcopy(self.data)
        data["nodes"][1]["name"] = "外观与尺寸是否全部符合验收标准"
        output = render_html(data, self.template)
        self.assertIn("<tspan", output)

    def test_renders_scene_tabs_decision_shape_and_software_details(self):
        output = render_html(self.data, self.template)
        self.assertIn('class="scene-tab', output)
        self.assertIn('class="scene-panel', output)
        self.assertIn('class="decision-shape"', output)
        self.assertIn("print-all-scenes", output)

    def test_html_decision_cards_include_decision_details(self):
        output = render_html(self.data, self.template)
        self.assertIn('class="decision-shape"', output)
        for text in ["判断人", "判断依据", "判不了怎么办"]:
            self.assertNotIn(text, output)

    def test_svg_ids_are_unique_across_scenes(self):
        output = render_html(self.data, self.template)
        ids = re.findall(r' id="([^"]+)"', output)
        self.assertEqual(len(ids), len(set(ids)))

    def test_normal_decision_target_is_not_marked_as_exception(self):
        output = render_html(self.data, self.template)
        match = re.search(r'<g class="([^"]+)" data-node="N03"', output)
        self.assertIsNotNone(match)
        self.assertNotIn("branch", match.group(1))

    def test_multiple_back_edges_have_separate_routes(self):
        data = copy.deepcopy(self.rework_data)
        edge = copy.deepcopy(data["edges"][2])
        edge["id"] = "E04"
        edge["from"] = "N03"
        edge["kind"] = "cancel"
        data["edges"].append(edge)
        data["scenes"][1]["edge_ids"].append("E04")
        output = render_html(data, self.template)
        paths = re.findall(r'<path class="connector (?:rework|cancel)" d="([^"]+)"', output)
        bottoms = [re.search(r'V([0-9.]+)H', path).group(1) for path in paths]
        self.assertEqual(len(bottoms), len(set(bottoms)))


if __name__ == "__main__":
    unittest.main()
