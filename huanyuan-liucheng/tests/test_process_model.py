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

    def test_render_rejects_model_before_user_confirmation(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        model["confirmation"]["status"] = "pending"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_path = tmp_path / "pending-confirmation.json"
            output_dir = tmp_path / "rendered"
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("render", model_path, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 3)
            self.assertIn("用户确认", result.stderr)
            self.assertFalse(output_dir.exists())

    def test_validate_requires_process_boundary_fields(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del model["process"]["business_object"]

        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "missing-boundary.json"
            invalid.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("validate", invalid)

        self.assertEqual(result.returncode, 1)
        self.assertIn("process.business_object", result.stderr)

    def test_validate_requires_owner_for_every_action(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        action = next(node for node in model["nodes"] if node["type"] == "action")
        del action["owner"]

        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "missing-owner.json"
            invalid.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("validate", invalid)

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"{action['id']}.owner", result.stderr)

    def test_validate_rejects_duplicate_question_id_and_unknown_related_node(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        model["pending_questions"][1]["id"] = "Q01"
        model["pending_questions"][1]["related_nodes"] = ["D99"]

        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "invalid-questions.json"
            invalid.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("validate", invalid)

        self.assertEqual(result.returncode, 1)
        self.assertIn("待确认问题 id 重复", result.stderr)
        self.assertIn("D99", result.stderr)

    def test_validate_accepts_decision_with_four_branches(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        decision = next(node for node in model["nodes"] if node["id"] == "D03")
        decision["branches"].extend(
            [
                {
                    "label": "风险等级二",
                    "condition": "触发等级二风险条件",
                    "target": "U02",
                    "status": "unresolved",
                    "primary": False,
                },
                {
                    "label": "风险等级三",
                    "condition": "触发等级三风险条件",
                    "target": "U03",
                    "status": "unresolved",
                    "primary": False,
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "four-branches.json"
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("validate", model_path)

        self.assertEqual(result.returncode, 0, result.stderr)

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
