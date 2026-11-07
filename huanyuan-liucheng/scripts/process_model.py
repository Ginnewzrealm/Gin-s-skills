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


NODE_TYPES = {"start", "action", "decision", "unresolved", "terminal"}
STATUS_TYPES = {"confirmed", "unresolved", "inferred"}


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
    require_text(model.get("company"), "company", errors)

    process = model.get("process")
    if not isinstance(process, dict):
        errors.append("process 必须是对象")
        process = {}
    for field in ("number", "name", "status"):
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

        if node_type in {"start", "action", "unresolved", "terminal"}:
            require_text(node.get("label"), f"{node_id}.label", errors)
        if node_type in {"start", "action"}:
            require_text(node.get("next"), f"{node_id}.next", errors)
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
        if node.get("type") in {"start", "action"} and isinstance(node.get("next"), str):
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
            if node["type"] in {"start", "action"}:
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
        for index, question in enumerate(pending):
            require_text(question, f"pending_questions[{index}]", errors)

    sources = model.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources 至少需要一项资料来源")
    else:
        for index, source in enumerate(sources):
            require_text(source, f"sources[{index}]", errors)

    return errors


def has_unresolved(model: dict[str, Any]) -> bool:
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
        sections.extend(f"{index}. {question}" for index, question in enumerate(pending, 1))
    else:
        sections.append("无。")
    sections.extend(["", "## 图例", "", "- `▶`：流程起点", "- `▭`：业务动作", "- `◇`：关键决策节点", "- `●`：业务终态", "- `⚠`：资料不足，必须继续确认", "", "## 资料来源", ""])
    sections.extend(f"- {source}" for source in model["sources"])
    sections.extend(["", "> 本文件只还原输入资料。所有“待确认”和“推断”内容均不得写成企业既定事实。", ""])
    return "\n".join(sections)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def primary_spine(model: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = index_nodes(model)
    current = next(node for node in model["nodes"] if node["type"] == "start")
    spine: list[dict[str, Any]] = []
    seen: set[str] = set()
    while current["id"] not in seen:
        spine.append(current)
        seen.add(current["id"])
        if current["type"] in {"terminal", "unresolved"}:
            break
        if current["type"] in {"start", "action"}:
            current = nodes[current["next"]]
        else:
            primary = next(branch for branch in current["branches"] if branch["primary"])
            current = nodes[primary["target"]]
    return spine


def node_card(node: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> str:
    node_type = node["type"]
    if node_type == "decision":
        criteria = "".join(
            f'<li><span class="tag {esc(item["status"])}">{esc(status_text(item["status"]))}</span>{esc(item["text"])}</li>'
            for item in node["criteria"]
        )
        branch_rows: list[str] = []
        for branch in node["branches"]:
            target = nodes[branch["target"]]
            target_label = target.get("label", target.get("question", ""))
            branch_rows.append(
                f'<div class="branch-row"><span>{esc(branch["label"])}</span><b>条件：{esc(branch["condition"])}</b><em>→ {esc(branch["target"])} · {esc(target_label)}</em></div>'
            )
        branches = "".join(branch_rows)
        return f'''<article class="node decision" id="{esc(node['id'])}">
  <header><span class="node-id">{esc(node['id'])} · {esc(node['title'])}</span><span class="owner">{esc(node['owner'])}</span></header>
  <h2>{esc(node['question'])}</h2>
  <p class="inputs"><strong>判断信息</strong>{esc(' · '.join(node['inputs']))}</p>
  <div class="criteria"><strong>判断标准</strong><ul>{criteria}</ul></div>
  <div class="branches">{branches}</div>
</article>'''
    labels = {
        "start": ("起点", "start"),
        "action": (node.get("owner", "业务动作"), "action"),
        "unresolved": (node.get("owner", "待确认"), "unresolved"),
        "terminal": ("完成", "terminal"),
    }
    owner, css_class = labels[node_type]
    return f'''<article class="node {css_class}" id="{esc(node['id'])}">
  <header><span class="node-id">{esc(node['id'])}</span><span class="owner">{esc(owner)}</span></header>
  <h2>{esc(node['label'])}</h2>
</article>'''


def render_html(model: dict[str, Any]) -> str:
    process = model["process"]
    nodes = index_nodes(model)
    decisions = [node for node in model["nodes"] if node["type"] == "decision"]
    pending = model["pending_questions"]
    spine = primary_spine(model)
    spine_ids = {node["id"] for node in spine}
    off_spine_decisions = [node for node in decisions if node["id"] not in spine_ids]
    blocks: list[str] = []
    for index, node in enumerate(spine):
        side_cards = ""
        primary_label = ""
        if node["type"] == "decision":
            primary = next(branch for branch in node["branches"] if branch["primary"])
            primary_label = f'<div class="path-label"><strong>{esc(primary["label"])}</strong><span>条件：{esc(primary["condition"])}</span></div>'
            alternatives = [branch for branch in node["branches"] if not branch["primary"]]
            if alternatives:
                side_cards = '<aside class="alternatives" aria-label="其他分支">' + "".join(
                    f'''<div class="alternative {esc(branch['status'])}">
  <span class="alternative-label">{esc(branch['label'])}</span>
  <strong>条件：{esc(branch['condition'])}</strong>
  <p>去向：{esc(branch['target'])} · {esc(nodes[branch['target']].get('label', nodes[branch['target']].get('question', '')))}</p>
</div>'''
                    for branch in alternatives
                ) + "</aside>"
        connector = ""
        if index < len(spine) - 1:
            connector = f'<div class="connector">{primary_label}<span class="line"></span><span class="arrow">▼</span></div>'
        blocks.append(f'<div class="stage"><div class="main">{node_card(node, nodes)}{connector}</div>{side_cards}</div>')

    branch_decisions = ""
    if off_spine_decisions:
        inbound: dict[str, list[str]] = {node["id"]: [] for node in off_spine_decisions}
        for source in model["nodes"]:
            if source.get("type") == "decision":
                for branch in source["branches"]:
                    if branch["target"] in inbound:
                        inbound[branch["target"]].append(f"{source['id']} · {branch['label']}")
            elif source.get("type") in {"start", "action"} and source.get("next") in inbound:
                inbound[source["next"]].append(source["id"])
        cards = "".join(
            f'''<div class="branch-decision-item">
  <p class="branch-entry"><strong>进入路径</strong>{esc('；'.join(inbound[node['id']]) or '见模型中的目标编号')}</p>
  {node_card(node, nodes)}
</div>'''
            for node in off_spine_decisions
        )
        branch_decisions = f'''<section class="branch-decisions" aria-label="分支决策展开">
  <div class="section-heading"><div><span>非主线关键节点</span><h2>分支决策展开</h2></div><p>这些决策位于中央主线之外，但仍完整保留判断信息、判断标准、每个分支条件和去向。</p></div>
  <div class="branch-decision-grid">{cards}</div>
</section>'''

    status = "草案 · 关键规则待确认" if has_unresolved(model) else "已确认"
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(model['company'])}｜{esc(process['name'])}决策路径图</title>
<style>
:root{{--ink:#162033;--muted:#667085;--paper:#f4f6f8;--line:#aeb8c7;--blue:#eaf3ff;--blue-border:#72a7df;--yellow:#fff4c7;--yellow-border:#d9a61f;--red:#fff0ef;--red-border:#d7655b;--green:#e9f7ee;--green-border:#55a46b;--white:#fff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.55}}
.page{{max-width:1440px;margin:0 auto;padding:42px 54px 72px}}.brand{{font-size:13px;font-weight:800;letter-spacing:.12em;color:#35618e;text-transform:uppercase}}
.hero{{display:flex;align-items:flex-start;justify-content:space-between;gap:30px;margin-top:10px}}h1{{font-size:38px;line-height:1.2;margin:0 0 9px}}.subtitle{{margin:0;color:var(--muted);font-size:16px}}.status{{white-space:nowrap;background:#fff7d8;border:1px solid #e5c04a;border-radius:999px;padding:9px 14px;font-size:13px;font-weight:800}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:28px 0}}.metric{{background:var(--white);border:1px solid #dfe4ea;border-radius:10px;padding:15px 18px}}.metric strong{{font-size:25px;margin-right:8px}}.metric span{{color:var(--muted);font-size:13px}}
.legend{{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:30px;padding:13px 16px;background:var(--white);border:1px solid #e0e5eb;border-radius:9px;font-size:13px;color:#475467}}.legend i{{display:inline-block;width:12px;height:12px;margin-right:7px;border-radius:3px;vertical-align:-1px}}
.flow{{background:#fff;border:1px solid #dce2e9;border-radius:14px;padding:36px 32px 46px;box-shadow:0 12px 35px rgba(29,41,57,.06)}}.stage{{display:grid;grid-template-columns:minmax(0,760px) minmax(260px,1fr);gap:52px;align-items:start;position:relative;max-width:1160px;margin:0 auto}}.main{{min-width:0}}.node{{border:2px solid;border-radius:12px;padding:17px 20px;background:#fff;box-shadow:0 5px 12px rgba(16,24,40,.05)}}.node header{{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:8px}}.node-id{{font-size:13px;font-weight:900;letter-spacing:.03em}}.owner{{font-size:12px;font-weight:800;background:rgba(255,255,255,.75);border:1px solid rgba(16,24,40,.14);border-radius:999px;padding:4px 9px}}.node h2{{font-size:20px;margin:0;line-height:1.35}}.node.action,.node.start{{background:var(--blue);border-color:var(--blue-border)}}.node.decision{{background:var(--yellow);border-color:var(--yellow-border)}}.node.unresolved{{background:var(--red);border-color:var(--red-border)}}.node.terminal{{background:var(--green);border-color:var(--green-border)}}
.inputs{{font-size:13px;margin:12px 0 8px;color:#4b5565}}.inputs strong,.criteria>strong{{display:inline-block;min-width:68px;color:#27364a}}.criteria{{font-size:13px;color:#4b5565}}.criteria ul{{margin:6px 0 13px;padding-left:19px}}.criteria li{{margin:5px 0}}.tag{{display:inline-block;font-size:11px;font-weight:850;border-radius:4px;padding:1px 5px;margin-right:6px}}.tag.confirmed{{background:#dff1e5;color:#246b39}}.tag.unresolved{{background:#ffe1dc;color:#9d3029}}.tag.inferred{{background:#e8e5ff;color:#5748a7}}
.branches{{border-top:1px solid rgba(104,75,0,.18);padding-top:9px}}.branch-row{{display:grid;grid-template-columns:140px 1fr auto;gap:10px;font-size:12.5px;padding:5px 0}}.branch-row span{{font-weight:850}}.branch-row b{{font-weight:550}}.branch-row em{{font-style:normal;color:#7d5b00;font-weight:800}}
.connector{{min-height:72px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;position:relative}}.line{{height:30px;width:2px;background:var(--line);margin-top:4px}}.arrow{{font-size:13px;color:#697586;line-height:1}}.path-label{{margin-top:9px;display:flex;align-items:center;gap:8px;background:#f8fafc;border:1px solid #d8dee7;border-radius:6px;padding:4px 8px;font-size:11px;color:#475467;max-width:92%}}.path-label strong{{color:#24486d;white-space:nowrap}}.path-label span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.alternatives{{margin-top:2px;position:relative}}.alternatives:before{{content:"";position:absolute;left:-52px;top:31px;width:52px;border-top:2px dashed var(--red-border)}}.alternative{{background:var(--red);border:1.5px solid var(--red-border);border-radius:10px;padding:13px 15px;margin-bottom:10px;box-shadow:0 4px 9px rgba(104,38,32,.05)}}.alternative-label{{display:inline-block;background:#a93f36;color:white;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:850;margin-bottom:7px}}.alternative strong{{display:block;font-size:13px}}.alternative p{{margin:5px 0 0;font-size:12px;color:#7b3b36}}
.branch-decisions{{margin-top:26px;background:#fff;border:1px solid #dce2e9;border-radius:14px;padding:28px 32px 34px;box-shadow:0 12px 35px rgba(29,41,57,.05)}}.section-heading{{display:flex;justify-content:space-between;gap:32px;align-items:end;margin-bottom:22px}}.section-heading span{{font-size:12px;font-weight:850;color:#9c5f00;letter-spacing:.08em}}.section-heading h2{{font-size:25px;margin:3px 0 0}}.section-heading p{{max-width:650px;margin:0;color:var(--muted);font-size:13px}}.branch-decision-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}.branch-decision-item{{min-width:0}}.branch-entry{{margin:0 0 8px;padding:7px 10px;background:#f6f8fa;border-left:3px solid #7f8da2;color:#586579;font-size:12px}}.branch-entry strong{{margin-right:8px;color:#27364a}}
.footnote{{margin:20px 3px 0;font-size:13px;color:var(--muted)}}
@media(max-width:900px){{.page{{padding:25px 16px 45px}}.hero{{display:block}}.status{{display:inline-block;margin-top:16px}}.metrics{{grid-template-columns:1fr}}.flow,.branch-decisions{{padding:22px 12px}}.stage{{grid-template-columns:1fr;gap:0}}.alternatives{{margin:0 0 22px 22px}}.alternatives:before{{left:-22px;width:22px}}.branch-row{{grid-template-columns:1fr;gap:2px}}.branch-decision-grid{{grid-template-columns:1fr}}.section-heading{{display:block}}.section-heading p{{margin-top:8px}}h1{{font-size:30px}}}}
@media print{{body{{background:#fff}}.page{{max-width:none;padding:20px}}.flow{{box-shadow:none}}}}
</style>
</head>
<body>
<main class="page">
  <div class="brand">企业流程与决策还原 · 决策路径图</div>
  <div class="hero">
    <div><h1>{esc(process['number'])} {esc(process['name'])}</h1><p class="subtitle">{esc(model['company'])}｜主线表示主要推进路径，右侧分支保留每个关键决策的条件与去向。</p></div>
    <div class="status">● {esc(status)}</div>
  </div>
  <section class="metrics" aria-label="流程统计">
    <div class="metric"><strong>{len(decisions)}</strong><span>关键决策节点</span></div>
    <div class="metric"><strong>{len(pending)}</strong><span>待确认问题</span></div>
    <div class="metric"><strong>{len(model['nodes'])}</strong><span>流程节点</span></div>
  </section>
  <div class="legend"><span><i style="background:var(--blue);border:1px solid var(--blue-border)"></i>业务动作</span><span><i style="background:var(--yellow);border:1px solid var(--yellow-border)"></i>关键决策</span><span><i style="background:var(--red);border:1px solid var(--red-border)"></i>其他／待确认分支</span><span><i style="background:var(--green);border:1px solid var(--green-border)"></i>业务终态</span></div>
  <section class="flow" aria-label="{esc(process['name'])}决策路径图">
    {''.join(blocks)}
  </section>
  {branch_decisions}
  <p class="footnote">本图只还原输入资料。红色分支表示其他路径或当前资料未说明清楚的去向；“推断”和“待确认”不得视为企业既定事实。</p>
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
        lines.extend(f"{index}. {question}" for index, question in enumerate(pending, 1))
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
        outputs = render_files(model, args.output_dir)
        for output in outputs:
            print(output)
        return 0
    except ModelError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
