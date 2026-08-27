from pathlib import Path
from typing import Optional


def save_progress(output_dir: Path, stage: str, decisions: dict, risks: list):
    """保存当前进度到 output_dir/<article_id>/progress.md。"""
    progress_file = output_dir / "progress.md"
    lines = [f"# 写作进度\n", f"\n当前阶段：{stage}\n", "\n## 关键决策\n"]
    for key, value in decisions.items():
        lines.append(f"- {key}: {value}\n")
    lines.append("\n## 风险点\n")
    for risk in risks:
        lines.append(f"- {risk}\n")
    progress_file.write_text("".join(lines), encoding="utf-8")


def save_blocked(output_dir: Path, items: list):
    """保存阻塞项到 output_dir/<article_id>/blocked.md。"""
    blocked_file = output_dir / "blocked.md"
    lines = ["# 等待确认/补充\n\n"]
    for item in items:
        lines.append(f"- [ ] {item}\n")
    blocked_file.write_text("".join(lines), encoding="utf-8")


def load_progress(output_dir: Path) -> Optional[dict]:
    """读取 output_dir/<article_id>/progress.md，返回解析后的进度信息。"""
    progress_file = output_dir / "progress.md"
    if not progress_file.exists():
        return None

    content = progress_file.read_text(encoding="utf-8")
    result = {"stage": "", "decisions": {}, "risks": []}
    section = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("当前阶段："):
            result["stage"] = stripped.replace("当前阶段：", "").strip()
        elif stripped == "## 关键决策":
            section = "decisions"
        elif stripped == "## 风险点":
            section = "risks"
        elif stripped.startswith("- ") and section:
            item = stripped[2:]
            if section == "decisions" and ":" in item:
                key, value = item.split(":", 1)
                result["decisions"][key.strip()] = value.strip()
            elif section == "risks":
                result["risks"].append(item)
    return result


def load_blocked(output_dir: Path) -> list:
    """读取 output_dir/<article_id>/blocked.md，返回等待确认/补充的项列表。"""
    blocked_file = output_dir / "blocked.md"
    if not blocked_file.exists():
        return []

    items = []
    for line in blocked_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ] "):
            items.append(stripped[6:])
        elif stripped.startswith("- "):
            items.append(stripped[2:])
    return items
