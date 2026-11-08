import importlib.util
import json
import os
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
    def legacy_html(self, model):
        # Keep testing the retained HTML helper without making it a deliverable.
        sys.path.insert(0, str(ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("legacy_html_model", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.render_html(model)

    def model(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def validate_dict(self, model):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            return self.run_cli("validate", path)

    def test_confirmation_cannot_be_only_a_boolean_status(self):
        model = self.model()
        model["confirmation"] = {"status": "confirmed", "scope_summary": "直接生成"}
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confirmation.presented", result.stderr)

    def test_correction_reply_is_not_approval(self):
        model = self.model()
        model["confirmation"]["response_kind"] = "correction"
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("response_kind", result.stderr)

    def test_business_action_requires_traceable_evidence(self):
        model = self.model()
        action = next(n for n in model["nodes"] if n["type"] == "action")
        action["label"] = "收取订单金额百分之三的保证金"
        action["evidence_refs"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence_refs", result.stderr)

    def test_sequential_connection_requires_evidence(self):
        model = self.model()
        model["nodes"][0]["next_evidence_refs"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("next_evidence_refs", result.stderr)

    def test_unresolved_process_cannot_be_marked_confirmed(self):
        model = self.model()
        model["process"]["status"] = "confirmed"
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("process.status", result.stderr)

    def test_unknown_end_is_allowed_without_inventing_business_completion(self):
        model = self.model()
        terminal = next(n for n in model["nodes"] if n["type"] == "terminal")
        terminal["type"] = "unresolved"
        terminal["label"] = "后续去向未确认"
        model["pending_questions"].append({"id": "Q09", "text": "审核后实际交给谁？", "related_nodes": [terminal["id"], "J01"]})
        result = self.validate_dict(model)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_declared_return_to_review_is_allowed(self):
        model = self.model()
        node = next(n for n in model["nodes"] if n["id"] == "U01")
        node.update(type="action", owner="业务员", label="修改销售订单", next="A03", back_edge=True,
                    evidence_refs=["E_RETURN"], next_evidence_refs=["E_RETURN"])
        model.setdefault("source_materials", []).append({"id":"RETURN", "text":"主管拒绝后，业务员修改销售订单，再提交商务主管审核。"})
        model.setdefault("evidence", []).append({"id":"E_RETURN", "source_id":"RETURN", "quote":"主管拒绝后，业务员修改销售订单，再提交商务主管审核。", "kind":"current"})
        result = self.validate_dict(model)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_render_cannot_bypass_confirmation(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("tested_process_model", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model = self.model()
        model["confirmation"]["status"] = "pending"
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            with self.assertRaises(module.ModelError):
                module.render_files(model, output_dir)
            self.assertFalse(output_dir.exists())

    def test_quote_must_exist_in_recorded_source(self):
        model = self.model()
        model["evidence"][0]["quote"] = "原资料中没有这句话"
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quote", result.stderr)

    def test_expected_goal_cannot_support_current_action(self):
        model = self.model()
        model["evidence"][0]["kind"] = "goal"
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不能只用预期目标", result.stderr)

    def test_unknowns_need_user_acceptance_and_related_questions(self):
        model = self.model()
        model["confirmation"]["accepted_unknowns"] = False
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted_unknowns", result.stderr)
        model = self.model()
        model["pending_questions"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("必须关联待确认问题", result.stderr)

    def test_confirmation_reply_must_match_recorded_reply(self):
        model = self.model()
        model["confirmation"]["user_reply"] = "伪造的确认回复"
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("user_reply", result.stderr)

    def test_branch_requires_its_own_evidence(self):
        model = self.model()
        decision = next(n for n in model["nodes"] if n["type"] == "decision")
        decision["branches"][0]["evidence_refs"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branches[0].evidence_refs", result.stderr)

    def test_no_decisions_and_unknown_destination_can_render_as_draft(self):
        model = self.model()
        model["nodes"] = [
            {"id": "S01", "type": "start", "label": "客户提出采购需求", "next": "A01", "evidence_refs": ["E01"], "next_evidence_refs": ["E01"]},
            {"id": "A01", "type": "action", "owner": "业务员", "label": "填写销售订单", "next": "U01", "evidence_refs": ["E01"], "next_evidence_refs": []},
            {"id": "U01", "type": "unresolved", "label": "后续去向未确认"}
        ]
        model["pending_questions"] = [{"id": "Q01", "text": "填写订单后交给谁？", "related_nodes": ["A01", "U01"]}]
        model["confirmation"]["presented"]["decisions"] = []
        result = self.validate_dict(model)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            result = self.run_cli("render", path, "--output-dir", Path(tmp) / "output")
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (Path(tmp) / "output/03 销售订单-流程说明.md").read_text()
            self.assertNotIn("D01", content)
            self.assertIn("后续去向未确认", content)

    def test_join_cannot_invent_a_following_connection(self):
        model = self.model()
        join = next(n for n in model["nodes"] if n["type"] == "join")
        join["next_evidence_refs"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("J01.next_evidence_refs", result.stderr)

    def test_markdown_render_does_not_require_node_or_layout_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "rendered"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "render", str(FIXTURE), "--output-dir", str(output_dir)],
                env={**os.environ, "PATH": tmp}, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([p.suffix for p in output_dir.iterdir()], [".md"])

    def test_decisions_must_have_been_presented_before_approval(self):
        model = self.model()
        model["confirmation"]["presented"]["decisions"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("presented.decisions", result.stderr)

    def partial_decision_model(self, known_outcome=True):
        model = self.model()
        quote = "销售提交订单后，主管根据订单金额是否超过10万元决定是否批准。"
        if known_outcome:
            quote += "不超过10万元就批准，订单审批通过。"
        reply = "确认，按当前事实和已说明的判断出草案，未说明的分支先列问题。"
        model["source_materials"] = [{"id": "PARTIAL", "text": quote}, {"id": "APPROVAL", "text": reply}]
        model["evidence"] = [{"id": "E_PARTIAL", "source_id": "PARTIAL", "quote": quote, "kind": "current"}]
        model["confirmation"].update(user_reply=reply, user_reply_source_id="APPROVAL", presented={
            "current_facts": ["销售提交订单后，主管根据金额判断是否批准。"], "excluded_goals": [],
            "process_boundaries": ["订单提交到审批；未说明的结果保留待确认。"], "decisions": ["主管是否批准订单？"]
        })
        decision = {"id": "D01", "type": "decision", "owner": "主管", "title": "订单审批", "question": "主管是否批准订单？",
                    "evidence_refs": ["E_PARTIAL"], "inputs": ["订单金额"], "branches_complete": False,
                    "criteria": [{"text": "判断金额是否超过10万元", "status": "confirmed", "evidence": "访谈明确提到金额判断", "evidence_refs": ["E_PARTIAL"]}],
                    "branches": []}
        model["nodes"] = [
            {"id": "S01", "type": "start", "label": "销售提交订单", "next": "D01", "evidence_refs": ["E_PARTIAL"], "next_evidence_refs": ["E_PARTIAL"]},
            decision,
        ]
        if known_outcome:
            decision["branches"] = [{"label": "批准", "condition": "订单金额不超过10万元", "target": "T01", "primary": True,
                                      "condition_status": "confirmed", "target_status": "confirmed", "status": "confirmed", "evidence_refs": ["E_PARTIAL"]}]
            model["nodes"].append({"id": "T01", "type": "terminal", "label": "订单审批通过", "evidence_refs": ["E_PARTIAL"]})
        model["pending_questions"] = [{"id": "Q01", "text": "其他判断结果分别进入哪里？", "related_nodes": ["D01"]}]
        return model

    def test_partial_decision_preserves_only_known_branch_without_fabrication(self):
        model = self.partial_decision_model()
        result = self.validate_dict(model)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            output_dir = Path(tmp) / "output"
            result = self.run_cli("render", path, "--output-dir", output_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (output_dir / "03 销售订单-流程说明.md").read_text()
            html = self.legacy_html(model)
            self.assertIn("批准", markdown)
            self.assertIn("分支完整性：仅列已知结果；未说明的结果及去向待确认", markdown)
            self.assertNotIn("拒绝", markdown)
            self.assertNotIn("U01", markdown)
            self.assertEqual(html.count('data-edge-source="D01"'), 1)

    def test_known_decision_without_described_outcomes_is_draft_leaf(self):
        model = self.partial_decision_model(known_outcome=False)
        result = self.validate_dict(model)
        self.assertEqual(result.returncode, 0, result.stderr)
        sys.path.insert(0, str(ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("partial_process_model", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tree = module.render_tree(model)
        self.assertIn("D01 主管是否批准订单？", tree)
        self.assertNotIn("T01", tree)
        self.assertNotIn("U01", tree)
        model["process"]["status"] = "confirmed"
        model["pending_questions"] = []
        self.assertTrue(module.has_unresolved(model))
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("process.status", result.stderr)
        self.assertIn("必须关联待确认问题", result.stderr)

    def test_terminal_or_unknown_node_cannot_hide_outgoing_connections(self):
        for node_id, target in (("U01", "D02"), ("T01", "S01")):
            with self.subTest(node=node_id):
                model = self.model()
                next(n for n in model["nodes"] if n["id"] == node_id)["next"] = target
                result = self.validate_dict(model)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(node_id + ".next", result.stderr)
        model = self.model()
        next(n for n in model["nodes"] if n["id"] == "A01")["branches"] = []
        result = self.validate_dict(model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("A01.branches", result.stderr)

    def support_extra_branches(self, model, decision):
        quote = "风险还有等级二和等级三：触发等级二风险条件、触发等级三风险条件，各自后续去向未说明。"
        model["source_materials"].append({"id": "FOUR_BRANCHES", "text": quote})
        model["evidence"].append({"id": "E_FOUR", "source_id": "FOUR_BRANCHES", "quote": quote, "kind": "current"})
        for branch in decision["branches"][2:]:
            branch.update(evidence_refs=["E_FOUR"], condition_status="unresolved", target_status="unresolved")

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

        self.support_extra_branches(model, decision)

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

    def test_render_preserves_decisions_conditions_and_questions_in_one_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = self.run_cli("render", FIXTURE, "--output-dir", output_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output_dir / "03 销售订单-流程说明.md"
            self.assertEqual(list(output_dir.iterdir()), [markdown])
            text = markdown.read_text(encoding="utf-8")
            self.assertEqual(set(re.findall(r"\bD\d{2}\b", text)), {f"D0{i}" for i in range(1,6)})
            for value in ("客户账期是否符合公司规则？", "客户类型和申请账期符合公司现行规则", "满足老板审批触发规则", "Q08", "调整账期、退回或终止方式待确认"):
                self.assertIn(value, text)

    def test_render_separates_path_map_from_decision_details(self):
        model = self.model()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "rendered"
            result = self.run_cli("render", FIXTURE, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            html_text = self.legacy_html(model)
            flow_start = html_text.index('<section id="flow-map"')
            details_start = html_text.index('<section id="decision-details"')
            questions_start = html_text.index('<section id="pending-questions"')
            flow_text = html_text[flow_start:details_start]
            detail_text = html_text[details_start:questions_start]
            question_text = html_text[questions_start:]

            self.assertLess(flow_start, details_start)
            self.assertLess(details_start, questions_start)
            self.assertNotIn("判断信息", flow_text)
            self.assertNotIn("客户类型、客户申请账期、公司账期规则", flow_text)
            self.assertNotIn("自然语言资料中的两条规则存在适用范围歧义", flow_text)
            self.assertIn("判断信息", detail_text)
            self.assertIn("客户类型、客户申请账期、公司账期规则", detail_text)
            self.assertIn("自然语言资料中的两条规则存在适用范围歧义", detail_text)
            self.assertIn("Q01", question_text)
            self.assertIn("新客户现款现货", question_text)

    def test_render_shows_every_branch_and_merge_reference(self):
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

        self.support_extra_branches(model, decision)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_path = tmp_path / "four-branches.json"
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            output_dir = tmp_path / "rendered"
            result = self.run_cli("render", model_path, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            html_text = self.legacy_html(model)
            flow_start = html_text.index('<section id="flow-map"')
            details_start = html_text.index('<section id="decision-details"')
            flow_text = html_text[flow_start:details_start]
            for condition in (
                "未触发公司定义的高风险情形",
                "风险判断标准待确认",
                "触发等级二风险条件",
                "触发等级三风险条件",
            ):
                self.assertIn(condition, flow_text)
            self.assertIn('id="path-J01"', flow_text)
            self.assertEqual(flow_text.count('data-edge-target="J01"'), 2)
            markdown = (output_dir / "03 销售订单-流程说明.md").read_text(encoding="utf-8")
            tree = markdown.split('```text\n', 1)[1].split('\n```', 1)[0]
            for branch in decision['branches']:
                self.assertIn(branch['label'], tree)
                self.assertIn(branch['condition'], tree)
                self.assertIn(branch['target'], tree)
            self.assertEqual(markdown.count('```text'), 1)

    def test_question_links_target_existing_decision_and_path_anchors(self):
        model = json.loads(FIXTURE.read_text(encoding="utf-8"))
        model["pending_questions"].append(
            {
                "id": "Q09",
                "text": "提交、审批和汇合之间的交接关系是什么？",
                "related_nodes": ["A01", "D01", "J01"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_path = tmp_path / "mixed-question-links.json"
            model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            output_dir = tmp_path / "rendered"
            result = self.run_cli("render", model_path, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            html_text = self.legacy_html(model)
            self.assertIn('href="#path-A01"', html_text)
            self.assertIn('href="#detail-D01"', html_text)
            self.assertIn('href="#path-J01"', html_text)
            ids = set(re.findall(r'\bid="([^"]+)"', html_text))
            fragments = set(re.findall(r'href="#([^"]+)"', html_text))
            self.assertEqual(fragments - ids, set())

    def test_markdown_includes_confirmed_process_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = self.run_cli("render", FIXTURE, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown_text = (output_dir / "03 销售订单-流程说明.md").read_text(encoding="utf-8")
            self.assertIn("**流程边界**", markdown_text)
            self.assertIn("核心业务对象：销售订单", markdown_text)
            self.assertIn("触发事件：客户向业务员提出采购需求", markdown_text)
            self.assertIn("结束状态：销售订单审核完成，进入待履约状态", markdown_text)
            self.assertIn("仓储履约属于下游流程", markdown_text)


if __name__ == "__main__":
    unittest.main()
