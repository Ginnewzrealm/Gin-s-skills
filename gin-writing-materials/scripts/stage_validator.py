#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段校验器：决定当前步骤、校验步骤合法性、支持回环。"""

from typing import Dict, List, Optional

from progress_reporter import MINE_STEPS, ACTION_MICRO_STEPS


MINE_STEP_KEYS = [step["key"] for step in MINE_STEPS]


def decide_next_stage(session: Dict, action: str = "mine") -> Dict[str, any]:
    """根据会话状态决定当前应处于哪个步骤。

    Args:
        session: 当前会话状态字典。
        action: 当前动作，默认 mine。

    Returns:
        {
            "current_key": 当前步骤 key,
            "completed_keys": 已完成的步骤 key 列表,
            "reason": 决策原因,
        }
    """
    stage = session.get("stage")
    status = session.get("status")

    if status == "completed":
        return {
            "current_key": "completed",
            "completed_keys": MINE_STEP_KEYS,
            "reason": "会话已完成",
        }

    if action != "mine":
        steps = ACTION_MICRO_STEPS.get(action, [])
        if not steps:
            return {"current_key": "", "completed_keys": [], "reason": "未知动作"}
        current_key = stage if stage and stage in [s["key"] for s in steps] else steps[0]["key"]
        completed = []
        for s in steps:
            if s["key"] == current_key:
                break
            completed.append(s["key"])
        return {"current_key": current_key, "completed_keys": completed, "reason": f"{action} 动作初始步骤"}

    # mine 动作
    if stage and stage in MINE_STEP_KEYS:
        current_key = stage
    else:
        current_key = "project_located"

    completed = []
    for step in MINE_STEPS:
        if step["key"] == current_key:
            break
        completed.append(step["key"])

    return {"current_key": current_key, "completed_keys": completed, "reason": "基于会话 stage 恢复"}


def validate_transition(current_key: str, next_key: str, action: str = "mine") -> Dict[str, any]:
    """校验步骤跳转是否合法。

    规则：
    - 正常只能前进到下一步
    - 允许回环到任意已完成步骤（[可回环]）
    - 不允许跳过后续未执行步骤

    Returns:
        {"valid": bool, "reason": str}
    """
    steps = MINE_STEPS if action == "mine" else ACTION_MICRO_STEPS.get(action, [])
    keys = [step["key"] for step in steps]

    if current_key not in keys:
        return {"valid": False, "reason": f"当前步骤 {current_key} 不在流程中"}
    if next_key not in keys:
        return {"valid": False, "reason": f"目标步骤 {next_key} 不在流程中"}

    current_idx = keys.index(current_key)
    next_idx = keys.index(next_key)

    if next_idx == current_idx + 1:
        return {"valid": True, "reason": "正常前进"}
    if next_idx <= current_idx:
        return {"valid": True, "reason": "用户要求回环到已完成步骤"}

    return {"valid": False, "reason": f"不能从 {current_key} 跳过到 {next_key}"}


def advance_stage(session: Dict, action: str = "mine") -> Optional[str]:
    """推进到下一步。返回新的 current_key，如果已是最后一步则返回 None。"""
    steps = MINE_STEPS if action == "mine" else ACTION_MICRO_STEPS.get(action, [])
    keys = [step["key"] for step in steps]
    current = session.get("stage", keys[0] if keys else None)
    if current not in keys:
        return keys[0] if keys else None
    idx = keys.index(current)
    if idx + 1 < len(keys):
        return keys[idx + 1]
    return None


def is_hard_gate(step_key: str, action: str = "mine") -> bool:
    """判断某步骤是否为硬闸门。"""
    steps = MINE_STEPS if action == "mine" else ACTION_MICRO_STEPS.get(action, [])
    for step in steps:
        if step["key"] == step_key:
            return "硬闸门" in step["tags"]
    return False
