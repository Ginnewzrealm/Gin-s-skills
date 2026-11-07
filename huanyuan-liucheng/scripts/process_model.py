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


def validate_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require_text(model.get("schema_version"), "schema_version", errors)
    if model.get("schema_version") != "2.0":
        errors.append("schema_version 必须是 2.0")
    require_text(model.get("company"), "company", errors)

    confirmation = model.get("confirmation")
    if not isinstance(confirmation, dict):
        errors.append("confirmation 必须是对象")
        confirmation = {}
    if confirmation.get("status") not in CONFIRMATION_TYPES:
        errors.append("confirmation.status 只能是 pending 或 confirmed")
    require_text(confirmation.get("scope_summary"), "confirmation.scope_summary", errors)

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
            if not isinstance(branches, list) or len(branches) < 2:
                errors.append(f"{node_id}.branches 至少需要两个分支")
            else:
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
                if primary_count != 1:
                    errors.append(f"{node_id}.branches 必须且只能有一个 primary=true 分支")

    duplicate_ids = sorted({node_id for node_id in ids if ids.count(node_id) > 1})
    if duplicate_ids:
        errors.append(f"节点 id 重复：{', '.join(duplicate_ids)}")

    node_map = {
        node["id"]: node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("id")
    }
    starts = [node for node in node_map.values() if node.get("type") == "start"]
    if len(starts) != 1:
        errors.append(f"必须且只能有一个 start 节点，当前为 {len(starts)} 个")
    if not any(node.get("type") == "terminal" for node in node_map.values()):
        errors.append("至少需要一个 terminal 节点")

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

        def walk(node_id: str) -> None:
            if node_id in active:
                errors.append(f"检测到未声明的流程环：{node_id}")
                return
            if node_id in reached:
                return
            reached.add(node_id)
            active.add(node_id)
            node = node_map[node_id]
            if node["type"] in {"start", "action", "join"}:
                walk(node["next"])
            elif node["type"] == "decision":
                for branch in node["branches"]:
                    walk(branch["target"])
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
    nodes = index_nodes(model)
    start = next(node for node in model["nodes"] if node["type"] == "start")
    lines: list[str] = []

    def append_node(node_id: str, prefix: str, path: frozenset[str]) -> None:
        node = nodes[node_id]
        node_type = node["type"]
        if node_id in path:
            lines.append(f"{prefix}↩ 汇入 {node_id} {node.get('label', node.get('question', ''))}")
            return
        next_path = path | {node_id}
        if node_type == "start":
            lines.append(f"{prefix}▶ {node['label']}")
            lines.append(f"{prefix}│")
            lines.append(f"{prefix}▼")
            append_node(node["next"], prefix, next_path)
        elif node_type == "action":
            owner = f"〔{node.get('owner')}〕" if node.get("owner") else ""
            lines.append(f"{prefix}▭ {node_id} {owner}{node['label']}")
            lines.append(f"{prefix}│")
            lines.append(f"{prefix}▼")
            append_node(node["next"], prefix, next_path)
        elif node_type == "decision":
            lines.append(f"{prefix}◇ {node_id} {node['question']}")
            branches = node["branches"]
            for index, branch in enumerate(branches):
                last = index == len(branches) - 1
                fork = "└─" if last else "├─"
                continuation = "   " if last else "│  "
                lines.append(f"{prefix}{fork} {branch['label']}")
                lines.append(f"{prefix}{continuation}条件：{branch['condition']}")
                lines.append(f"{prefix}{continuation}│")
                lines.append(f"{prefix}{continuation}▼")
                append_node(branch["target"], prefix + continuation, next_path)
        elif node_type == "join":
            lines.append(f"{prefix}◆ {node_id} {node['label']}")
            lines.append(f"{prefix}│")
            lines.append(f"{prefix}▼")
            append_node(node["next"], prefix, next_path)
        elif node_type == "unresolved":
            lines.append(f"{prefix}⚠ {node_id} {node['label']}")
        elif node_type == "terminal":
            lines.append(f"{prefix}● {node_id} {node['label']}")

    append_node(start["id"], "", frozenset())
    return "\n".join(lines)


