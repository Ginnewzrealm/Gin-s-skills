"""YAML 风格模板加载器。

负责读取 templates/ 下的 YAML 风格模板并校验必要字段。
支持插件式扩展：用户只要按约定格式新建 YAML 文件放入模板目录，
即可被自动发现和加载。
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import yaml


# 风格模板必要字段（与 _style-template.yaml 保持一致）
REQUIRED_TOP_KEYS = [
    "meta",
    "风格核心",
    "结构参考",
]

REQUIRED_META_KEYS = ["name", "id", "description"]

# 推荐字段（缺失时仅警告，不阻塞）
RECOMMENDED_TOP_KEYS = [
    "怎么开头",
    "怎么推进",
    "怎么处理意外/转折",
    '怎么"掏知识"',
    "怎么处理读者",
    "怎么结尾",
    "情绪基调",
    "禁区",
    "情绪触发点匹配",
    "转场口语",
    "原文片段示例",
    "视觉提示",
]


def load_template(path: Union[str, Path]) -> dict:
    """加载 YAML 风格模板文件。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"模板文件不存在：{path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_template(template: dict) -> list:
    """校验模板是否包含必要字段。

    返回错误列表。空列表表示校验通过。
    """
    errors = []

    for key in REQUIRED_TOP_KEYS:
        if key not in template:
            errors.append(f"缺少顶层字段：{key}")

    if "meta" in template:
        for key in REQUIRED_META_KEYS:
            if key not in template["meta"]:
                errors.append(f"meta 缺少字段：{key}")

    # 推荐字段缺失时作为警告，不阻塞
    for key in RECOMMENDED_TOP_KEYS:
        if key not in template:
            errors.append(f"[建议补充] 缺少字段：{key}")

    return errors


def validate_template_completeness(template: dict) -> list:
    """校验模板结构是否完整到足以生成 narrative_protocol。

    与 validate_template 不同，这里关注模板能否被下游安全使用：
    - 必须包含非空的结构参考（sections）
    - 每个 section 必须包含名称

    返回错误列表。空列表表示完整可用。
    """
    errors = []
    raw_sections = template.get("结构参考", [])

    if not raw_sections:
        errors.append("模板缺少结构参考（sections），无法生成 narrative_protocol")
        return errors

    if not isinstance(raw_sections, list):
        errors.append("模板的结构参考必须是列表")
        return errors

    for i, sec in enumerate(raw_sections):
        if not isinstance(sec, dict):
            errors.append(f"结构参考第 {i + 1} 项必须是字典")
            continue
        if not sec.get("section"):
            errors.append(f"结构参考第 {i + 1} 项缺少 section 名称")

    return errors


def list_templates(templates_dir: Union[str, Path]) -> List[dict]:
    """扫描模板目录，返回所有可用的风格模板元信息。

    返回列表项格式：
        {
            "id": "investigation",
            "name": "调查实验型",
            "description": "...",
            "path": "/path/to/investigation.yaml"
        }
    """
    templates_dir = Path(templates_dir)
    if not templates_dir.exists():
        return []

    templates = []
    for file_path in sorted(templates_dir.glob("*.yaml")):
        # 跳过模板范本文件（以下划线开头）
        if file_path.name.startswith("_"):
            continue

        try:
            template = load_template(file_path)
            meta = template.get("meta", {})
            templates.append(
                {
                    "id": meta.get("id", file_path.stem),
                    "name": meta.get("name", file_path.stem),
                    "description": meta.get("description", ""),
                    "path": str(file_path),
                }
            )
        except Exception:
            # 解析失败的文件跳过，不中断扫描
            continue

    return templates


def list_all_templates(
    default_dir: Union[str, Path],
    user_dir: Optional[Union[str, Path]] = None,
) -> List[dict]:
    """合并默认目录和用户目录，返回所有可用风格模板元信息。

    用户目录优先：同名 template_id 以用户目录为准。
    """
    default_dir = Path(default_dir)
    user_dir = Path(user_dir) if user_dir else None

    default_templates = {t["id"]: t for t in list_templates(default_dir)}
    user_templates = {}
    if user_dir and user_dir.exists():
        user_templates = {t["id"]: t for t in list_templates(user_dir)}

    merged = dict(default_templates)
    merged.update(user_templates)

    return sorted(merged.values(), key=lambda t: t["id"])


def find_template(
    template_id: str,
    default_dir: Union[str, Path],
    user_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """按 template_id 查找模板文件路径。

    查找顺序：
    1. 用户自定义模板目录（如果存在）
    2. 默认模板目录

    找不到则抛出 FileNotFoundError。
    """
    default_dir = Path(default_dir)
    candidates = [default_dir / f"{template_id}.yaml"]

    if user_dir is not None:
        user_dir = Path(user_dir)
        if user_dir.exists():
            candidates.insert(0, user_dir / f"{template_id}.yaml")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"找不到模板：{template_id}.yaml。"
        f"已查找路径：{[str(c) for c in candidates]}"
    )


def extract_narrative_protocol(template: dict) -> dict:
    """从 YAML 模板中提取叙事协议，供大纲生成和正文写作强制执行。"""
    meta = template.get("meta", {})
    raw_sections = template.get("结构参考", [])

    completeness_errors = validate_template_completeness(template)
    fully_loaded = len(completeness_errors) == 0

    sections = []
    for sec in raw_sections:
        if not isinstance(sec, dict):
            continue
        sections.append(
            {
                "name": sec.get("section", ""),
                "purpose": sec.get("purpose", ""),
                "length": sec.get("length", ""),
                "must_include": sec.get("must_include", []),
                "forbidden": sec.get("forbidden", []),
                "template": sec.get("template", ""),
            }
        )

    return {
        "derived_from": meta.get("id", ""),
        "fully_loaded": fully_loaded,
        "completeness_errors": completeness_errors,
        "sections": sections,
        "global_rules": {
            "opening": template.get("怎么开头", ""),
            "progression": template.get("怎么推进", ""),
            "twist": template.get("怎么处理意外/转折", ""),
            "knowledge": template.get('怎么"掏知识"', ""),
            "reader": template.get("怎么处理读者", ""),
            "ending": template.get("怎么结尾", ""),
        },
        "tone": template.get("情绪基调", ""),
        "forbidden_zone": _parse_forbidden_zone(template.get("禁区", [])),
    }


def _parse_forbidden_zone(value: Any) -> List[str]:
    """解析禁区字段，支持列表或文本块。"""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if not value:
        return []
    return [
        line.strip().lstrip("- ").strip()
        for line in str(value).strip().splitlines()
        if line.strip()
    ]


def validate_sections_coverage(
    outline_sections: List[dict], narrative_protocol: dict
) -> List[str]:
    """校验大纲是否完整覆盖了 narrative_protocol 中的所有 section。

    这是"模板 100% 阅读"原则的代码级校验：
    - narrative_protocol 必须 fully_loaded
    - 大纲必须包含 narrative_protocol 中定义的每一个 section name

    返回错误列表。空列表表示覆盖完整。
    """
    errors = []
    if not narrative_protocol.get("fully_loaded"):
        errors.extend(narrative_protocol.get("completeness_errors", []))
        return errors

    expected_names = {
        sec["name"]
        for sec in narrative_protocol.get("sections", [])
        if sec.get("name")
    }
    actual_names = {
        sec.get("name")
        for sec in outline_sections
        if isinstance(sec, dict) and sec.get("name")
    }

    missing = expected_names - actual_names
    if missing:
        errors.append(f"大纲缺少 narrative_protocol 要求的章节：{sorted(missing)}")

    return errors
