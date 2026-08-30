"""统一渲染微信公众号写作技能组的 Progress checklist。"""

from typing import Dict, List, Optional

STAGE_TO_PHASE = {
    "init": 1,
    "clarify": 1,
    "template_loaded": 2,
    "angle_diagnosed": 2,
    "role_boundary": 2,
    "angle_matched": 3,
    "outline_generated": 3,
    "outline_selected": 3,
    "outline_confirmed": 3,
    "draft_written": 4,
    "draft_revised": 4,
    "polished": 5,
    "titled": 5,
    "title_confirmed": 5,
    "quality_checked": 6,
    "quality_failed": 6,
    "finalized": 6,
    "markdown_output": 6,
    "publish_decision": 6,
}

PHASE_NAMES = {
    1: "阶段 1/6：初始化与需求澄清",
    2: "阶段 2/6：素材诊断与角度选择",
    3: "阶段 3/6：大纲生成与确认",
    4: "阶段 4/6：正文写作与人工改写",
    5: "阶段 5/6：润色、小标题与标题优化",
    6: "阶段 6/6：质量检查与终审定稿",
}


def _render_step(step: dict, is_current: bool, seq: int) -> str:
    status = step.get("status", "pending")
    checkbox = "[✓]" if status == "done" else "[ ]"
    tags = " ".join(f"[{tag}]" for tag in step.get("tags", []))
    current_marker = "  ← 当前" if is_current else ""
    return f"- {checkbox} Step {seq} {step['name']} {tags}{current_marker}"


def render_macro(
    current_stage: str,
    completed_stages: List[str],
    pending_stages: List[str],
    current_step: Optional[str] = None,
    steps: Optional[List[Dict]] = None,
) -> str:
    """输出宏观 6 阶段仪表盘。

    Args:
        current_stage: 当前内部 stage 名。
        completed_stages: 已完成的 stage 列表（仅用于未来扩展，当前按 current_stage 计算）。
        pending_stages: 待开始的 stage 列表（仅用于未来扩展）。
        current_step: 当前阶段内的步骤名称。
        steps: 当前阶段内的步骤列表。

    Returns:
        Markdown 格式的宏观进度字符串。
    """
    lines = ["📝 公众号长文写作进度", ""]
    current_phase_num = STAGE_TO_PHASE.get(current_stage, 0)

    for phase_num in range(1, 7):
        phase_title = PHASE_NAMES[phase_num]
        if phase_num < current_phase_num:
            lines.append(f"{phase_title} [✓]")
        elif phase_num == current_phase_num:
            lines.append(f"{phase_title}")
            if steps:
                for idx, step in enumerate(steps, start=1):
                    is_current = step["name"] == current_step
                    lines.append("  " + _render_step(step, is_current, idx))
        else:
            lines.append(f"{phase_title} [待开始]")

    return "\n".join(lines)


def render_micro(
    phase_name: str,
    steps: list[dict],
    current_step: str,
    show_phase_locator: bool = False,
) -> str:
    """输出子 skill 的 micro-checklist。

    Args:
        phase_name: 阶段名称，如"阶段 3/6：大纲生成与确认"。
        steps: 步骤列表，每项包含 name / tags / status。
        current_step: 当前步骤名称。
        show_phase_locator: 是否展示"当前处于公众号长文写作的..."定位句。

    Returns:
        Markdown 格式的 micro-checklist 字符串。
    """
    lines = []
    if show_phase_locator:
        lines.append(f"当前处于公众号长文写作的{phase_name}。")
        lines.append("")

    lines.append(phase_name)
    lines.append("Progress:")

    for idx, step in enumerate(steps, start=1):
        is_current = step["name"] == current_step
        lines.append(_render_step(step, is_current, idx))

    return "\n".join(lines)
