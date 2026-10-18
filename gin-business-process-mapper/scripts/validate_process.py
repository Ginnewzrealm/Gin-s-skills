#!/usr/bin/env python3
"""Validate the structured source used by both process outputs."""

import json
import re
import sys
from pathlib import Path

PROCESS_FIELDS = {
    "process_id", "process_name", "purpose", "scope_start", "scope_end",
    "participants", "systems_and_channels", "nodes", "edges",
    "open_questions", "future_expectations", "sources", "version", "status",
}
NODE_FIELDS = {
    "id", "name", "business_fact", "actor", "execution_mode", "carrier",
    "carrier_name", "entry_or_signal", "business_action", "interface_implications",
    "inputs", "outputs", "completion_signal", "state_before", "state_after",
    "rules", "exceptions", "evidence_status", "evidence_refs",
}
EDGE_FIELDS = {"from", "to", "label", "condition", "kind", "evidence_status", "evidence_refs"}
EVIDENCE_STATUSES = {"confirmed", "inferred", "unknown"}
EXECUTION_MODES = {"manual", "automatic", "assisted"}
CARRIERS = {"system", "chat", "email", "spreadsheet", "paper", "onsite", "other"}
EDGE_KINDS = {"normal", "decision", "exception", "timeout", "cancel", "rework"}


def _missing(item, required):
    return sorted(field for field in required if field not in item)


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["流程数据必须是 JSON 对象"]

    for field in _missing(data, PROCESS_FIELDS):
        errors.append(f"缺少流程字段：{field}")
    for field in ("process_id", "process_name", "scope_start", "scope_end"):
        if field in data and not str(data[field]).strip():
            errors.append(f"流程字段不能为空：{field}")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status 只能是 draft 或 confirmed")

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 必须是非空数组")
        nodes = []
    ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    duplicates = sorted({node_id for node_id in ids if node_id and ids.count(node_id) > 1})
    if duplicates:
        errors.append(f"节点 ID 重复：{', '.join(duplicates)}")

    expected_ids = [f"N{index:02d}" for index in range(1, len(nodes) + 1)]
    if ids != expected_ids:
        errors.append(f"节点 ID 必须从 N01 开始连续排列，预期 {expected_ids}，实际 {ids}")

    source_ids = {source.get("id") for source in data.get("sources", []) if isinstance(source, dict)}
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index - 1}] 必须是对象")
            continue
        node_id = node.get("id", f"nodes[{index - 1}]")
        for field in _missing(node, NODE_FIELDS):
            errors.append(f"{node_id} 缺少字段：{field}")
        if node.get("execution_mode") not in EXECUTION_MODES:
            errors.append(f"{node_id} execution_mode 无效")
        if node.get("carrier") not in CARRIERS:
            errors.append(f"{node_id} carrier 无效")
        if node.get("evidence_status") not in EVIDENCE_STATUSES:
            errors.append(f"{node_id} evidence_status 无效")
        refs = node.get("evidence_refs", [])
        if node.get("evidence_status") == "confirmed" and not refs:
            errors.append(f"{node_id} 已确认事实必须包含 evidence_refs")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{node_id} 引用了不存在的证据：{ref}")

    valid_ids = set(ids)
    for index, edge in enumerate(data.get("edges", [])):
        label = f"edges[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{label} 必须是对象")
            continue
        for field in _missing(edge, EDGE_FIELDS):
            errors.append(f"{label} 缺少字段：{field}")
        for endpoint in ("from", "to"):
            if edge.get(endpoint) not in valid_ids:
                errors.append(f"{label}.{endpoint} 引用了不存在的节点：{edge.get(endpoint)}")
        if edge.get("kind") not in EDGE_KINDS:
            errors.append(f"{label} kind 无效")
        if edge.get("evidence_status") not in EVIDENCE_STATUSES:
            errors.append(f"{label} evidence_status 无效")
        for ref in edge.get("evidence_refs", []):
            if ref not in source_ids:
                errors.append(f"{label} 引用了不存在的证据：{ref}")

    return errors


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("用法：validate_process.py <process.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取流程数据：{exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("流程数据验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
