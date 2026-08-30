#!/usr/bin/env python3
"""progress_reporter.py — 渲染 write-verify micro-checklist。

输入 JSON：
{
  "stage": "VALIDATE",
  "artifacts_status": {
    "write_request": "ready",
    "header_map": "ready",
    "coerced_values": "missing"
  }
}

输出：Markdown checklist 字符串。
"""
import json
import sys
from typing import Any, Dict


STAGE_STEPS = {
    "LOAD_DEFS": [
        ("write_request", "接收写入请求"),
        ("header_map", "读取表头并建立字段名→列字母映射"),
        ("column_constraints", "读取列格式与数据验证"),
    ],
    "VALIDATE": [
        ("validated_values", "字段元数据类型校验"),
        ("coerced_values", "真实列约束转换"),
        ("existing_values", "字段已有值检查"),
    ],
    "WRITE": [
        ("write_plan", "构造批量写入请求"),
        ("write_response", "执行写入"),
        ("verify_result", "回读校验"),
    ],
    "REPORT": [
        ("write_result", "汇总写入结果"),
    ],
}


def _status_icon(status: str) -> str:
    if status == "ready":
        return "✓"
    if status == "failed":
        return "✗"
    return " "


def progress_reporter(payload: Dict[str, Any]) -> str:
    stage = payload.get("stage", "LOAD_DEFS")
    artifacts_status = payload.get("artifacts_status", {})

    lines = [f"✍️ write-verify 当前阶段：{stage}", ""]
    lines.append("Progress:")

    for step_key, step_name in STAGE_STEPS.get(stage, []):
        status = artifacts_status.get(step_key, "missing")
        icon = _status_icon(status)
        marker = "  ← 当前" if status != "ready" else ""
        lines.append(f"- [{icon}] {step_name} [{status}]{marker}")

    missing = [k for k, v in artifacts_status.items() if v == "missing"]
    if missing:
        lines.append("")
        lines.append(f"⚠️ 当前阻塞：缺少产物 {', '.join(missing)}")

    return "\n".join(lines)


def main() -> None:
    payload = json.load(sys.stdin)
    print(progress_reporter(payload))


if __name__ == "__main__":
    main()
