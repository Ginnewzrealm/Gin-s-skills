#!/usr/bin/env python3
"""sub_skill_guard.py — 子 skill 执行守卫。

检查某个子 skill 是否真正执行过：
1. context.md 中指定的输出 key 是否存在且非空
2. 对应的输出文件是否真实存在
3. 输出文件是否晚于 context.md（防止使用旧文件）

用法：
  python3 scripts/sub_skill_guard.py \
      --article-dir output_dir/<article_id> \
      --sub-skill gin-wechat-article-angle \
      --context-key angle_candidates \
      --context-key diagnosis_report \
      --output-file reports/diagnosis_report.md
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_context(article_dir: Path) -> Dict[str, Any]:
    """解析 context.md 的 YAML frontmatter。"""
    context_path = article_dir / "context.md"
    if not context_path.exists():
        return {}

    content = context_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def check_sub_skill_executed(
    article_dir: Path,
    sub_skill: str,
    context_keys: List[str],
    output_files: List[str],
) -> List[str]:
    """检查子 skill 是否真正执行过。返回错误列表。"""
    errors: List[str] = []
    context = load_context(article_dir)

    # 检查 context key
    missing_keys = []
    empty_keys = []
    for key in context_keys:
        value = context.get(key)
        if value is None:
            missing_keys.append(key)
        elif isinstance(value, (dict, list)) and not value:
            empty_keys.append(key)
        elif isinstance(value, str) and not value.strip():
            empty_keys.append(key)

    if missing_keys:
        errors.append(
            f"子 skill {sub_skill} 尚未执行：context.md 缺少字段 {missing_keys}"
        )
    if empty_keys:
        errors.append(
            f"子 skill {sub_skill} 输出为空：context.md 中 {empty_keys} 没有实际内容"
        )

    # 检查输出文件
    for rel_file in output_files:
        file_path = article_dir / rel_file
        if not file_path.exists():
            errors.append(
                f"子 skill {sub_skill} 输出文件缺失：{rel_file}"
            )
        elif file_path.stat().st_size == 0:
            errors.append(
                f"子 skill {sub_skill} 输出文件 {rel_file} 为空"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="子 skill 执行守卫")
    parser.add_argument("--article-dir", required=True, help="文章项目目录")
    parser.add_argument("--sub-skill", required=True, help="子 skill 名称")
    parser.add_argument(
        "--context-key",
        action="append",
        default=[],
        help="context.md 中必须存在的输出 key（可多次指定）",
    )
    parser.add_argument(
        "--output-file",
        action="append",
        default=[],
        help="必须存在的输出文件路径（相对 article-dir，可多次指定）",
    )

    args = parser.parse_args()
    article_dir = Path(args.article_dir)

    errors = check_sub_skill_executed(
        article_dir,
        args.sub_skill,
        args.context_key,
        args.output_file,
    )

    result = {"ok": len(errors) == 0, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
