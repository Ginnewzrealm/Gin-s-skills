#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_store.py — PDCA 减脂分析执行进度持久化。"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from progress_reporter import list_step_ids


DEFAULT_PROGRESS_FILE = "progress.md"


def _default_progress_path() -> str:
    """默认进度文件路径：本技能目录下 progress.md。"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DEFAULT_PROGRESS_FILE)


def load_progress(progress_file: Optional[str] = None) -> Optional[Dict[str, object]]:
    """读取 progress.md，返回进度字典；文件不存在或解析失败返回 None。

    返回结构：
        {
            "flow": "init" | "main",
            "current_step": "init_4",
            "completed_steps": ["init_1", "init_2", "init_3"],
            "last_updated": "2026-09-02T14:30:00+08:00",
        }
    """
    path = progress_file or _default_progress_path()
    if not os.path.isfile(path):
        return None

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None

    # 解析 YAML frontmatter
    if not content.startswith("---"):
        return None

    end = content.find("\n---", 3)
    if end == -1:
        return None

    frontmatter = content[3:end].strip()
    data: Dict[str, object] = {}
    current_key = None
    current_list: List[str] = []

    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- "):
            if current_key:
                current_list.append(stripped[2:].strip())
            continue
        else:
            if current_key and current_list:
                data[current_key] = current_list
                current_list = []

        if ":" in stripped:
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            if value:
                data[current_key] = value
            else:
                data[current_key] = []

    if current_key and current_list:
        data[current_key] = current_list

    # 类型修正
    if "completed_steps" in data and isinstance(data["completed_steps"], list):
        data["completed_steps"] = [str(s) for s in data["completed_steps"]]

    required = {"flow", "current_step", "completed_steps"}
    if not required.issubset(data.keys()):
        return None

    return data


def save_progress(
    flow: str,
    current_step: str,
    completed_steps: List[str],
    progress_file: Optional[str] = None,
) -> None:
    """保存进度到 progress.md。"""
    path = progress_file or _default_progress_path()
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")

    completed_lines = "\n".join(f"  - {s}" for s in completed_steps) or "  - "

    content = f"""---
flow: {flow}
current_step: {current_step}
completed_steps:
{completed_lines}
last_updated: {now}
---

# PDCA减脂分析执行进度

本文件由 `scripts/progress_store.py` 自动维护，用于会话中断后恢复。
请勿手动修改。
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def mark_step_done(
    flow: str,
    step_id: str,
    progress_file: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """将某步骤标记为已完成，并返回更新后的进度。

    如果当前进度不存在，会创建一个新的进度对象。
    """
    progress = load_progress(progress_file) or {
        "flow": flow,
        "current_step": step_id,
        "completed_steps": [],
    }

    if progress["flow"] != flow:
        raise ValueError(f"进度流程不匹配: 当前 {progress['flow']}，请求 {flow}")

    completed = list(progress.get("completed_steps", []))
    if step_id not in completed:
        completed.append(step_id)

    progress["completed_steps"] = completed
    progress["current_step"] = step_id
    save_progress(flow, step_id, completed, progress_file)
    return progress


def clear_progress(progress_file: Optional[str] = None) -> None:
    """清除进度文件。"""
    path = progress_file or _default_progress_path()
    if os.path.isfile(path):
        os.remove(path)


def is_step_completed(
    flow: str,
    step_id: str,
    progress_file: Optional[str] = None,
) -> bool:
    """判断某步骤是否已完成。"""
    progress = load_progress(progress_file)
    if progress is None:
        return False
    return step_id in progress.get("completed_steps", [])


def get_next_step(flow: str, progress_file: Optional[str] = None) -> Optional[str]:
    """根据当前进度获取下一个待执行步骤。

    如果当前步骤是最后一个，返回 None。
    """
    progress = load_progress(progress_file)
    if progress is None:
        all_ids = list_step_ids(flow)
        return all_ids[0] if all_ids else None

    current = progress.get("current_step")
    all_ids = list_step_ids(flow)
    if current not in all_ids:
        return all_ids[0] if all_ids else None

    idx = all_ids.index(current)
    if idx + 1 < len(all_ids):
        return all_ids[idx + 1]
    return None


if __name__ == "__main__":
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("""---
flow: init
current_step: init_3
completed_steps:
  - init_1
  - init_2
last_updated: 2026-09-02T14:30:00+08:00
---
""")
        tmp = f.name

    p = load_progress(tmp)
    print("loaded:", p)
    mark_step_done("init", "init_4", tmp)
    print("after mark:", load_progress(tmp))
    clear_progress(tmp)
    print("exists after clear:", os.path.exists(tmp))
    os.remove(tmp)
