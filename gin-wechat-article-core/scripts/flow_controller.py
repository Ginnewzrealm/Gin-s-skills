#!/usr/bin/env python3
"""flow_controller.py — 微信公众号长文写作流程控制器。

把「读取 progress.md → 决定当前 stage → 校验下一步 → 渲染 Progress」封装成单一入口，
强制主 skill 在推进 stage 前先调用本脚本。

用法：
  python3 scripts/flow_controller.py \
      --article-dir output_dir/<article_id> \
      --next-stage role_boundary

输出 JSON：
  {
    "can_proceed": true | false,
    "current_stage": "angle_diagnosed",
    "next_stage": "role_boundary",
    "errors": [],
    "skipped_sub_skills": [],
    "rendered_progress": "...",
    "is_hard_gate": true | false
  }
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

import importlib.util


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


progress_reporter = _load_module("progress_reporter", SCRIPTS_DIR / "progress_reporter.py")
stage_validator = _load_module("stage_validator", SCRIPTS_DIR / "stage_validator.py")


def _load_context(article_dir: Path) -> Dict[str, Any]:
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


def _load_progress(article_dir: Path) -> Dict[str, Any]:
    """读取 progress.md，返回其中的 stage 信息。"""
    progress_path = article_dir / "progress.md"
    if not progress_path.exists():
        return {"stage": "init"}

    content = progress_path.read_text(encoding="utf-8")
    stage = "init"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("当前阶段："):
            stage = stripped.replace("当前阶段：", "").strip()
            break
    return {"stage": stage}


def _detect_skipped_sub_skills(errors: List[str]) -> List[Dict[str, str]]:
    """从错误信息中提取被跳过的子 skill。"""
    skipped = []
    for err in errors:
        if "子 skill" in err and "被跳过" in err:
            # 简单提取子 skill 名
            start = err.find("子 skill ") + len("子 skill ")
            end = err.find(" ", start)
            sub_skill = err[start:end] if end > start else err[start:]
            skipped.append({"sub_skill": sub_skill, "reason": err})
    return skipped


def control_flow(article_dir: Path, next_stage: str) -> Dict[str, Any]:
    """主控函数。"""
    progress = _load_progress(article_dir)
    context = _load_context(article_dir)

    current_stage = progress.get("stage", "init")

    # 校验下一步
    errors = stage_validator.validate_next_step(
        current_stage,
        next_stage,
        context,
        available_templates=None,
        article_dir=article_dir,
    )

    can_proceed = len(errors) == 0
    skipped = _detect_skipped_sub_skills(errors)

    # 渲染进度
    try:
        rendered = progress_reporter.render_macro(current_stage, [], [], steps=None)
        if not can_proceed:
            rendered += progress_reporter.render_skipped_warnings(skipped)
            rendered += "\n" + progress_reporter.render_blocker(
                f"无法从 {current_stage} 进入 {next_stage}",
                errors,
            )
    except Exception as e:
        rendered = f"📝 公众号长文写作进度（渲染失败：{e}）"

    is_hard_gate = stage_validator.is_hard_gate(next_stage)

    return {
        "can_proceed": can_proceed,
        "current_stage": current_stage,
        "next_stage": next_stage,
        "errors": errors,
        "skipped_sub_skills": skipped,
        "rendered_progress": rendered,
        "is_hard_gate": is_hard_gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="微信公众号长文写作流程控制器")
    parser.add_argument("--article-dir", required=True, help="文章项目目录")
    parser.add_argument("--next-stage", required=True, help="目标 stage")

    args = parser.parse_args()
    article_dir = Path(args.article_dir)

    result = control_flow(article_dir, args.next_stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["can_proceed"] else 1


if __name__ == "__main__":
    sys.exit(main())
