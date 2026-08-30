#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一渲染 gin-writing-materials 的 Progress Checklist。"""

from typing import Dict, List, Optional


# mine 动作的完整阶段定义
MINE_STEPS = [
    {"key": "project_located", "name": "定位/创建项目文件夹", "tags": ["自动"]},
    {"key": "topic_defined", "name": "生成主题定义并确认读者/文体/方向", "tags": ["硬闸门"]},
    {"key": "anchors_loaded", "name": "拉取锚点素材到成品库", "tags": ["自动"]},
    {"key": "domain_selected", "name": "选择本次挖掘域", "tags": ["需确认"]},
    {"key": "mining", "name": "对话挖掘素材", "tags": ["硬闸门", "可回环"]},
    {"key": "validated", "name": "完整性校验", "tags": ["自动"]},
    {"key": "doc_built", "name": "生成素材文档", "tags": ["自动"]},
    {"key": "completed", "name": "输出素材文档路径", "tags": ["需确认"]},
]


# review / correct / build 动作的 micro-checklist
ACTION_MICRO_STEPS = {
    "review": [
        {"key": "project_located", "name": "定位项目文件夹", "tags": ["自动"]},
        {"key": "fragments_loaded", "name": "加载已有素材碎片", "tags": ["自动"]},
        {"key": "presenting", "name": "展示素材碎片列表", "tags": ["需确认"]},
    ],
    "correct": [
        {"key": "project_located", "name": "定位项目文件夹", "tags": ["自动"]},
        {"key": "fragment_loaded", "name": "加载目标素材碎片", "tags": ["自动"]},
        {"key": "correcting", "name": "修改素材碎片", "tags": ["硬闸门"]},
    ],
    "build": [
        {"key": "project_located", "name": "定位项目文件夹", "tags": ["自动"]},
        {"key": "fragments_loaded", "name": "加载已有素材碎片", "tags": ["自动"]},
        {"key": "building", "name": "整合生成素材文档", "tags": ["自动"]},
        {"key": "completed", "name": "输出素材文档路径", "tags": ["需确认"]},
    ],
}


def _checkbox(status: str) -> str:
    return "[✓]" if status == "done" else "[ ]"


def _tag_str(tags: List[str]) -> str:
    return " ".join(f"[{tag}]" for tag in tags)


def render_mine(
    current_key: str,
    completed_keys: Optional[List[str]] = None,
    title: str = "📝 写作素材挖掘进度",
) -> str:
    """渲染 mine 动作的完整 Progress Checklist。

    Args:
        current_key: 当前步骤的 key。
        completed_keys: 已完成步骤的 key 列表。
        title: 标题。

    Returns:
        Markdown 格式的进度字符串。
    """
    completed = set(completed_keys or [])
    lines = [title, ""]
    found_current = False

    for step in MINE_STEPS:
        is_current = step["key"] == current_key
        if is_current:
            found_current = True
        status = "done" if step["key"] in completed or (not is_current and found_current is False) else "pending"
        if is_current:
            status = "current"
        checkbox = _checkbox(status) if status != "current" else "[ ]"
        current_marker = "  ← 当前" if is_current else ""
        tags = _tag_str(step["tags"])
        lines.append(f"- {checkbox} Step {step['key']} {step['name']} {tags}{current_marker}")

    return "\n".join(lines)


def render_micro(
    action: str,
    current_key: str,
    completed_keys: Optional[List[str]] = None,
) -> str:
    """渲染 review / correct / build 等子动作的 micro-checklist。

    Args:
        action: 动作名，必须是 ACTION_MICRO_STEPS 的 key。
        current_key: 当前步骤的 key。
        completed_keys: 已完成步骤的 key 列表。

    Returns:
        Markdown 格式的 micro-checklist。
    """
    steps = ACTION_MICRO_STEPS.get(action, [])
    completed = set(completed_keys or [])
    lines = [f"📝 写作素材 — {action}", ""]
    found_current = False

    for idx, step in enumerate(steps, start=1):
        is_current = step["key"] == current_key
        if is_current:
            found_current = True
        if step["key"] in completed or (not is_current and not found_current):
            status = "done"
        elif is_current:
            status = "current"
        else:
            status = "pending"
        checkbox = _checkbox(status) if status != "current" else "[ ]"
        current_marker = "  ← 当前" if is_current else ""
        tags = _tag_str(step["tags"])
        lines.append(f"- {checkbox} Step {idx} {step['name']} {tags}{current_marker}")

    return "\n".join(lines)


def render_blocker(step_name: str, reason: str, options: Optional[List[str]] = None) -> str:
    """渲染阻塞提示。"""
    lines = [
        f"⚠️ 当前阻塞：{reason}（{step_name}）",
        "",
        "你可以：",
    ]
    for opt in options or []:
        lines.append(f"- {opt}")
    return "\n".join(lines)


def get_default_completed(current_key: str, action: str = "mine") -> List[str]:
    """根据当前 key 推断默认已完成步骤（用于首次展示）。"""
    steps = MINE_STEPS if action == "mine" else ACTION_MICRO_STEPS.get(action, [])
    completed = []
    for step in steps:
        if step["key"] == current_key:
            break
        completed.append(step["key"])
    return completed
