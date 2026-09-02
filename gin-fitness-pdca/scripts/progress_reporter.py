#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_reporter.py — 统一渲染 PDCA 减脂分析的 Progress checklist。"""

from typing import Dict, List, Optional


# ---------- 初始化流程定义 ----------

INIT_PHASES: Dict[int, str] = {
    1: "阶段 1/4：环境准备",
    2: "阶段 2/4：表结构确认",
    3: "阶段 3/4：目标配置",
    4: "阶段 4/4：持久化与注册",
}

INIT_STEPS: List[Dict[str, object]] = [
    {"name": "检测 lark-cli", "phase": 1, "tags": ["自动"]},
    {"name": "询问并保存电子表格链接", "phase": 1, "tags": ["硬闸门"]},
    {"name": "验证表格和子表存在", "phase": 2, "tags": ["自动"]},
    {"name": "读取表头并建立字段映射", "phase": 2, "tags": ["需确认", "可回环"]},
    {"name": "询问目标参数", "phase": 3, "tags": ["硬闸门", "可回环"]},
    {"name": "询问定时时间", "phase": 3, "tags": ["硬闸门", "可回环"]},
    {"name": "保存 config.json", "phase": 4, "tags": ["自动"]},
    {"name": "注册 cron", "phase": 4, "tags": ["自动"]},
]


# ---------- 主流程定义 ----------

MAIN_PHASES: Dict[int, str] = {
    1: "阶段 1/4：周边界与数据拉取",
    2: "阶段 2/4：数据质量校验",
    3: "阶段 3/4：扫描与报告生成",
    4: "阶段 4/4：写入与通知",
}

MAIN_STEPS: List[Dict[str, object]] = [
    {"name": "计算本周周号与日期边界", "phase": 1, "tags": ["自动"]},
    {"name": "发送开始通知", "phase": 1, "tags": ["自动"]},
    {"name": "读取本期 7 天数据与上期输出表", "phase": 1, "tags": ["自动"]},
    {"name": "执行数据质量双闸", "phase": 2, "tags": ["硬闸门"]},
    {"name": "执行 M1-M9 代谢扫描", "phase": 3, "tags": ["自动"]},
    {"name": "生成 9 字段 PDCA 报告", "phase": 3, "tags": ["自动"]},
    {"name": "写入周表并回执确认", "phase": 4, "tags": ["自动"]},
    {"name": "发送完成通知", "phase": 4, "tags": ["自动"]},
]


_FLOW_CONFIG = {
    "init": {"phases": INIT_PHASES, "steps": INIT_STEPS, "title": "🔄 PDCA减脂分析 · 初始化进度"},
    "main": {"phases": MAIN_PHASES, "steps": MAIN_STEPS, "title": "📝 PDCA减脂分析进度"},
}


def _step_id(flow: str, idx: int) -> str:
    """生成步骤内部 ID，例如 init_1 / main_4。"""
    return f"{flow}_{idx + 1}"


def _step_id_to_index(step_id: str) -> int:
    """从步骤 ID 解析序号，例如 init_4 → 3。"""
    return int(step_id.split("_", 1)[1]) - 1


def _render_step(step: Dict[str, object], is_current: bool, is_done: bool, seq: int) -> str:
    checkbox = "[✓]" if is_done else "[ ]"
    tags = " ".join(f"[{tag}]" for tag in step.get("tags", []))
    current_marker = "  ← 当前" if is_current else ""
    return f"- {checkbox} Step {seq} {step['name']} {tags}{current_marker}".rstrip()


def _get_flow_config(flow: str) -> Dict[str, object]:
    if flow not in _FLOW_CONFIG:
        raise ValueError(f"未知的流程类型: {flow}，只能是 init 或 main")
    return _FLOW_CONFIG[flow]


