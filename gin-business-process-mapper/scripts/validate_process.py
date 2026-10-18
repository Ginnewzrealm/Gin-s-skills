#!/usr/bin/env python3
"""Validate the structured source used by both process outputs."""

import json
import re
import sys
from pathlib import Path

PROCESS_FIELDS = {
    "process_id", "process_name", "purpose", "scope_start", "scope_end",
    "participants", "systems_and_channels", "nodes", "edges", "scenes",
    "open_questions", "future_expectations", "sources", "version", "status",
}
NODE_FIELDS = {
    "id", "name", "kind", "business_fact", "actor_role", "execution_mode", "carrier",
    "carrier_name", "entry_or_signal", "business_action", "software_location",
    "software_operation", "interface_implications",
    "inputs", "outputs", "completion_signal", "state_before", "state_after",
    "rules", "exceptions", "evidence_status", "evidence_refs",
}
EDGE_FIELDS = {"id", "from", "to", "label", "condition", "kind", "evidence_status", "evidence_refs"}
SCENE_FIELDS = {"id", "name", "type", "owner_roles", "edge_ids", "boundary_rule"}
EVIDENCE_STATUSES = {"confirmed", "inferred", "unknown"}
EXECUTION_MODES = {"manual", "automatic", "assisted"}
CARRIERS = {"system", "chat", "email", "spreadsheet", "paper", "onsite", "other"}
EDGE_KINDS = {"normal", "decision", "exception", "timeout", "cancel", "rework"}
NODE_KINDS = {"start", "action", "decision", "end"}
SCENE_TYPES = {"main", "exception", "variant"}
DECISION_FIELDS = {"decider_role", "criteria", "fallback"}
VAGUE_PHRASES = {"处理", "跟进", "对接", "协调", "弄一下", "看情况", "及时", "尽快", "完善", "优化"}


def _missing(item, required):
    return sorted(field for field in required if field not in item)


def _has_cycle(node_ids, edges):
    outgoing = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("kind") in {"rework", "cancel"}:
            continue
        if edge.get("from") in outgoing and edge.get("to") in outgoing:
            outgoing[edge["from"]].append(edge["to"])
    visiting, visited = set(), set()

    def visit(node_id):
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        if any(visit(target) for target in outgoing.get(node_id, [])):
            return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in node_ids)


def _is_vague(value):
    text = re.sub(r"[，。；、,.\s]", "", str(value or ""))
    return any(phrase in text for phrase in VAGUE_PHRASES)


def lint(data):
    """Return non-blocking interview-quality warnings."""
    warnings = []
    for node in data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if _is_vague(node.get("business_action")):
            warnings.append(f"{node.get('id', '节点')} business_action 表达过于模糊，需要继续访谈")
        for criterion in node.get("criteria", []):
            if _is_vague(criterion):
                warnings.append(f"{node.get('id', '节点')} criteria 表达过于模糊，需要继续访谈")
        if node.get("kind") == "decision" and _is_vague(node.get("fallback")):
            warnings.append(f"{node.get('id', '节点')} fallback 表达过于模糊，需要继续访谈")
    for scene in data.get("scenes", []):
        if isinstance(scene, dict) and _is_vague(scene.get("boundary_rule")):
            warnings.append(f"{scene.get('id', '场景')} boundary_rule 表达过于模糊，需要继续访谈")
    return warnings


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
        if node.get("kind") not in NODE_KINDS:
            errors.append(f"{node_id} kind 无效")
        if node.get("kind") == "decision":
            for field in _missing(node, DECISION_FIELDS):
                errors.append(f"{node_id} 决策节点缺少字段：{field}")
            if "criteria" in node and (not isinstance(node["criteria"], list) or not node["criteria"]):
                errors.append(f"{node_id} 决策节点 criteria 必须是非空数组")
        if node.get("evidence_status") not in EVIDENCE_STATUSES:
            errors.append(f"{node_id} evidence_status 无效")
        refs = node.get("evidence_refs", [])
        if node.get("evidence_status") == "confirmed" and not refs:
            errors.append(f"{node_id} 已确认事实必须包含 evidence_refs")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{node_id} 引用了不存在的证据：{ref}")

    valid_ids = set(ids)
    edges = data.get("edges", [])
    edge_ids = [edge.get("id") for edge in edges if isinstance(edge, dict)]
    duplicate_edge_ids = sorted({edge_id for edge_id in edge_ids if edge_id and edge_ids.count(edge_id) > 1})
    if duplicate_edge_ids:
        errors.append(f"连线 ID 重复：{', '.join(duplicate_edge_ids)}")
    for index, edge in enumerate(edges):
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
        refs = edge.get("evidence_refs", [])
        if data.get("status") == "confirmed" and edge.get("evidence_status") == "confirmed" and not refs:
            errors.append(f"{label} 已确认事实必须包含 evidence_refs")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{label} 引用了不存在的证据：{ref}")

    outgoing = {}
    for edge in edges:
        if isinstance(edge, dict):
            outgoing.setdefault(edge.get("from"), []).append(edge)
    for node in nodes:
        if not isinstance(node, dict) or node.get("kind") != "decision":
            continue
        decision_edges = outgoing.get(node.get("id"), [])
        conditions = [str(edge.get("condition", "")).strip() for edge in decision_edges]
        if len(decision_edges) < 2:
            errors.append(f"{node.get('id')} 决策节点至少需要两条出边")
        if any(not condition for condition in conditions) or len(set(conditions)) != len(conditions):
            errors.append(f"{node.get('id')} 决策出边必须包含不同条件")

    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes 必须是非空数组")
        scenes = []
    valid_edge_ids = set(edge_ids)
    covered_edge_ids = set()
    edge_owners = {}
    has_main = False
    for index, scene in enumerate(scenes):
        label = f"scenes[{index}]"
        if not isinstance(scene, dict):
            errors.append(f"{label} 必须是对象")
            continue
        for field in _missing(scene, SCENE_FIELDS):
            errors.append(f"{label} 缺少字段：{field}")
        if scene.get("type") not in SCENE_TYPES:
            errors.append(f"{label} type 无效")
        has_main = has_main or scene.get("type") == "main"
        for edge_id in scene.get("edge_ids", []):
            if edge_id not in valid_edge_ids:
                errors.append(f"{label} 引用了不存在的连线：{edge_id}")
            covered_edge_ids.add(edge_id)
            edge_owners.setdefault(edge_id, []).append(scene.get("id", label))
            edge = next((item for item in edges if isinstance(item, dict) and item.get("id") == edge_id), None)
            if scene.get("type") == "main" and edge and edge.get("kind") in {"exception", "rework", "cancel", "timeout"}:
                errors.append(f"{label} 主场景不能包含异常、返工、取消或超时连线：{edge_id}")
        if scene.get("type") != "main" and not str(scene.get("boundary_rule", "")).strip():
            errors.append(f"{label} 非主场景必须填写 boundary_rule")
    if scenes and not has_main:
        errors.append("scenes 至少包含一个 main 场景")
    for edge_id, owners in edge_owners.items():
        if len(owners) > 1:
            errors.append(f"连线 {edge_id} 只能归属一个场景，当前归属：{', '.join(owners)}")
    if data.get("status") == "confirmed":
        uncovered = sorted(valid_edge_ids - covered_edge_ids)
        if uncovered:
            errors.append(f"终稿连线未归属场景：{', '.join(uncovered)}")
    if _has_cycle(valid_ids, edges):
        errors.append("普通流程边不能形成循环；返工或取消请使用 rework/cancel")

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
    warnings = lint(data)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("流程数据验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
