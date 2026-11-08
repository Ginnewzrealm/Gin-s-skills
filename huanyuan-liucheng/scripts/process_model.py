#!/usr/bin/env python3
# Copyright (c) 2026 Gin. All rights reserved.
# Proprietary material. See LICENSE in the skill root.
"""Validate and render a business-process decision model."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


NODE_TYPES = {"start", "action", "decision", "join", "unresolved", "terminal"}
STATUS_TYPES = {"confirmed", "unresolved", "inferred"}
CONFIRMATION_TYPES = {"pending", "confirmed"}


class ModelError(ValueError):
    pass


def load_model(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ModelError(f"找不到模型文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ModelError(f"JSON 格式错误（第 {exc.lineno} 行）：{exc.msg}") from exc
    if not isinstance(data, dict):
        raise ModelError("模型顶层必须是 JSON 对象")
    return data


def require_text(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{location} 必须是非空文字")


def validate_evidence(model: dict[str, Any], errors: list[str]) -> tuple[dict, dict]:
    """Check traceability, not whether a quotation logically proves a claim."""
    materials: dict[str, str] = {}
    values = model.get("source_materials")
    if not isinstance(values, list) or not values:
        errors.append("source_materials 至少需要一份原始文字资料")
    else:
        for index, item in enumerate(values):
            location = f"source_materials[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{location} 必须是对象")
                continue
            for field in ("id", "text"):
                require_text(item.get(field), f"{location}.{field}", errors)
            if isinstance(item.get("id"), str) and isinstance(item.get("text"), str):
                if item["id"] in materials:
                    errors.append(f"资料 id 重复：{item['id']}")
                materials[item["id"]] = item["text"]
    registry: dict[str, dict] = {}
    evidence = model.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence 至少需要一条原文证据")
    else:
        for index, item in enumerate(evidence):
            location = f"evidence[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{location} 必须是对象")
                continue
            for field in ("id", "source_id", "quote"):
                require_text(item.get(field), f"{location}.{field}", errors)
            if item.get("kind") not in {"current", "goal", "rule", "unclear", "user_confirmation"}:
                errors.append(f"{location}.kind 必须区分现状、目标、制度、未知或用户确认")
            source_id = item.get("source_id")
            if not isinstance(source_id, str) or source_id not in materials:
                errors.append(f"{location}.source_id 指向不存在的原始资料")
            elif isinstance(item.get("quote"), str) and item["quote"] not in materials[source_id]:
                errors.append(f"{location}.quote 与原始资料不匹配")
            evidence_id = item.get("id")
            if isinstance(evidence_id, str) and evidence_id:
                if evidence_id in registry:
                    errors.append(f"证据 id 重复：{evidence_id}")
                registry[evidence_id] = item
    return materials, registry


def require_refs(value: Any, location: str, registry: dict, errors: list[str], *,
                 required: bool = True, current: bool = True) -> None:
    if not isinstance(value, list):
        errors.append(f"{location} 必须是证据 ID 数组")
        return
    if required and not value:
        errors.append(f"{location} 至少需要一条原文依据")
    referenced = []
    for reference in value:
        if not isinstance(reference, str) or reference not in registry:
            errors.append(f"{location} 引用了不存在的证据：{reference}")
        else:
            referenced.append(registry[reference])
    if current and referenced and not any(item.get("kind") in {"current", "user_confirmation"} for item in referenced):
        errors.append(f"{location} 不能只用预期目标、制度要求或未知说法证明当前事实")


def validate_confirmation(confirmation: dict, materials: dict, errors: list[str]) -> None:
    presented = confirmation.get("presented")
    if not isinstance(presented, dict):
        errors.append("confirmation.presented 必须记录向用户展示的确认内容")
        presented = {}
    for field in ("current_facts", "excluded_goals", "process_boundaries", "decisions"):
        value = presented.get(field)
        if not isinstance(value, list):
            errors.append(f"confirmation.presented.{field} 必须是文字数组；没有时显式记录空数组")
        else:
            for index, text in enumerate(value):
                require_text(text, f"confirmation.presented.{field}[{index}]", errors)
    if not isinstance(confirmation.get("accepted_unknowns"), bool):
        errors.append("confirmation.accepted_unknowns 必须明确是否允许保留待确认项")
    if confirmation.get("status") == "confirmed":
        if confirmation.get("response_kind") != "approval":
            errors.append("confirmation.response_kind 必须为 approval；仅纠正信息不等于同意生成")
        require_text(confirmation.get("user_reply"), "confirmation.user_reply", errors)
        source_id = confirmation.get("user_reply_source_id")
        if not isinstance(source_id, str) or source_id not in materials:
            errors.append("confirmation.user_reply_source_id 必须指向用户实际回复")
        elif isinstance(confirmation.get("user_reply"), str) and confirmation["user_reply"] not in materials[source_id]:
            errors.append("confirmation.user_reply 与记录的用户回复不匹配")


def validate_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if 'processes' in model:
        errors.append('一次只能还原一个流程；请先选定单个 process，不接收流程集合 processes')
    if model.get('known_fragments'):
        errors.append('不要提交碎片流程 known_fragments；把未定位的已知动作及证据写入对应问题的 known_facts')
    require_text(model.get("schema_version"), "schema_version", errors)
    if model.get("schema_version") != "3.0":
        errors.append("schema_version 必须是 3.0")
    require_text(model.get("company"), "company", errors)

    confirmation = model.get("confirmation")
    if not isinstance(confirmation, dict):
        errors.append("confirmation 必须是对象")
        confirmation = {}
    if confirmation.get("status") not in CONFIRMATION_TYPES:
        errors.append("confirmation.status 只能是 pending 或 confirmed")
    require_text(confirmation.get("scope_summary"), "confirmation.scope_summary", errors)

    materials, evidence = validate_evidence(model, errors)
    validate_confirmation(confirmation, materials, errors)

    process = model.get("process")
    if not isinstance(process, dict):
        errors.append("process 必须是对象")
        process = {}
    for field in (
        "number",
        "name",
        "status",
        "business_object",
        "trigger",
        "end_state",
        "boundary_reason",
    ):
        require_text(process.get(field), f"process.{field}", errors)
    if process.get("status") not in {"draft", "confirmed"}:
        errors.append("process.status 只能是 draft 或 confirmed")

    nodes = model.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 必须是非空数组")
        return errors

    ids: list[str] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] 必须是对象")
            continue
        node_id = node.get("id")
        require_text(node_id, f"nodes[{index}].id", errors)
        if isinstance(node_id, str) and node_id:
            ids.append(node_id)
        node_type = node.get("type")
        if node_type not in NODE_TYPES:
            errors.append(f"{node_id or f'nodes[{index}]'}: type 必须是 {sorted(NODE_TYPES)} 之一")
            continue

        if "next" in node and node_type not in {"start", "action", "join"}:
            errors.append(f"{node_id}.next 不适用于 {node_type} 节点")
        if "branches" in node and node_type != "decision":
            errors.append(f"{node_id}.branches 只能用于 decision 节点")

        if node_type in {"start", "action", "join", "unresolved", "terminal"}:
            require_text(node.get("label"), f"{node_id}.label", errors)
        if node_type in {"start", "action", "join"}:
            require_text(node.get("next"), f"{node_id}.next", errors)
        if node_type == "action":
            require_text(node.get("owner"), f"{node_id}.owner", errors)
        if node_type == "decision":
            if not isinstance(node_id, str) or not re.fullmatch(r"D\d{2}", node_id):
                errors.append(f"{node_id}: 决策节点 id 必须使用 D01 形式")
            for field in ("owner", "title", "question"):
                require_text(node.get(field), f"{node_id}.{field}", errors)
            inputs = node.get("inputs")
            if not isinstance(inputs, list) or not inputs:
                errors.append(f"{node_id}.inputs 至少需要一项判断信息")
            else:
                for item_index, item in enumerate(inputs):
                    require_text(item, f"{node_id}.inputs[{item_index}]", errors)

            criteria = node.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                errors.append(f"{node_id}.criteria 至少需要一项判断标准")
            else:
                for criterion_index, criterion in enumerate(criteria):
                    location = f"{node_id}.criteria[{criterion_index}]"
                    if not isinstance(criterion, dict):
                        errors.append(f"{location} 必须是对象")
                        continue
                    require_text(criterion.get("text"), f"{location}.text", errors)
                    if criterion.get("status") not in STATUS_TYPES:
                        errors.append(f"{location}.status 必须是 confirmed、unresolved 或 inferred")
                    require_text(criterion.get("evidence"), f"{location}.evidence", errors)

            branches = node.get("branches")
            branches_complete = node.get("branches_complete", True)
            if not isinstance(branches_complete, bool):
                errors.append(f"{node_id}.branches_complete 必须是布尔值")
            if not isinstance(branches, list):
                errors.append(f"{node_id}.branches 必须是数组")
            else:
                if branches_complete and len(branches) < 2:
                    errors.append(f"{node_id}.branches 完整决策至少需要两个分支；资料未说全时设置 branches_complete=false 并提问")
                primary_count = 0
                for branch_index, branch in enumerate(branches):
                    location = f"{node_id}.branches[{branch_index}]"
                    if not isinstance(branch, dict):
                        errors.append(f"{location} 必须是对象")
                        continue
                    for field in ("label", "condition", "target"):
                        require_text(branch.get(field), f"{location}.{field}", errors)
                    if branch.get("status") not in STATUS_TYPES:
                        errors.append(f"{location}.status 必须是 confirmed、unresolved 或 inferred")
                    if not isinstance(branch.get("primary"), bool):
                        errors.append(f"{location}.primary 必须是布尔值")
                    elif branch["primary"]:
                        primary_count += 1
                if primary_count != (1 if branches else 0):
                    errors.append(f"{node_id}.branches 非空时必须且只能有一个 primary=true 分支")

    duplicate_ids = sorted({node_id for node_id in ids if ids.count(node_id) > 1})
    if duplicate_ids:
        errors.append(f"节点 id 重复：{', '.join(duplicate_ids)}")

    node_map = {
        node["id"]: node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("id")
    }
    if confirmation.get("status") == "confirmed":
        presented = confirmation.get("presented", {})
        if isinstance(presented, dict):
            for field in ("current_facts", "process_boundaries"):
                if not presented.get(field):
                    errors.append(f"confirmation.presented.{field} 不能省略已展示的事实与范围")
            if any(node.get("type") == "decision" for node in node_map.values()) and not presented.get("decisions"):
                errors.append("confirmation.presented.decisions 必须记录已向用户确认的关键决策")
    starts = [node for node in node_map.values() if node.get("type") == "start"]
    if len(starts) != 1:
        errors.append(f"必须且只能有一个 start 节点，当前为 {len(starts)} 个")

    for node_id, node in node_map.items():
        targets: list[str] = []
        if node.get("type") in {"start", "action", "join"} and isinstance(node.get("next"), str):
            targets.append(node["next"])
        if node.get("type") == "decision" and isinstance(node.get("branches"), list):
            targets.extend(
                branch.get("target")
                for branch in node["branches"]
                if isinstance(branch, dict) and isinstance(branch.get("target"), str)
            )
        for target in targets:
            if target not in node_map:
                errors.append(f"{node_id} 指向不存在的节点 {target}")

    if len(starts) == 1 and not errors:
        reached: set[str] = set()
        active: set[str] = set()

        def walk(node_id: str, back_edge: bool = False) -> None:
            if back_edge:
                return
            if node_id in active:
                errors.append(f"检测到未声明的流程环：{node_id}")
                return
            if node_id in reached:
                return
            reached.add(node_id)
            active.add(node_id)
            node = node_map[node_id]
            if node["type"] in {"start", "action", "join"}:
                walk(node["next"], node.get("back_edge", False))
            elif node["type"] == "decision":
                for branch in node["branches"]:
                    walk(branch["target"], branch.get("back_edge", False))
            active.remove(node_id)

        walk(starts[0]["id"])
        unreachable = sorted(set(node_map) - reached)
        if unreachable:
            errors.append(f"存在从起点不可达的节点：{', '.join(unreachable)}")

    pending = model.get("pending_questions")
    if not isinstance(pending, list):
        errors.append("pending_questions 必须是数组；没有待确认项时使用空数组")
    else:
        question_ids: list[str] = []
        for index, question in enumerate(pending):
            location = f"pending_questions[{index}]"
            if not isinstance(question, dict):
                errors.append(f"{location} 必须是对象")
                continue
            question_id = question.get("id")
            require_text(question_id, f"{location}.id", errors)
            if isinstance(question_id, str) and question_id:
                question_ids.append(question_id)
                if not re.fullmatch(r"Q\d{2}", question_id):
                    errors.append(f"{location}.id 必须使用 Q01 形式")
            require_text(question.get("text"), f"{location}.text", errors)
            facts = question.get('known_facts', [])
            if not isinstance(facts, list):
                errors.append(f'{location}.known_facts 必须是事实数组')
            else:
                for fact_index, fact in enumerate(facts):
                    fact_location = f'{location}.known_facts[{fact_index}]'
                    if not isinstance(fact, dict):
                        errors.append(f'{fact_location} 必须包含 text 与 evidence_refs')
                        continue
                    require_text(fact.get('text'), f'{fact_location}.text', errors)
                    require_refs(fact.get('evidence_refs'), f'{fact_location}.evidence_refs', evidence, errors)
            related = question.get("related_nodes")
            if not isinstance(related, list) or not related:
                errors.append(f"{location}.related_nodes 至少需要一个关联节点")
            else:
                for related_index, related_node in enumerate(related):
                    require_text(related_node, f"{location}.related_nodes[{related_index}]", errors)
                    if isinstance(related_node, str) and related_node not in node_map:
                        errors.append(f"{location} 引用了不存在的节点 {related_node}")
        duplicate_question_ids = sorted(
            {question_id for question_id in question_ids if question_ids.count(question_id) > 1}
        )
        if duplicate_question_ids:
            errors.append(f"待确认问题 id 重复：{', '.join(duplicate_question_ids)}")

    questioned_nodes = {
        node_id for question in pending if isinstance(question, dict)
        for node_id in question.get("related_nodes", []) if isinstance(node_id, str)
    } if isinstance(pending, list) else set()
    uncertain_nodes: set[str] = set()
    for node_id, node in node_map.items():
        node_type = node.get("type")
        if node_type in {"start", "action", "decision", "terminal"}:
            require_refs(node.get("evidence_refs"), f"{node_id}.evidence_refs", evidence, errors)
        if node_type in {"start", "action", "join"}:
            target = node_map.get(node.get("next"), {})
            if node.get('next_status', 'confirmed') not in STATUS_TYPES:
                errors.append(f'{node_id}.next_status 必须区分 confirmed、unresolved 或 inferred')
            if node.get('next_status', 'confirmed') != 'confirmed':
                uncertain_nodes.add(node_id)
            require_refs(node.get("next_evidence_refs"), f"{node_id}.next_evidence_refs", evidence, errors,
                         required=target.get("type") != "unresolved")
            if target.get("type") == "unresolved":
                uncertain_nodes.add(node_id)
        if "back_edge" in node and not isinstance(node["back_edge"], bool):
            errors.append(f"{node_id}.back_edge 必须是布尔值")
        if node.get("back_edge"):
            require_refs(node.get("next_evidence_refs"), f"{node_id}.next_evidence_refs", evidence, errors)
        if node_type == "unresolved":
            uncertain_nodes.add(node_id)
        if node_type == "decision" and node.get("branches_complete", True) is False:
            uncertain_nodes.add(node_id)
        for index, criterion in enumerate(node.get("criteria", [])):
            if not isinstance(criterion, dict):
                continue
            location = f"{node_id}.criteria[{index}]"
            known = criterion.get("status") == "confirmed"
            require_refs(criterion.get("evidence_refs"), f"{location}.evidence_refs", evidence, errors,
                         required=known, current=known)
            if not known:
                uncertain_nodes.add(node_id)
        for index, branch in enumerate(node.get("branches", [])):
            if not isinstance(branch, dict):
                continue
            location = f"{node_id}.branches[{index}]"
            require_refs(branch.get("evidence_refs"), f"{location}.evidence_refs", evidence, errors)
            for field in ("condition_status", "target_status"):
                if branch.get(field) not in STATUS_TYPES:
                    errors.append(f"{location}.{field} 必须区分 confirmed、unresolved 或 inferred")
            known = all(branch.get(field) == "confirmed" for field in ("condition_status", "target_status"))
            if (branch.get("status") == "confirmed") != known:
                errors.append(f"{location}.status 与条件/去向状态不一致")
            target = node_map.get(branch.get("target"), {})
            if target.get("type") == "unresolved" and branch.get("target_status") == "confirmed":
                errors.append(f"{location}.target_status 不能把未知去向标成 confirmed")
            if "back_edge" in branch and not isinstance(branch["back_edge"], bool):
                errors.append(f"{location}.back_edge 必须是布尔值")
            if not known:
                uncertain_nodes.add(node_id)
    for node_id in sorted(uncertain_nodes - questioned_nodes):
        errors.append(f"{node_id} 存在未知内容，必须关联待确认问题")
    if process.get("status") == "confirmed" and (uncertain_nodes or pending):
        errors.append("process.status 不能为 confirmed：仍有待确认内容")
    if confirmation.get("status") == "confirmed" and (uncertain_nodes or pending) and confirmation.get("accepted_unknowns") is not True:
        errors.append("confirmation.accepted_unknowns：用户尚未允许保留未知项生成草案")

    sources = model.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources 至少需要一项资料来源")
    else:
        for index, source in enumerate(sources):
            require_text(source, f"sources[{index}]", errors)

    return errors


def has_unresolved(model: dict[str, Any]) -> bool:
    if model.get("confirmation", {}).get("status") != "confirmed":
        return True
    if model.get("process", {}).get("status") != "confirmed":
        return True
    if model.get("pending_questions"):
        return True
    for node in model.get("nodes", []):
        if node.get("type") == "unresolved":
            return True
        if node.get("type") == "decision" and node.get("branches_complete", True) is False:
            return True
        for item in node.get("criteria", []):
            if item.get("status") != "confirmed":
                return True
        for branch in node.get("branches", []):
            if branch.get("status") != "confirmed":
                return True
    return False


def index_nodes(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in model["nodes"]}


def status_text(status: str) -> str:
    return {"confirmed": "已确认", "unresolved": "待确认", "inferred": "推断"}.get(status, status)


def render_tree(model: dict[str, Any]) -> str:
    """Expand the whole process once; only real merges and returns use references."""
    nodes = index_nodes(model)
    start = next(node for node in model["nodes"] if node["type"] == "start")
    expanded: set[str] = set()

    def draw(node_id: str, path: frozenset[str]) -> list[str]:
        node = nodes[node_id]
        node_type = node["type"]
        name = node.get('label', node.get('question', ''))
        if node_id in path:
            return [f'↩ 返回 {node_id} {name}']
        if node_id in expanded:
            return [f'↪ 汇入 {node_id} {name}']
        expanded.add(node_id)
        next_path = path | {node_id}
        symbol = {'decision':'◆ ', 'join':'＋ ', 'unresolved':'… ', 'terminal':'● '}.get(node_type, '')
        owner = f"{node['owner']}：" if node_type == 'action' else ''
        rows = [f'{symbol}{node_id} {owner}{name}']
        if node_type in {'start', 'action', 'join'}:
            child = draw(node['next'], next_path)
            if node.get('next_note'):
                rows.extend(['│', f"衔接：{node['next_note']}"])
            elif node.get('next_status', 'confirmed') != 'confirmed':
                rows.extend(['│', '衔接待核'])
            elif nodes[node['next']]['type'] in {'decision','join'}:
                rows.append('│')
            else:
                child[0] = ('↓ ' if not child[0].startswith(('↪','↩')) else '') + child[0]
            rows.extend(child)
        elif node_type == 'decision':
            children = []
            for branch in node['branches']:
                child = draw(branch['target'], next_path)
                labels = [f"【{branch['label']}】"]
                if branch['condition_status'] != 'confirmed':
                    labels[0] += f"〔条件：{status_text(branch['condition_status'])}〕"
                if branch['condition'] != branch['label']:
                    labels.append('条件：'+branch['condition'])
                target_notes = []
                if branch['target_status'] != 'confirmed':
                    target_notes.append('去向：'+status_text(branch['target_status']))
                if branch.get('path_note'):
                    target_notes.append(branch['path_note'])
                if target_notes:
                    child[0] += '〔'+'；'.join(target_notes)+'〕'
                children.append((labels, child))
            if children:
                rows.append('│')
            for index, (labels, child) in enumerate(children):
                last = index == len(children)-1
                fork, continuation = ('└─','   ') if last else ('├─','│  ')
                if len(labels) == len(child) == 1:
                    rows.append(fork+labels[0]+(' ' if child[0].startswith(('↪','↩')) else ' → ')+child[0])
                else:
                    rows.append(fork+labels[0])
                    rows.extend(continuation+text for text in labels[1:])
                    rows.append(continuation+'└─ '+child[0])
                    rows.extend(continuation+'   '+text for text in child[1:])
                if not last and (len(labels)+len(child)>2 or sum(map(len,children[index+1]))>2):
                    rows.append('│')
        return rows

    return '\n'.join(draw(start['id'], frozenset()))


def render_markdown(model: dict[str, Any]) -> str:
    process = model["process"]
    nodes = index_nodes(model)
    decisions = [node for node in model["nodes"] if node["type"] == "decision"]
    pending = model["pending_questions"]
    status = "草案，存在待确认规则" if has_unresolved(model) else "已确认"
    sections = [
        f"# {process['number']} {process['name']}",
        "",
        f"> 公司：{model['company']}  ",
        "> 文档类型：企业流程与决策还原  ",
        f"> 状态：{status}  ",
        f"> 已识别关键决策：{len(decisions)} 个  ",
        f"> 待确认问题：{len(pending)} 项",
        "",
        "**流程边界**",
        "",
        f"- 核心业务对象：{process['business_object']}",
        f"- 触发事件：{process['trigger']}",
        f"- 结束状态：{process['end_state']}",
        f"- 边界理由：{process['boundary_reason']}",
        "",
        "## 流程图",
        "",
        "同一棵树连续展示本流程。↓ 表示连续动作；◆ 表示决策；【】表示分支条件；↪ 仅用于汇入已展开的公共节点；… 表示资料缺口。",
        "",
        "```text",
        render_tree(model),
        "```",
        "",
        "## 关键决策节点",
        "",
    ]
    if not decisions:
        sections.extend(["未识别到关键决策节点。", ""])
    for node in decisions:
        sections.extend(
            [
                f"### {node['id']} {node['question']}",
                "",
                f"- **判断主体：**{node['owner']}",
                f"- **判断信息：**{'、'.join(node['inputs'])}",
            ]
        )
        for criterion in node["criteria"]:
            basis = f"（依据：{criterion['evidence']}）" if criterion['evidence'] != criterion['text'] else ''
            sections.append(f"- **条件依据：**[{status_text(criterion['status'])}] {criterion['text']}{basis}")
        if node.get("branches_complete", True) is False:
            sections.append("- 分支完整性：仅列已知结果；未说明的结果及去向待确认。")
        for index, branch in enumerate(node["branches"], 1):
            target = nodes[branch['target']]
            condition = branch['condition'] if branch['label'] == branch['condition'] else f"{branch['label']}（条件：{branch['condition']}）"
            if branch['condition_status'] != 'confirmed':
                condition += f"〔条件：{status_text(branch['condition_status'])}〕"
            target_notes = []
            if branch['target_status'] != 'confirmed':
                target_notes.append('去向：'+status_text(branch['target_status']))
            if branch.get('path_note'):
                target_notes.append(branch['path_note'])
            note = '〔'+'；'.join(target_notes)+'〕' if target_notes else ''
            sections.append(f"- **分支 {index}：**{condition} → {branch['target']} {target.get('label',target.get('question',''))}{note}")
        if node.get('note'):
            sections.append('- **边界：**'+node['note'])
        related = [q['id'] for q in pending if node['id'] in q['related_nodes']]
        if related:
            sections.append('- **对应待确认：**'+'、'.join(related))
        sections.append("")

    sections.extend(["## 待确认问题", ""])
    if pending:
        for question in pending:
            sections.extend([f"**{question['id']}** {question['text']}（关联：{'、'.join(question['related_nodes'])}）", ''])
            for fact in question.get('known_facts', []):
                sections.extend(['已知事实：'+fact['text'], ''])
    else:
        sections.append("无。")
    sections.extend(["", "**资料来源**", ""])
    sections.extend(f"- {source}" for source in model["sources"])
    sections.extend(["", "> 本文件只还原输入资料。所有“待确认”和“推断”内容均不得写成企业既定事实。", ""])
    return "\n".join(sections)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_path_map(model: dict[str, Any]) -> str:
    from flow_svg import render_svg
    return render_svg(model)


def render_decision_details(model: dict[str, Any]) -> str:
    nodes = index_nodes(model)
    cards = []
    for node in model['nodes']:
        if node['type'] != 'decision':
            continue
        rows = [f'<div class="detail-row"><strong>决策人</strong><p>{esc(node["owner"])}</p></div>',
                f'<div class="detail-row"><strong>判断信息</strong><p>{esc("、".join(node["inputs"]))}</p></div>']
        for item in node['criteria']:
            heading = '判断标准'
            rows.append(f'<div class="detail-row"><strong>{heading}</strong><p><span class="tag {esc(item["status"])}">{esc(status_text(item["status"]))}</span>{esc(item["text"])}<small>依据：{esc(item["evidence"])}</small></p></div>')
        if node.get('branches_complete') is False:
            rows.append('<div class="detail-row"><strong>待确认</strong><p>资料只说明已列出的结果；其他结果及去向尚未说明。</p></div>')
        for branch in node['branches']:
            target = nodes[branch['target']]
            condition_heading = '条件' if branch.get('condition_status') == 'confirmed' else f'条件（{status_text(branch.get("condition_status",branch["status"]))}）'
            target_heading = '去向' if branch.get('target_status') == 'confirmed' else f'去向（{status_text(branch.get("target_status",branch["status"]))}）'
            rows.append(f'<div class="detail-branch"><strong>{esc(branch["label"])}</strong><span>{condition_heading}：{esc(branch["condition"])}</span><span class="target">{target_heading}：<a href="#path-{esc(branch["target"])}">→ {esc(branch["target"])} · {esc(target.get("label",target.get("question","")))}</a></span></div>')
        cards.append(f'<article class="decision-detail" id="detail-{esc(node["id"])}"><header><span class="decision-id">{esc(node["id"])}</span><h3>{esc(node["question"])}</h3></header>{"".join(rows)}</article>')
    return ''.join(cards) or '<p class="empty">现有资料未识别到改变后续路径的决策。</p>'


def render_pending_questions(model: dict[str, Any]) -> str:
    nodes = index_nodes(model)
    questions = []
    for question in model['pending_questions']:
        links = ''.join(f'<a href="#{"detail" if nodes[nid]["type"] == "decision" else "path"}-{esc(nid)}">{esc(nid)}</a>' for nid in question['related_nodes'])
        questions.append(f'<li class="question-card" id="question-{esc(question["id"])}"><p>{esc(question["text"])}</p><span class="question-links">{esc(question["id"])} · 关联 {links}</span></li>')
    return '<ol class="questions">'+''.join(questions)+'</ol>' if questions else '<p class="empty">当前没有待确认问题。</p>'


def render_html(model: dict[str, Any]) -> str:
    process = model['process']
    decisions = [node for node in model['nodes'] if node['type'] == 'decision']
    status = '草案，保留待确认规则' if has_unresolved(model) else '已确认'
    css = (Path(__file__).resolve().parents[1] / 'assets' / 'process.css').read_text(encoding='utf-8')
    sources = ''.join(f'<li>{esc(source)}</li>' for source in model['sources'])
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(model['company'])} · {esc(process['name'])}流程说明</title><style>{css}</style></head>
<body><main class="page">
<h1>{esc(process['number'])} {esc(process['name'])} · 流程说明</h1>
<div class="meta"><span>{esc(model['company'])}</span><span class="status">{esc(status)}</span><span>{len(decisions)} 个关键决策</span><span>{len(model['pending_questions'])} 项待确认问题</span></div>
<p class="scope">{esc(process['trigger'])} → {esc(process['end_state'])}</p>
<div class="legend"><span><i></i>业务动作</span><span><i class="diamond"></i>关键决策</span><span><i class="unknown"></i>去向待确认</span><span><i class="end"></i>起点 / 终态</span></div>
<section id="flow-map" class="panel"><h2>流程图</h2><div class="flow-canvas" tabindex="0" role="region" aria-label="可横向滚动查看流程图">{render_path_map(model)}</div></section>
<section id="decision-details" class="panel"><h2>关键决策节点</h2>{render_decision_details(model)}</section>
<section id="pending-questions" class="panel"><h2>待确认问题</h2>{render_pending_questions(model)}</section>
<footer class="sources"><strong>资料来源</strong><ul>{sources}</ul><p>只还原现有资料；待确认内容不代表既定事实，不补写缺失业务环节。</p></footer>
</main></body></html>'''


def render_files(model: dict[str, Any], output_dir: Path) -> list[Path]:
    errors = validate_model(model)
    if errors:
        raise ModelError("；".join(errors))
    if model["confirmation"]["status"] != "confirmed":
        raise ModelError("尚未取得用户确认，不能生成正式流程成果")
    process = model["process"]
    stem = f"{process['number']} {process['name']}"
    outputs = [
        (output_dir / f"{stem}-流程说明.md", render_markdown(model)),
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    return [path for path, _ in outputs]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验并渲染企业流程决策模型")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="校验 JSON 模型")
    validate.add_argument("model", type=Path)
    validate.add_argument("--require-confirmed", action="store_true", help="不允许任何待确认或推断内容")
    render = subparsers.add_parser("render", help="生成一个流程的一份完整 Markdown 文档")
    render.add_argument("model", type=Path)
    render.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        model = load_model(args.model)
        errors = validate_model(model)
        if errors:
            for error in errors:
                print(f"错误：{error}", file=sys.stderr)
            return 1
        if args.command == "validate":
            if args.require_confirmed and has_unresolved(model):
                print("错误：模型仍含待确认内容，不能作为已确认流程发布", file=sys.stderr)
                return 2
            decisions = sum(node["type"] == "decision" for node in model["nodes"])
            pending = len(model["pending_questions"])
            print(f"校验通过：{decisions} 个决策节点，{pending} 个待确认问题")
            return 0
        if model.get("confirmation", {}).get("status") != "confirmed":
            print("错误：尚未取得用户确认，不能生成正式流程成果", file=sys.stderr)
            return 3
        outputs = render_files(model, args.output_dir)
        for output in outputs:
            print(output)
        return 0
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
