import sys
import importlib.util
from pathlib import Path


_SKILL_DIR = Path(__file__).parent.parent
_SKILL_MD = _SKILL_DIR / "SKILL.md"

# 动态导入 stage_validator.py（保持与现有测试一致的导入方式）
_MODULE_DIR = _SKILL_DIR / "scripts"
_spec = importlib.util.spec_from_file_location(
    "stage_validator", _MODULE_DIR / "stage_validator.py"
)
stage_validator = importlib.util.module_from_spec(_spec)
sys.modules["stage_validator"] = stage_validator
_spec.loader.exec_module(stage_validator)

STAGE_TRANSITIONS = stage_validator.STAGE_TRANSITIONS
STAGE_REQUIRED_FIELDS = stage_validator.STAGE_REQUIRED_FIELDS


def _blocking_table_stages(content: str) -> set:
    """从 SKILL.md 的硬闸门表中提取所有 stage 名称。"""
    start = content.find("## 阶段路由与硬闸门")
    end = content.find("### stage 说明", start)
    assert start != -1, "找不到硬闸门表起始位置"
    assert end != -1, "找不到硬闸门表结束位置"
    section = content[start:end]
    stages = set()
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("|") and "stage" not in line:
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]
            if cells and cells[0] != "stage":
                stages.add(cells[0])
    return stages


def test_core_stages_include_human_review():
    content = _SKILL_MD.read_text(encoding="utf-8")
    required_stages = [
        "role_boundary",
        "outline_confirmed",
        "draft_revised",
        "finalized",
    ]
    for stage in required_stages:
        assert stage in content, f"stage {stage} missing from SKILL.md"


def test_core_stages_removed_polish_confirmed():
    content = _SKILL_MD.read_text(encoding="utf-8")
    assert "polish_confirmed" not in content, "polish_confirmed stage should be removed"


def test_blocking_table_includes_draft_revised_and_polished():
    """标题/润色相关阶段必须出现在硬闸门表中，否则主 skill 容易跳过。"""
    content = _SKILL_MD.read_text(encoding="utf-8")
    blocking_stages = _blocking_table_stages(content)
    assert "draft_revised" in blocking_stages, "draft_revised 必须出现在硬闸门表"
    assert "polished" in blocking_stages, "polished 必须出现在硬闸门表"


def test_title_flow_stage_transitions_are_enforced():
    """标题优化链路必须是顺序推进，不允许跳过。"""
    assert "draft_revised" in STAGE_TRANSITIONS["draft_written"]
    assert "polished" in STAGE_TRANSITIONS["draft_revised"]
    assert "titled" in STAGE_TRANSITIONS["polished"]


def test_stage_required_fields_match_title_flow_context():
    """stage_validator 的必填字段名必须和 context.md 实际字段一致。"""
    assert "draft_revised_path" in STAGE_REQUIRED_FIELDS["draft_revised"]
    assert "article_draft" not in STAGE_REQUIRED_FIELDS["draft_revised"]

    assert "polished_draft_path" in STAGE_REQUIRED_FIELDS["polished"]
    assert "draft_revised" not in STAGE_REQUIRED_FIELDS["polished"]

    assert "title_candidates" in STAGE_REQUIRED_FIELDS["titled"]
    assert "polished_draft" not in STAGE_REQUIRED_FIELDS["titled"]


def test_blocking_table_includes_init():
    """风格选择发生在 init 阶段，init 也必须是硬闸门，否则会被跳过。"""
    content = _SKILL_MD.read_text(encoding="utf-8")
    blocking_stages = _blocking_table_stages(content)
    assert "init" in blocking_stages, "init 必须出现在硬闸门表"


def test_selected_template_confirmed_is_enforced():
    """需要 selected_template 的阶段，必须确认 selected_template.confirmed = true。"""
    validate_stage_prerequisites = stage_validator.validate_stage_prerequisites

    unconfirmed_context = {
        "selected_template": {"id": "social-slice", "confirmed": False},
        "requirements": {},
        "narrative_protocol": {},
    }
    errors = validate_stage_prerequisites("clarify", unconfirmed_context)
    assert any("confirmed" in e for e in errors), "模板未确认时应报错"

    confirmed_context = {
        "selected_template": {"id": "social-slice", "confirmed": True},
        "requirements": {},
        "narrative_protocol": {},
    }
    errors = validate_stage_prerequisites("clarify", confirmed_context)
    assert not any("confirmed" in e for e in errors), "模板已确认时不应报 confirmed 错误"