def render_markdown(model: dict[str, Any]) -> str:
    process = model["process"]
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
        "## 全流程决策树",
        "",
        "```text",
        render_tree(model),
        "```",
        "",
        "## 关键决策节点",
        "",
    ]
    for node in decisions:
        sections.extend(
            [
                f"### {node['id']} {node['question']}",
                "",
                f"- 决策人：{node['owner']}",
                f"- 判断信息：{'、'.join(node['inputs'])}",
                "- 判断标准：",
            ]
        )
        for criterion in node["criteria"]:
            sections.append(
                f"  - [{status_text(criterion['status'])}] {criterion['text']}（依据：{criterion['evidence']}）"
            )
        sections.append("- 分支条件：")
        for branch in node["branches"]:
            sections.append(
                f"  - {branch['label']}｜条件：{branch['condition']}｜去向：{branch['target']}｜{status_text(branch['status'])}"
            )
        sections.append("")

    sections.extend(["## 待确认问题", ""])
    if pending:
        sections.extend(
            f"{question['id']}. {question['text']}（关联：{'、'.join(question['related_nodes'])}）"
            for question in pending
        )
    else:
        sections.append("无。")
    sections.extend(["", "## 图例", "", "- `▶`：流程起点", "- `▭`：业务动作", "- `◇`：关键决策节点", "- `●`：业务终态", "- `⚠`：资料不足，必须继续确认", "", "## 资料来源", ""])
    sections.extend(f"- {source}" for source in model["sources"])
    sections.extend(["", "> 本文件只还原输入资料。所有“待确认”和“推断”内容均不得写成企业既定事实。", ""])
    return "\n".join(sections)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def path_card(node: dict[str, Any]) -> str:
    node_type = node["type"]
    owners = {
        "start": "起点",
        "action": node.get("owner", ""),
        "decision": node.get("owner", ""),
        "join": "路径汇合",
        "unresolved": node.get("owner", "待确认"),
        "terminal": "完成",
    }
    label = node.get("question", node.get("label", ""))
    return f'''<article class="path-card {esc(node_type)}" id="path-{esc(node['id'])}">
  <header><span>{esc(node['id'])}</span><span>{esc(owners[node_type])}</span></header>
  <h3>{esc(label)}</h3>
</article>'''


def render_path_map(model: dict[str, Any]) -> str:
    nodes = index_nodes(model)
    start = next(node for node in model["nodes"] if node["type"] == "start")
    expanded: set[str] = set()

    def render_node(node_id: str, path: frozenset[str]) -> str:
        node = nodes[node_id]
        if node_id in path or node_id in expanded:
            label = node.get("question", node.get("label", ""))
            return f'''<a class="merge-reference" data-merge-target="{esc(node_id)}" href="#path-{esc(node_id)}">
  汇入 {esc(node_id)} · {esc(label)}
</a>'''
        expanded.add(node_id)
        next_path = path | {node_id}
        card = path_card(node)
        if node["type"] in {"terminal", "unresolved"}:
            return f'<div class="path-node path-end">{card}</div>'
        if node["type"] == "decision":
            branches = "".join(
                f'''<div class="branch-lane {esc(branch['status'])}">
  <div class="branch-condition"><strong>{esc(branch['label'])}</strong><span>{esc(branch['condition'])}</span></div>
  <div class="branch-arrow" aria-hidden="true">↓</div>
  {render_node(branch['target'], next_path)}
</div>'''
                for branch in node["branches"]
            )
            return f'''<div class="path-node decision-node">
  {card}
  <div class="branch-grid" style="--branch-count:{len(node['branches'])}">{branches}</div>
</div>'''
        return f'''<div class="path-node linear-node">
  {card}
  <div class="linear-arrow" aria-hidden="true">↓</div>
  <div class="linear-child">{render_node(node['next'], next_path)}</div>
</div>'''

    return render_node(start["id"], frozenset())


