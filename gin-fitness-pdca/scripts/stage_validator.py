#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage_validator.py — PDCA 减脂分析阶段合法性校验。"""

from typing import Dict, List, Optional

from progress_reporter import (
    INIT_STEPS,
    MAIN_STEPS,
    list_step_ids,
)


class StageValidationError(Exception):
    """阶段校验失败异常。"""

    def __init__(self, message: str, from_step: Optional[str] = None, to_step: Optional[str] = None):
        super().__init__(message)
        self.from_step = from_step
        self.to_step = to_step


_FLOW_STEPS: Dict[str, List[Dict[str, object]]] = {
    "init": INIT_STEPS,
    "main": MAIN_STEPS,
}

_HARD_GATES: Dict[str, List[str]] = {
    "init": ["init_2", "init_5", "init_6"],
    "main": ["main_4"],
}

# 回环映射：用户指令 → 目标步骤
_LOOP_TARGETS: Dict[str, Dict[str, str]] = {
    "init": {
        "重新映射字段": "init_4",
        "字段映射不对": "init_4",
        "表头认错了": "init_4",
        "修改目标": "init_5",
        "目标参数错了": "init_5",
        "目标改一下": "init_5",
        "修改定时": "init_6",
        "换个时间": "init_6",
        "定时改一下": "init_6",
    },
    "main": {
        "重新校验数据": "main_4",
        "数据再检查一遍": "main_4",
        "重新扫描": "main_5",
        "重新做 M1-M9": "main_5",
        "重新生成报告": "main_6",
        "报告重新出": "main_6",
    },
}


def _step_index(flow: str, step_id: str) -> int:
    all_ids = list_step_ids(flow)
    if step_id not in all_ids:
        raise StageValidationError(f"未知步骤: {step_id}")
    return all_ids.index(step_id)


def validate_transition(
    flow: str,
    from_step: Optional[str],
    to_step: str,
    completed_step_ids: Optional[List[str]] = None,
) -> None:
    """校验从 from_step 到 to_step 的转换是否合法。

    合法规则：
    - 只能顺序推进，不能跳过未完成的步骤（自动步骤例外：可连续执行）
    - 不能回退到已完成步骤之后的位置，除非显式回环
    - 硬闸门步骤必须由用户确认后才能推进

    参数：
        flow: "init" 或 "main"
        from_step: 当前步骤 ID，None 表示从头开始
        to_step: 目标步骤 ID
        completed_step_ids: 已完成的步骤 ID 列表

    异常：
        StageValidationError: 转换非法时抛出
    """
    if flow not in _FLOW_STEPS:
        raise StageValidationError(f"未知流程: {flow}")

    completed = set(completed_step_ids or [])
    all_ids = list_step_ids(flow)

    to_idx = _step_index(flow, to_step)
    from_idx = _step_index(flow, from_step) if from_step else -1

    # 不能跳到未知步骤
    if to_step not in all_ids:
        raise StageValidationError(f"目标步骤 {to_step} 不存在", from_step, to_step)

    # 顺序推进：下一步或者当前步（重试）
    if to_idx == from_idx:
        # 允许停留在当前步骤（例如重试）
        return

    if to_idx == from_idx + 1:
        # 顺序前进一步：检查是否越过了未完成的硬闸门
        if from_step and from_step in _HARD_GATES[flow] and from_step not in completed:
            raise StageValidationError(
                f"硬闸门步骤 {from_step} 尚未确认，不能推进",
                from_step,
                to_step,
            )
        return

    # 向后跳超过一步：非法跳跃
    if to_idx > from_idx + 1:
        # 自动步骤可以连续执行：允许从已完成步骤跳到下一个未执行的自动步骤链末端
        if from_step and from_step in completed:
            # 检查中间步骤是否都是自动且已完成
            intermediate = all_ids[from_idx + 1 : to_idx]
            if not all(s in completed for s in intermediate):
                raise StageValidationError(
                    f"非法跳跃：从 {from_step} 到 {to_step} 跳过了未完成的步骤",
                    from_step,
                    to_step,
                )
            return
        raise StageValidationError(
            f"非法跳跃：从 {from_step} 到 {to_step} 跳过了中间步骤",
            from_step,
            to_step,
        )

    # 回退（to_idx < from_idx）
    # 只允许回退到已完成步骤或当前步骤之前的步骤
    if to_idx < from_idx:
        if to_step not in completed and to_idx != from_idx - 1:
            raise StageValidationError(
                f"非法回退：不能回退到未完成的步骤 {to_step}",
                from_step,
                to_step,
            )
        return


def is_hard_gate(flow: str, step_id: str) -> bool:
    """判断步骤是否为硬闸门。"""
    return step_id in _HARD_GATES.get(flow, [])


def get_loop_target(flow: str, user_command: str) -> Optional[str]:
    """根据用户指令解析回环目标步骤。"""
    return _LOOP_TARGETS.get(flow, {}).get(user_command.strip())


def list_loop_commands(flow: str) -> List[str]:
    """返回某流程下所有支持的回环指令。"""
    return list(_LOOP_TARGETS.get(flow, {}).keys())


def next_step_id(flow: str, current_step_id: Optional[str]) -> Optional[str]:
    """获取当前步骤的下一个步骤 ID。"""
    all_ids = list_step_ids(flow)
    if current_step_id is None:
        return all_ids[0] if all_ids else None
    idx = _step_index(flow, current_step_id)
    if idx + 1 < len(all_ids):
        return all_ids[idx + 1]
    return None


if __name__ == "__main__":
    # 简单自测
    print("hard gates in init:", _HARD_GATES["init"])
    print("main_4 is hard gate:", is_hard_gate("main", "main_4"))
    try:
        validate_transition("main", "main_3", "main_5", ["main_1", "main_2", "main_3"])
        print("非法跳跃未被拦截！")
    except StageValidationError as e:
        print("正确拦截非法跳跃:", e)

    try:
        validate_transition("main", "main_3", "main_4", ["main_1", "main_2", "main_3"])
        print("main_3 → main_4 合法")
    except StageValidationError as e:
        print("错误拦截:", e)

    target = get_loop_target("init", "修改目标")
    print("回环目标:", target)
