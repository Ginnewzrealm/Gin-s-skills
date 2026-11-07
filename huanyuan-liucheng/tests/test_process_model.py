import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "process_model.py"
FIXTURE = ROOT / "tests" / "fixtures" / "sales-order.json"


class ProcessModelCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_validate_accepts_draft_and_reports_counts(self):
        result = self.run_cli("validate", FIXTURE)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5 个决策节点", result.stdout)
        self.assertIn("8 个待确认问题", result.stdout)

    def test_require_confirmed_rejects_unresolved_draft(self):
        result = self.run_cli("validate", FIXTURE, "--require-confirmed")

        self.assertEqual(result.returncode, 2)
        self.assertIn("仍含待确认内容", result.stderr)

    def test_validate_rejects_blank_branch_condition(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        decision = next(node for node in model["nodes"] if node["id"] == "D01")
        decision["branches"][1]["condition"] = ""

        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "invalid.json"
            invalid.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("validate", invalid)

        self.assertEqual(result.returncode, 1)
        self.assertIn("D01", result.stderr)
        self.assertIn("condition", result.stderr)

    def test_render_creates_consistent_markdown_html_and_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = self.run_cli("render", FIXTURE, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output_dir / "03 销售订单-流程说明.md"
            html = output_dir / "03 销售订单-决策路径图.html"
            questions = output_dir / "03 销售订单-待确认问题.md"
            self.assertTrue(markdown.is_file())
            self.assertTrue(html.is_file())
            self.assertTrue(questions.is_file())

            markdown_text = markdown.read_text(encoding="utf-8")
            html_text = html.read_text(encoding="utf-8")
            questions_text = questions.read_text(encoding="utf-8")

            expected_decisions = {f"D0{index}" for index in range(1, 6)}
            md_decisions = set(re.findall(r"\bD\d{2}\b", markdown_text))
            html_decisions = set(re.findall(r"\bD\d{2}\b", html_text))
            self.assertEqual(md_decisions, expected_decisions)
            self.assertEqual(html_decisions, expected_decisions)

            for required_text in (
                "客户账期是否符合公司规则？",
                "客户类型和申请账期符合公司现行规则",
                "满足老板审批触发规则",
                "待确认",
            ):
                self.assertIn(required_text, markdown_text)
                self.assertIn(required_text, html_text)

            self.assertIn("→ U01 · 调整账期、退回或终止方式待确认", html_text)
            self.assertIn("8 项", questions_text)
            self.assertNotRegex(html_text, r"https?://")

    def test_render_expands_decisions_that_are_not_on_primary_spine(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        route = next(node for node in model["nodes"] if node["id"] == "D04")
        route["branches"][0]["primary"] = False
        route["branches"][1]["primary"] = True

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_path = tmp_path / "branch-decision.json"
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            output_dir = tmp_path / "rendered"
            result = self.run_cli("render", model_path, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            html_text = (output_dir / "03 销售订单-决策路径图.html").read_text(encoding="utf-8")
            self.assertIn("分支决策展开", html_text)
            self.assertIn("D05 · 最终审批", html_text)
            self.assertIn("符合老板审批标准，具体标准待确认", html_text)
            self.assertIn("不符合老板审批标准，具体标准待确认", html_text)


if __name__ == "__main__":
    unittest.main()