def render_decision_details(model: dict[str, Any]) -> str:
    nodes = index_nodes(model)
    cards: list[str] = []
    for node in model["nodes"]:
        if node["type"] != "decision":
            continue
        criteria = "".join(
            f'<li><span class="tag {esc(item["status"])}">{esc(status_text(item["status"]))}</span>'
            f'<span>{esc(item["text"])}</span><small>依据：{esc(item["evidence"])}</small></li>'
            for item in node["criteria"]
        )
        branch_rows = "".join(
            f'''<div class="detail-branch {esc(branch['status'])}">
  <strong>{esc(branch['label'])}</strong>
  <span>条件：{esc(branch['condition'])}</span>
  <span class="target">→ {esc(branch['target'])} · {esc(nodes[branch['target']].get('label', nodes[branch['target']].get('question', '')))}</span>
</div>'''
            for branch in node["branches"]
        )
        cards.append(
            f'''<article class="decision-detail" id="detail-{esc(node['id'])}">
  <header><div><span>{esc(node['id'])} · {esc(node['title'])}</span><h3>{esc(node['question'])}</h3></div><b>{esc(node['owner'])}</b></header>
  <p class="detail-inputs"><strong>判断信息</strong>{esc('、'.join(node['inputs']))}</p>
  <div class="detail-criteria"><strong>判断标准</strong><ul>{criteria}</ul></div>
  <div class="detail-branches"><strong>分支条件与去向</strong>{branch_rows}</div>
</article>'''
        )
    return "".join(cards)


def render_pending_questions(model: dict[str, Any]) -> str:
    if not model["pending_questions"]:
        return '<p class="empty">当前没有待确认问题。</p>'
    return "".join(
        f'''<article class="question-card" id="question-{esc(question['id'])}">
  <div><strong>{esc(question['id'])}</strong><p>{esc(question['text'])}</p></div>
  <div class="question-links">关联：{''.join(f'<a href="#detail-{esc(node_id)}">{esc(node_id)}</a>' for node_id in question['related_nodes'])}</div>
</article>'''
        for question in model["pending_questions"]
    )


