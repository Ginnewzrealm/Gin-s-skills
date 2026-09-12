"""需求记录校验工具。

把 gin-wechat-article-clarify SKILL.md 中描述的两条确定性规则固化为纯函数：

1. 素材完整性确认（SKILL.md「动作」第 6 条）：
   - `materials_summary.total_chars` 为 0 或用户未提供任何素材
     -> `materials_sufficient = false`，`materials_gap` 列出需要补充的素材类型
   - 已有素材可支撑核心观点 -> `materials_sufficient = true`，`materials_gap` 为空列表

2. 需求记录结构校验（SKILL.md「输出」节）：
   - `topic` / `target_reader` / `core_points` / `word_count` / `materials`
     / `speaker_position`（含 `who` / `credential` / `trigger`）必须存在且非空。

主 skill 可在写入 context.md 前调用本脚本做一致性检查；
本脚本是可选辅助，不改变 SKILL.md 定义的输出契约。
"""

from typing import Any, Dict, List


# 素材不足时建议补充的素材类型（通用提示，具体缺口由访谈确认）
DEFAULT_MATERIAL_GAP = [
    "核心事实或亲历经过",
    "支撑细节（数据、对话、场景）",
]

REQUIRED_REQUIREMENT_FIELDS = [
    "topic",
    "target_reader",
    "core_points",
    "word_count",
    "materials",
    "speaker_position",
]

REQUIRED_SPEAKER_POSITION_FIELDS = ["who", "credential", "trigger"]


def assess_materials(total_chars: int, user_provided_materials: bool = True) -> Dict[str, Any]:
    """按 SKILL.md 动作第 6 条的规则判断素材是否足够。

    Args:
        total_chars: materials_summary.total_chars，即已读取素材的总字符数。
        user_provided_materials: 用户是否提供了任何素材（含素材目录外的口头素材）。

    Returns:
        {"materials_sufficient": bool, "materials_gap": [str, ...]}
    """
    if not user_provided_materials or total_chars <= 0:
        return {"materials_sufficient": False, "materials_gap": list(DEFAULT_MATERIAL_GAP)}
    return {"materials_sufficient": True, "materials_gap": []}


def validate_requirements(requirements: Dict[str, Any]) -> List[str]:
    """校验需求记录是否包含 SKILL.md 要求的全部字段且非空。

    返回错误列表。空列表表示校验通过。
    """
    errors: List[str] = []
    if not isinstance(requirements, dict) or not requirements:
        return ["requirements 为空或不是对象"]

    for field in REQUIRED_REQUIREMENT_FIELDS:
        value = requirements.get(field)
        if value is None:
            errors.append(f"需求记录缺少字段：{field}")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"需求记录字段 {field} 为空字符串")
        elif isinstance(value, (list, dict)) and not value:
            errors.append(f"需求记录字段 {field} 为空")

    speaker = requirements.get("speaker_position")
    if isinstance(speaker, dict):
        for field in REQUIRED_SPEAKER_POSITION_FIELDS:
            value = speaker.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"speaker_position 缺少字段：{field}")

    return errors
