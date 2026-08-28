import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from progress_reporter import render_macro, render_micro, STAGE_TO_PHASE


def test_stage_to_phase_has_all_stages():
    expected = {
        "init", "clarify", "template_loaded", "angle_diagnosed", "role_boundary",
        "angle_matched", "outline_generated", "outline_selected", "outline_confirmed",
        "draft_written", "draft_revised", "polished", "titled", "title_confirmed",
        "quality_checked", "quality_failed", "finalized", "markdown_output", "publish_decision",
    }
    assert set(STAGE_TO_PHASE.keys()) == expected


def test_render_macro_shows_current_phase():
    result = render_macro(
        current_stage="outline_generated",
        completed_stages=["init", "clarify", "template_loaded", "angle_diagnosed", "role_boundary"],
        pending_stages=["outline_selected", "outline_confirmed", "draft_written", "draft_revised", "polished", "titled", "title_confirmed", "quality_checked", "finalized", "markdown_output", "publish_decision"],
        current_step="展示候选大纲",
        steps=[
            {"name": "读取 context.md 与 reference_briefs", "tags": ["自动"], "status": "done"},
            {"name": "为可用角度生成候选大纲", "tags": ["自动"], "status": "done"},
            {"name": "自检排序并标注风险点", "tags": ["自动"], "status": "done"},
            {"name": "展示候选大纲", "tags": ["需确认"], "status": "current"},
            {"name": "用户选择/修改大纲", "tags": ["硬闸门", "可回环"], "status": "pending"},
        ],
    )
    assert "阶段 3/6：大纲生成与确认" in result
    assert "展示候选大纲" in result
    assert "← 当前" in result
    assert "- [x]" in result
    assert "- [ ]" in result


def test_render_micro_with_phase_locator():
    result = render_micro(
        phase_name="阶段 3/6：大纲生成与确认",
        steps=[
            {"name": "读取 context.md 与 reference_briefs", "tags": ["自动"], "status": "pending"},
        ],
        current_step="读取 context.md 与 reference_briefs",
        show_phase_locator=True,
    )
    assert "当前处于公众号长文写作的阶段 3/6：大纲生成与确认" in result
    assert "读取 context.md 与 reference_briefs" in result


def test_render_micro_without_phase_locator():
    result = render_micro(
        phase_name="阶段 3/6：大纲生成与确认",
        steps=[
            {"name": "读取 context.md 与 reference_briefs", "tags": ["自动"], "status": "current"},
        ],
        current_step="读取 context.md 与 reference_briefs",
        show_phase_locator=False,
    )
    assert "当前处于公众号长文写作" not in result
    assert "阶段 3/6：大纲生成与确认" in result


def test_render_macro_completed_phases_marked():
    result = render_macro(
        current_stage="draft_written",
        completed_stages=["init", "clarify", "template_loaded", "angle_diagnosed", "role_boundary", "angle_matched", "outline_generated", "outline_selected", "outline_confirmed"],
        pending_stages=["draft_revised", "polished", "titled", "title_confirmed", "quality_checked", "finalized", "markdown_output", "publish_decision"],
        current_step="按章节逐段生成正文",
        steps=[
            {"name": "读取 selected_outline 与 narrative_protocol", "tags": ["自动"], "status": "done"},
            {"name": "按章节逐段生成正文", "tags": ["自动"], "status": "current"},
        ],
    )
    assert "阶段 1/6：初始化与需求澄清 [x]" in result
    assert "阶段 2/6：素材诊断与角度选择 [x]" in result
    assert "阶段 3/6：大纲生成与确认 [x]" in result
    assert "阶段 4/6：正文写作与人工改写" in result
    assert "阶段 5/6：润色、小标题与标题优化 [待开始]" in result