def render_html(model: dict[str, Any]) -> str:
    process = model["process"]
    decisions = [node for node in model["nodes"] if node["type"] == "decision"]
    pending = model["pending_questions"]
    status = "草案 · 关键规则待确认" if has_unresolved(model) else "已确认"
    sources = "".join(f"<li>{esc(source)}</li>" for source in model["sources"])
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(model['company'])}｜{esc(process['name'])}决策路径图</title>
<style>
:root{{--ink:#192230;--muted:#667085;--paper:#f5f6f8;--card:#fff;--line:#98a2b3;--blue:#eaf3ff;--blue-b:#72a7df;--yellow:#fff2bd;--yellow-b:#d5a72b;--red:#fff0ef;--red-b:#d7655b;--green:#e9f7ee;--green-b:#55a46b;--purple:#f0e9ff;--purple-b:#8b6fd1}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55}}a{{color:inherit}}
.page{{max-width:1500px;margin:auto;padding:42px 48px 72px}}.brand{{font-size:12px;font-weight:850;letter-spacing:.12em;color:#35618e}}.hero{{display:flex;justify-content:space-between;gap:28px;align-items:flex-start;margin-top:9px}}h1{{font-size:38px;line-height:1.2;margin:0 0 8px}}.subtitle{{margin:0;color:var(--muted)}}.status{{white-space:nowrap;padding:8px 13px;border:1px solid #e1bd44;background:#fff7d8;border-radius:999px;font-size:13px;font-weight:800}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:26px 0}}.metric{{background:#fff;border:1px solid #dfe3e8;border-radius:10px;padding:14px 17px}}.metric strong{{font-size:24px;margin-right:8px}}.metric span{{font-size:13px;color:var(--muted)}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:18px;padding:12px 15px;background:#fff;border:1px solid #dfe3e8;border-radius:9px;font-size:13px;color:#475467}}.legend i{{display:inline-block;width:12px;height:12px;margin-right:6px;border-radius:3px;vertical-align:-1px}}
.panel{{background:#fff;border:1px solid #dce2e8;border-radius:14px;padding:30px;box-shadow:0 10px 30px rgba(29,41,57,.05)}}.panel+.panel{{margin-top:26px}}.section-head{{margin-bottom:22px}}.section-head h2{{font-size:25px;margin:0 0 4px}}.section-head p{{margin:0;color:var(--muted);font-size:13px}}
.path-root{{overflow-x:auto;padding:4px 0 14px}}.path-node{{display:flex;flex-direction:column;align-items:center;min-width:0}}.path-card{{width:min(100%,360px);border:2px solid;border-radius:11px;padding:13px 15px;box-shadow:0 4px 10px rgba(16,24,40,.04)}}.path-card header{{display:flex;justify-content:space-between;gap:12px;color:#586579;font-size:12px;font-weight:800}}.path-card h3{{font-size:16px;line-height:1.35;margin:8px 0 0}}.path-card.start,.path-card.action{{background:var(--blue);border-color:var(--blue-b)}}.path-card.decision{{background:var(--yellow);border-color:var(--yellow-b)}}.path-card.unresolved{{background:var(--red);border-color:var(--red-b)}}.path-card.terminal{{background:var(--green);border-color:var(--green-b)}}.path-card.join{{background:var(--purple);border-color:var(--purple-b)}}
.linear-arrow,.branch-arrow{{color:#697586;font-weight:800;line-height:1;padding:9px 0}}.linear-child{{width:100%;display:flex;justify-content:center}}.branch-grid{{width:100%;display:grid;grid-template-columns:repeat(var(--branch-count),minmax(220px,1fr));gap:16px;margin-top:14px;align-items:start}}.branch-lane{{min-width:0;border-top:2px solid var(--line);padding-top:10px;display:flex;flex-direction:column;align-items:center}}.branch-lane.unresolved{{border-top-color:var(--red-b)}}.branch-condition{{width:100%;min-height:74px;border:1px solid #d9dee5;background:#f8fafc;border-radius:8px;padding:10px 11px;text-align:left}}.branch-condition strong{{display:block;font-size:13px;margin-bottom:4px}}.branch-condition span{{display:block;font-size:12px;color:#475467}}.merge-reference{{display:block;width:min(100%,330px);border:1.5px dashed var(--purple-b);background:var(--purple);border-radius:9px;padding:11px 13px;text-align:center;text-decoration:none;font-size:13px;font-weight:800;color:#58409a}}
.decision-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.decision-detail{{border:1px solid #dce2e8;border-radius:11px;padding:18px;background:#fff}}.decision-detail header{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}}.decision-detail header span{{font-size:12px;font-weight:850;color:#8a6500}}.decision-detail h3{{font-size:18px;margin:3px 0 0}}.decision-detail header b{{font-size:12px;background:#fff4c7;border:1px solid #e2c360;border-radius:999px;padding:4px 9px;white-space:nowrap}}.detail-inputs{{display:grid;grid-template-columns:76px 1fr;gap:8px;font-size:13px;margin:16px 0}}.detail-criteria>strong,.detail-branches>strong{{display:block;font-size:13px;margin-bottom:7px}}.detail-criteria ul{{margin:0 0 16px;padding-left:18px}}.detail-criteria li{{margin:7px 0;font-size:13px}}.detail-criteria li small{{display:block;margin:2px 0 0 54px;color:var(--muted)}}.tag{{display:inline-block;font-size:11px;font-weight:850;border-radius:4px;padding:1px 5px;margin-right:6px}}.tag.confirmed{{background:#dff1e5;color:#246b39}}.tag.unresolved{{background:#ffe1dc;color:#9d3029}}.tag.inferred{{background:#e8e5ff;color:#5748a7}}.detail-branch{{display:grid;grid-template-columns:120px 1fr;gap:3px 10px;border-top:1px solid #e8ebef;padding:9px 0;font-size:12.5px}}.detail-branch .target{{grid-column:2;color:#675200;font-weight:750}}
.questions{{display:grid;gap:10px}}.question-card{{display:flex;justify-content:space-between;gap:22px;padding:14px 16px;border:1px solid #e1e5ea;border-left:4px solid var(--red-b);border-radius:8px;background:#fff}}.question-card div:first-child{{display:grid;grid-template-columns:46px 1fr;gap:8px}}.question-card p{{margin:0}}.question-links{{white-space:nowrap;font-size:12px;color:var(--muted)}}.question-links a{{display:inline-block;margin-left:6px;color:#35618e;font-weight:800}}.sources{{font-size:13px;color:#475467}}.footnote{{margin:16px 2px 0;color:var(--muted);font-size:13px}}
@media(max-width:900px){{.page{{padding:24px 14px 44px}}.hero{{display:block}}.status{{display:inline-block;margin-top:14px}}.metrics{{grid-template-columns:1fr}}.panel{{padding:20px 12px}}.branch-grid{{grid-template-columns:1fr!important}}.decision-grid{{grid-template-columns:1fr}}.question-card{{display:block}}.question-links{{margin-top:8px;white-space:normal}}h1{{font-size:30px}}}}
@media print{{body{{background:#fff}}.page{{max-width:none;padding:16px}}.panel{{box-shadow:none;break-inside:avoid}}.path-root{{overflow:visible}}}}
</style>
</head>
<body>
<main class="page">
  <div class="brand">企业流程现状还原 · 决策路径图</div>
  <div class="hero"><div><h1>{esc(process['number'])} {esc(process['name'])}</h1><p class="subtitle">{esc(model['company'])}｜{esc(process['trigger'])} → {esc(process['end_state'])}</p></div><div class="status">● {esc(status)}</div></div>
  <section class="metrics" aria-label="流程统计"><div class="metric"><strong>{len(decisions)}</strong><span>关键决策节点</span></div><div class="metric"><strong>{len(pending)}</strong><span>待确认问题</span></div><div class="metric"><strong>{len(model['nodes'])}</strong><span>流程节点</span></div></section>
  <div class="legend"><span><i style="background:var(--blue);border:1px solid var(--blue-b)"></i>业务动作</span><span><i style="background:var(--yellow);border:1px solid var(--yellow-b)"></i>关键决策</span><span><i style="background:var(--purple);border:1px solid var(--purple-b)"></i>路径汇合</span><span><i style="background:var(--red);border:1px solid var(--red-b)"></i>资料未说明的去向</span><span><i style="background:var(--green);border:1px solid var(--green-b)"></i>业务终态</span></div>
  <section id="flow-map" class="panel" aria-label="{esc(process['name'])}当前现状流程图"><div class="section-head"><h2>当前现状流程图</h2><p>只显示实际节点、决策分支和路径汇合；完整说明统一列在图后。</p></div><div class="path-root">{render_path_map(model)}</div></section>
  <section id="decision-details" class="panel" aria-label="关键决策节点说明"><div class="section-head"><h2>关键决策节点说明</h2><p>逐项列出决策人、判断信息、判断标准、分支条件和去向。</p></div><div class="decision-grid">{render_decision_details(model)}</div></section>
  <section id="pending-questions" class="panel" aria-label="待确认问题"><div class="section-head"><h2>待确认问题</h2><p>资料缺失、冲突或衔接不明只在这里提问，不补成流程动作。</p></div><div class="questions">{render_pending_questions(model)}</div></section>
  <section id="sources" class="panel sources" aria-label="资料来源"><div class="section-head"><h2>资料来源与事实声明</h2></div><ul>{sources}</ul><p class="footnote">本文件只还原输入资料。规范、建议和未来目标不等于当前现状；所有“推断”和“待确认”内容不得写成企业既定事实。</p></section>
</main>
</body>
</html>
'''


def render_questions(model: dict[str, Any]) -> str:
    process = model["process"]
    pending = model["pending_questions"]
    lines = [
        f"# {process['number']} {process['name']}｜待确认问题",
        "",
        f"> 共 {len(pending)} 项。访谈时按顺序确认；确认后同步更新 JSON，再重新生成两种输出。",
        "",
    ]
    if pending:
        lines.extend(
            f"{question['id']}. {question['text']}（关联：{'、'.join(question['related_nodes'])}）"
            for question in pending
        )
    else:
        lines.append("当前没有待确认问题。")
    lines.append("")
    return "\n".join(lines)


def render_files(model: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    process = model["process"]
    stem = f"{process['number']} {process['name']}"
    outputs = [
        (output_dir / f"{stem}-流程说明.md", render_markdown(model)),
        (output_dir / f"{stem}-决策路径图.html", render_html(model)),
        (output_dir / f"{stem}-待确认问题.md", render_questions(model)),
    ]
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    return [path for path, _ in outputs]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验并渲染企业流程决策模型")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="校验 JSON 模型")
    validate.add_argument("model", type=Path)
    validate.add_argument("--require-confirmed", action="store_true", help="不允许任何待确认或推断内容")
    render = subparsers.add_parser("render", help="生成 Markdown、HTML 和待确认问题单")
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
    except ModelError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
