import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "stage_validator", _MODULE_DIR / "stage_validator.py"
)
stage_validator = importlib.util.module_from_spec(_spec)
sys.modules["stage_validator"] = stage_validator
_spec.loader.exec_module(stage_validator)

validate_stage_transition = stage_validator.validate_stage_transition
validate_stage_prerequisites = stage_validator.validate_stage_prerequisites
validate_template_whitelist = stage_validator.validate_template_whitelist
validate_narrative_protocol = stage_validator.validate_narrative_protocol
validate_next_step = stage_validator.validate_next_step
validate_sub_skill_execution = stage_validator.validate_sub_skill_execution
is_hard_gate = stage_validator.is_hard_gate


def test_valid_stage_transition():
    errors = validate_stage_transition("outline_selected", "outline_confirmed")
    assert errors == []


def test_invalid_stage_transition():
    errors = validate_stage_transition("outline_selected", "draft_written")
    assert len(errors) > 0
    assert "非法阶段转换" in errors[0]


def test_unknown_current_stage():
    errors = validate_stage_transition("not_a_stage", "init")
    assert len(errors) > 0
    assert "未知当前阶段" in errors[0]


def test_stage_prerequisites_missing_field():
    errors = validate_stage_prerequisites("clarify", {})
    assert any("selected_template" in err for err in errors)


def test_stage_prerequisites_satisfied():
    context = {"selected_template": {"id": "shangye-guancha", "confirmed": True}}
    errors = validate_stage_prerequisites("clarify", context)
    assert errors == []


def test_stage_prerequisites_template_not_confirmed():
    context = {"selected_template": {"id": "shangye-guancha", "confirmed": False}}
    errors = validate_stage_prerequisites("clarify", context)
    assert any("confirmed" in err for err in errors)


def test_validate_template_whitelist_allowed():
    templates = [{"id": "shangye-guancha"}, {"id": "renwu-xushi"}]
    errors = validate_template_whitelist("shangye-guancha", templates)
    assert errors == []


def test_validate_template_whitelist_denied():
    templates = [{"id": "shangye-guancha"}]
    errors = validate_template_whitelist("fake", templates)
    assert len(errors) > 0
    assert "不在白名单内" in errors[0]


def test_validate_narrative_protocol_fully_loaded():
    protocol = {
        "fully_loaded": True,
        "sections": [{"name": "开头"}],
    }
    errors = validate_narrative_protocol(protocol)
    assert errors == []


def test_validate_narrative_protocol_not_fully_loaded():
    protocol = {
        "fully_loaded": False,
        "completeness_errors": ["缺少结构参考"],
        "sections": [],
    }
    errors = validate_narrative_protocol(protocol)
    assert any("缺少结构参考" in err for err in errors)


def test_validate_next_step_combined():
    context = {
        "selected_template": {"id": "shangye-guancha", "confirmed": True},
        "requirements": {"topic": "test"},
        "narrative_protocol": {"fully_loaded": True, "sections": [{"name": "开头"}]},
    }
    templates = [{"id": "shangye-guancha"}]
    errors = validate_next_step("clarify", "template_loaded", context, templates)
    assert errors == []


def test_validate_sub_skill_execution_missing_keys():
    context = {"selected_template": {"confirmed": True}, "requirements": {}, "narrative_protocol": {}}
    errors = validate_sub_skill_execution("role_boundary", context)
    assert any("angle_candidates" in err for err in errors)
    assert any("diagnosis_report" in err for err in errors)


def test_validate_sub_skill_execution_missing_output_file(tmp_path):
    context = {
        "selected_template": {"confirmed": True},
        "requirements": {},
        "narrative_protocol": {},
        "angle_candidates": [{"id": "A1"}],
        "diagnosis_report": {"summary": "..."},
    }
    errors = validate_sub_skill_execution("role_boundary", context, article_dir=tmp_path)
    assert any("reports/diagnosis_report.md" in err for err in errors)


def test_validate_sub_skill_execution_with_empty_file(tmp_path):
    (tmp_path / "reports").mkdir()
    report_path = tmp_path / "reports" / "diagnosis_report.md"
    report_path.write_text("", encoding="utf-8")

    context = {
        "selected_template": {"confirmed": True},
        "requirements": {},
        "narrative_protocol": {},
        "angle_candidates": [{"id": "A1"}],
        "diagnosis_report": {"summary": "..."},
    }
    errors = validate_sub_skill_execution("role_boundary", context, article_dir=tmp_path)
    assert any("为空" in err for err in errors)


def test_validate_sub_skill_execution_with_existing_file(tmp_path):
    (tmp_path / "reports").mkdir()
    report_path = tmp_path / "reports" / "diagnosis_report.md"
    report_path.write_text("# diagnosis", encoding="utf-8")

    context = {
        "selected_template": {"confirmed": True},
        "requirements": {},
        "narrative_protocol": {},
        "angle_candidates": [{"id": "A1"}],
        "diagnosis_report": {"summary": "..."},
    }
    errors = validate_sub_skill_execution("role_boundary", context, article_dir=tmp_path)
    assert errors == []


def test_is_hard_gate():
    assert is_hard_gate("role_boundary") is True
    assert is_hard_gate("template_loaded") is False


def test_validate_next_step_detects_skipped_sub_skill(tmp_path):
    (tmp_path / "context.md").write_text("---\n---\n", encoding="utf-8")
    context = {
        "selected_template": {"id": "shangye-guancha", "confirmed": True},
        "requirements": {},
        "narrative_protocol": {"fully_loaded": True, "sections": [{"name": "开头"}]},
    }
    errors = validate_next_step(
        "angle_diagnosed", "role_boundary", context, article_dir=tmp_path
    )
    assert any("gin-wechat-article-angle" in err for err in errors)
