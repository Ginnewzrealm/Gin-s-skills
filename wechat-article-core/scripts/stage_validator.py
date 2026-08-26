"""阶段校验器。

负责微信公众号长文写作主流程的代码级阶段校验：
- 校验 stage 转换是否合法
- 校验进入每个 stage 前必要字段是否存在
- 校验模板是否在白名单内
- 校验 narrative_protocol 是否完整加载

每次主 skill 决定下一步前，都应调用本模块。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


# 合法阶段序列与转换图
# key: 当前 stage
# value: 允许的下一个 stage 列表
STAGE_TRANSITIONS = {
    "init": ["clarify", "template_loaded"],
    "clarify": ["template_loaded"],
    "template_loaded": ["angle_diagnosed"],
    "angle_diagnosed": ["role_boundary"],
    "role_boundary": ["angle_matched"],
    "angle_matched": ["outline_generated"],
    "outline_generated": ["outline_selected"],
    # 新增 outline_confirmed 阻塞节点
    "outline_selected": ["outline_confirmed"],
    "outline_confirmed": ["draft_written"],
    "draft_written": ["draft_revised"],
    "draft_revised": ["polished"],
    "polished": ["titled"],
    "titled": ["title_confirmed"],
    "title_confirmed": ["quality_checked"],
    "quality_checked": ["finalized"],
    "finalized": ["markdown_output"],
    "markdown_output": ["publish_decision"],
    "publish_decision": [],
}

# 每个 stage 进入前必须存在的字段（context.md 中）
STAGE_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "init": [],
    "clarify": ["selected_template"],
    "template_loaded": ["selected_template", "requirements"],
    "angle_diagnosed": ["selected_template", "requirements", "narrative_protocol"],
    "role_boundary": ["selected_template", "requirements", "narrative_protocol", "angle_candidates"],
    "angle_matched": ["selected_template", "requirements", "narrative_protocol", "collaboration_charter"],
    "outline_generated": ["selected_template", "requirements", "narrative_protocol", "selected_angle"],
    "outline_selected": ["selected_template", "requirements", "narrative_protocol", "outline_candidates"],
    "outline_confirmed": ["selected_template", "requirements", "narrative_protocol", "selected_outline"],
    "draft_written": ["selected_template", "requirements", "narrative_protocol", "selected_outline"],
    "draft_revised": ["selected_template", "requirements", "narrative_protocol", "draft_revised_path"],
    "polished": ["selected_template", "requirements", "narrative_protocol", "polished_draft_path"],
    "titled": ["selected_template", "requirements", "narrative_protocol", "title_candidates"],
    "title_confirmed": ["selected_template", "requirements", "narrative_protocol", "title_candidates"],
    "quality_checked": ["selected_template", "requirements", "narrative_protocol", "selected_title"],
    "finalized": ["selected_template", "requirements", "narrative_protocol", "quality_report"],
    "markdown_output": ["selected_template", "requirements", "narrative_protocol", "final_draft"],
    "publish_decision": ["selected_template", "requirements", "narrative_protocol", "markdown_output"],
}


def validate_stage_transition(current: str, next_stage: str) -> List[str]:
    """校验从 current 到 next_stage 的转换是否合法。"""
    errors = []
    if current not in STAGE_TRANSITIONS:
        errors.append(f"未知当前阶段：{current}")
        return errors
    allowed = STAGE_TRANSITIONS[current]
    if next_stage not in allowed:
        errors.append(
            f"非法阶段转换：{current} -> {next_stage}。"
            f"允许的下一步：{allowed}"
        )
    return errors


def validate_stage_prerequisites(stage: str, context: Dict[str, Any]) -> List[str]:
    """校验进入 stage 前 context 中必要字段是否存在。"""
    errors = []
    required = STAGE_REQUIRED_FIELDS.get(stage, [])
    for field in required:
        value = context.get(field)
        if value is None:
            errors.append(f"进入阶段 {stage} 缺少必要字段：{field}")
        elif isinstance(value, dict) and not value:
            errors.append(f"进入阶段 {stage} 字段 {field} 为空对象")
        # selected_template 必须已确认，防止风格选择被跳过
        if field == "selected_template" and isinstance(value, dict):
            if not value.get("confirmed"):
                errors.append(
                    f"进入阶段 {stage} 的 selected_template 未确认（confirmed 不为 true）"
                )
    return errors


def validate_template_whitelist(
    template_id: str, available_templates: List[Dict[str, Any]]
) -> List[str]:
    """校验模板 ID 是否在可用模板白名单内。"""
    errors = []
    allowed_ids = {t.get("id") for t in available_templates if t.get("id")}
    if not template_id:
        errors.append("模板 ID 为空")
    elif template_id not in allowed_ids:
        errors.append(
            f"模板 ID '{template_id}' 不在白名单内。"
            f"可用模板：{sorted(allowed_ids)}"
        )
    return errors


def validate_narrative_protocol(narrative_protocol: Dict[str, Any]) -> List[str]:
    """校验 narrative_protocol 是否完整加载。"""
    errors = []
    if not narrative_protocol:
        errors.append("narrative_protocol 为空")
        return errors
    if not narrative_protocol.get("fully_loaded"):
        errors.extend(narrative_protocol.get("completeness_errors", []))
    if not narrative_protocol.get("sections"):
        errors.append("narrative_protocol.sections 为空")
    return errors


def decide_next_stage(
    progress_file: Optional[Path],
    default_stage: str = "init",
) -> str:
    """根据 progress.md 中的 stage 决定下一步。

    这是流程强制的入口：每次主 skill 启动时，先读取持久化的 stage，
    而不是从头开始。
    """
    if not progress_file or not progress_file.exists():
        return default_stage

    content = progress_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("当前阶段："):
            return stripped.replace("当前阶段：", "").strip() or default_stage
    return default_stage


def validate_next_step(
    current_stage: str,
    next_stage: str,
    context: Dict[str, Any],
    available_templates: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """综合校验下一步是否可执行。

    返回错误列表。空列表表示可以安全推进。
    """
    errors = []
    errors.extend(validate_stage_transition(current_stage, next_stage))
    errors.extend(validate_stage_prerequisites(next_stage, context))

    if available_templates and "selected_template" in context:
        template_id = context.get("selected_template", {}).get("id")
        if template_id:
            errors.extend(
                validate_template_whitelist(template_id, available_templates)
            )

    if "narrative_protocol" in context:
        errors.extend(validate_narrative_protocol(context["narrative_protocol"]))

    return errors