def render_macro(
    flow: str,
    current_step_id: Optional[str] = None,
    completed_step_ids: Optional[List[str]] = None,
    resume: bool = False,
) -> str:
    """渲染宏观 4 阶段仪表盘。

    参数：
        flow: "init" 或 "main"
        current_step_id: 当前步骤 ID，例如 "main_3"
        completed_step_ids: 已完成的步骤 ID 列表
        resume: 是否为会话恢复场景
    """
    config = _get_flow_config(flow)
    phases: Dict[int, str] = config["phases"]
    steps: List[Dict[str, object]] = config["steps"]
    completed = set(completed_step_ids or [])

    current_idx = _step_id_to_index(current_step_id) if current_step_id else -1
    current_phase = steps[current_idx]["phase"] if current_step_id and 0 <= current_idx < len(steps) else 0

    title = config["title"]
    if resume:
        title += "（恢复）"

    lines = [title, ""]

    for phase_num in range(1, len(phases) + 1):
        phase_title = phases[phase_num]
        if phase_num < current_phase:
            lines.append(f"{phase_title} [✓]")
        elif phase_num == current_phase:
            lines.append(f"{phase_title} [当前]")
            # 展开当前阶段的微观 checklist，使用全局 Step 序号
            phase_steps = [s for s in steps if s["phase"] == phase_num]
            for step in phase_steps:
                global_idx = steps.index(step)
                step_id = _step_id(flow, global_idx)
                is_current = step_id == current_step_id
                is_done = step_id in completed
                lines.append("  " + _render_step(step, is_current, is_done, global_idx + 1))
        else:
            lines.append(f"{phase_title} [待开始]")

    return "\n".join(lines)


def render_micro(
    flow: str,
    current_step_id: Optional[str] = None,
    completed_step_ids: Optional[List[str]] = None,
    show_phase_locator: bool = False,
) -> str:
    """渲染当前阶段微观 checklist。

    参数：
        flow: "init" 或 "main"
        current_step_id: 当前步骤 ID
        completed_step_ids: 已完成的步骤 ID 列表
        show_phase_locator: 是否在开头输出阶段定位句
    """
    config = _get_flow_config(flow)
    phases: Dict[int, str] = config["phases"]
    steps: List[Dict[str, object]] = config["steps"]
    completed = set(completed_step_ids or [])

    current_idx = _step_id_to_index(current_step_id) if current_step_id else -1
    current_phase = steps[current_idx]["phase"] if current_step_id and 0 <= current_idx < len(steps) else 0

    lines = []
    if show_phase_locator:
        phase_title = phases.get(current_phase, "")
        if phase_title:
            lines.append(f"当前处于 PDCA减脂分析的{phase_title}。")
            lines.append("")

    if current_phase:
        lines.append(phases[current_phase])
    else:
        lines.append(config["title"])

    lines.append("Progress:")

    phase_steps = [s for s in steps if s["phase"] == current_phase]
    for step in phase_steps:
        global_idx = steps.index(step)
        step_id = _step_id(flow, global_idx)
        is_current = step_id == current_step_id
        is_done = step_id in completed
        lines.append(_render_step(step, is_current, is_done, global_idx + 1))

    return "\n".join(lines)


def render_blocker(
    flow: str,
    current_step_id: str,
    reason: str,
    options: Optional[List[str]] = None,
) -> str:
    """渲染硬闸门阻塞提示。"""
    config = _get_flow_config(flow)
    steps: List[Dict[str, object]] = config["steps"]
    current_idx = _step_id_to_index(current_step_id)
    current_step = steps[current_idx]
    phase_title = config["phases"][current_step["phase"]]

    lines = [
        f"⚠️ 当前阻塞：{reason}",
        "",
        f"当前位置：{phase_title} · Step {_step_id_to_index(current_step_id) + 1} {current_step['name']}",
    ]

    if options:
        lines.append("")
        lines.append("你可以：")
        for opt in options:
            lines.append(f"- {opt}")

    return "\n".join(lines)


def get_step_name(flow: str, step_id: str) -> str:
    """获取步骤名称。"""
    config = _get_flow_config(flow)
    steps: List[Dict[str, object]] = config["steps"]
    idx = _step_id_to_index(step_id)
    return steps[idx]["name"]


def get_phase_of_step(flow: str, step_id: str) -> int:
    """获取步骤所属阶段。"""
    config = _get_flow_config(flow)
    steps: List[Dict[str, object]] = config["steps"]
    idx = _step_id_to_index(step_id)
    return steps[idx]["phase"]


def list_step_ids(flow: str) -> List[str]:
    """返回某流程下所有步骤 ID。"""
    config = _get_flow_config(flow)
    return [_step_id(flow, i) for i in range(len(config["steps"]))]


if __name__ == "__main__":
    # 简单自测
    print(render_macro("main", "main_3", ["main_1", "main_2"]))
    print()
    print(render_micro("main", "main_3", ["main_1", "main_2"], show_phase_locator=True))
    print()
    print(render_blocker("main", "main_4", "数据质量未通过「闸 1 · 覆盖率」", [
        "补充缺失的每日记录后，重新说\"跑一下周报\"",
        "输入\"跳过本周\"放弃本期分析",
    ]))
