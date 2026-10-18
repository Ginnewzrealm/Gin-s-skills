#!/usr/bin/env python3
"""Render validated business-process JSON into Markdown and offline HTML."""

import argparse
import html
import json
import re
from pathlib import Path

from validate_process import validate

STATUS_LABELS = {
    "confirmed": "已确认事实",
    "inferred": "推导",
    "unknown": "待确认",
}
MODE_LABELS = {"manual": "人工", "automatic": "系统自动", "assisted": "人机协同"}
CARRIER_LABELS = {
    "system": "业务系统", "chat": "即时通讯", "email": "邮件",
    "spreadsheet": "电子表格", "paper": "纸质", "onsite": "线下现场", "other": "其他",
}


def _items(values, empty="无"):
    if not values:
        return empty
    return "；".join(str(value) for value in values)


def _require_valid(data):
    errors = validate(data)
    if errors:
        raise ValueError("流程数据验证失败：\n" + "\n".join(f"- {error}" for error in errors))


def render_markdown(data):
    _require_valid(data)
    nodes = {node["id"]: node for node in data["nodes"]}
    edges = {edge["id"]: edge for edge in data["edges"]}
    scene_order = {"main": 0, "exception": 1, "variant": 2}
    scenes = sorted(data["scenes"], key=lambda scene: (scene_order[scene["type"]], scene["id"]))
    lines = [
        f"# {data['process_name']}", "",
        f"> 版本：{data['version']}｜状态：{'已确认' if data['status'] == 'confirmed' else '草稿'}", "",
        "## 1. 流程概况与范围", "",
        f"- **流程编号**：{data['process_id']}",
        f"- **目的**：{data['purpose']}",
        f"- **起点**：{data['scope_start']}",
        f"- **终点**：{data['scope_end']}", "",
        "## 2. 参与角色与使用载体", "",
        f"- **参与角色**：{_items(data['participants'])}",
        f"- **系统与渠道**：{_items(data['systems_and_channels'])}", "",
        "## 3. 场景流程", "",
    ]

    for index, scene in enumerate(scenes, start=1):
        chinese_number = "一二三四五六七八九十"[index - 1] if index <= 10 else str(index)
        lines.extend([f"### 场景{chinese_number}：{scene['name']}", "", "```text"])
        lines.extend(_render_scene_tree(scene, nodes, edges))
        lines.extend(["```", "", f"- **岗位角色**：主责：{'、'.join(scene['owner_roles'])}", f"- **分界线**：{scene['boundary_rule']}"])
        lines.append("")

    lines.extend(["## 4. 软件操作与状态变化", "", "| 节点 | 岗位角色 | 软件位置／线下载体 | 软件操作 | 状态变化 |", "|---|---|---|---|---|"])
    for node in data["nodes"]:
        carrier = CARRIER_LABELS[node["carrier"]]
        if node["carrier_name"]:
            carrier += f"（{node['carrier_name']}）"
        location = node["software_location"] or carrier
        lines.append(f"| {node['id']} {node['name']} | {node['actor_role']} | {location} | {node['software_operation'] or '待确认'} | {node['state_before'] or '未定义'} → {node['state_after'] or '未定义'} |")

    lines.extend(["", "## 5. 产品待设计及待确认事项", ""])
    if data["open_questions"]:
        for question in data["open_questions"]:
            lines.append(f"- {question}（待设计／待确认）")
    else:
        lines.append("- 无")
    if data["future_expectations"]:
        lines.extend(["", "### 未来期望（不属于现状主流程）", ""])
        lines.extend(f"- {item}" for item in data["future_expectations"])

    lines.extend(["", "## 6. 事实来源与确认状态", "", "| 来源 | 类型 | 摘要 |", "|---|---|---|"])
    for source in data["sources"]:
        lines.append(f"| {source['id']} | {source['type']} | {source['summary']} |")
    lines.extend(["", "## 7. 节点明细附录", ""])
    for node in data["nodes"]:
        lines.extend([
            f"### {node['id']} · {node['name']}", "",
            f"- **确认状态**：{STATUS_LABELS[node['evidence_status']]}",
            f"- **现状事实**：{node['business_fact']}",
            f"- **岗位角色**：{node['actor_role']}",
            f"- **实际动作**：{node['business_action']}",
            f"- **业务规则**：{_items(node['rules'])}",
            f"- **输入／输出**：{_items(node['inputs'])} → {_items(node['outputs'])}",
            f"- **异常处理**：{_items(node['exceptions'])}",
            f"- **软件实现含义**：{_items(node['interface_implications'])}",
            f"- **证据引用**：{'、'.join(node['evidence_refs']) or '无'}", "",
        ])
    return "\n".join(lines)


def _flow_node_text(node):
    marker = {"start": "● 开始｜", "decision": "◇ ", "end": "■ 结束（闭环）｜"}.get(node.get("kind"), "")
    location = node.get("software_location") or node.get("carrier_name")
    context = " · ".join(item for item in [node.get("actor_role"), location] if item)
    return f"{marker}{node['name']}" + (f"（{context}）" if context else "")


def _render_scene_tree(scene, nodes, edges):
    scene_edges = [edges[edge_id] for edge_id in scene["edge_ids"]]
    outgoing = {}
    incoming = set()
    for edge in scene_edges:
        outgoing.setdefault(edge["from"], []).append(edge)
        incoming.add(edge["to"])
    roots = [edge["from"] for edge in scene_edges if edge["from"] not in incoming]
    if not roots and scene_edges:
        roots = [scene_edges[0]["from"]]
    roots = list(dict.fromkeys(roots))
    result = []

    def decision_details(node, prefix):
        if node.get("kind") != "decision":
            return
        result.append(prefix + f"  判断人：{node['decider_role']}")
        for criterion in node.get("criteria", []):
            result.append(prefix + f"  依据：{criterion}")
        result.append(prefix + f"  判不了：{node['fallback']}")

    def walk(node_id, prefix, visited, include_node=True):
        node = nodes[node_id]
        if include_node:
            result.append(prefix + _flow_node_text(node))
            decision_details(node, prefix)
        choices = outgoing.get(node_id, [])
        for offset, edge in enumerate(choices):
            last = offset == len(choices) - 1
            branch = "└─" if last else "├─"
            continuation = "  " if last else "│ "
            target_node = nodes[edge["to"]]
            result.append(prefix + branch + f" {edge['label']}：{edge['condition']} → " + _flow_node_text(target_node))
            target = edge["to"]
            if target in visited or edge["kind"] in {"rework", "cancel"}:
                result.append(prefix + continuation + f"  └─ 回到「{nodes[target]['name']}」")
            else:
                child_prefix = prefix + continuation + "  "
                decision_details(target_node, child_prefix)
                walk(target, child_prefix, visited | {target}, include_node=False)
            if not last:
                result.append("")

    for root_index, root in enumerate(roots):
        if root_index:
            result.append("")
        walk(root, "", {root})
    return result or ["该场景尚无已确认连线"]


def _layout_nodes(data):
    node_ids = [node["id"] for node in data["nodes"]]
    levels, rows = {}, {}
    outgoing = {}
    incoming_count = {node_id: 0 for node_id in node_ids}
    for edge in data["edges"]:
        if edge["kind"] in {"rework", "cancel"}:
            continue
        outgoing.setdefault(edge["from"], []).append(edge)
        incoming_count[edge["to"]] = incoming_count.get(edge["to"], 0) + 1
    roots = [node_id for node_id in node_ids if outgoing.get(node_id) and incoming_count.get(node_id, 0) == 0]
    start_ids = [node["id"] for node in data["nodes"] if node.get("kind") == "start" and outgoing.get(node["id"])]
    roots = list(dict.fromkeys(start_ids + roots))
    base_row = 0
    for root in roots + node_ids:
        if root in levels:
            continue
        levels[root], rows[root] = 0, base_row
        queue = [root]
        component_nodes = [root]
        while queue:
            source = queue.pop(0)
            choices = outgoing.get(source, [])
            next_level = levels[source] + 1
            for offset, edge in enumerate(choices):
                target = edge["to"]
                if target not in levels:
                    levels[target] = next_level
                    rows[target] = rows[source] + offset
                    queue.append(target)
                    component_nodes.append(target)
        base_row = max(rows[node_id] for node_id in component_nodes) + 2
    raw_levels = dict(levels)
    component_height = max(rows.values(), default=0) + 2
    for node_id, raw_level in raw_levels.items():
        levels[node_id] = raw_level % 6
        rows[node_id] += (raw_level // 6) * component_height
    return levels, rows


def _build_svg(data, svg_key="flow"):
    levels, rows = _layout_nodes(data)
    node_width, node_height = 148, 72
    x_gap, y_gap = 220, 130
    positions = {
        node["id"]: (60 + levels[node["id"]] * x_gap, 70 + rows[node["id"]] * y_gap)
        for node in data["nodes"]
    }
    width = max((x for x, _ in positions.values()), default=60) + node_width + 70
    height = max((y for _, y in positions.values()), default=70) + node_height + 80
    parts = [
        f'<svg viewBox="0 0 {width} {height}" style="width:{width}px;min-width:{width}px" role="img" aria-labelledby="{svg_key}-title {svg_key}-desc">',
        f'<title id="{svg_key}-title">{html.escape(data["process_name"])}</title>',
        f'<desc id="{svg_key}-desc">从{html.escape(data["scope_start"])}到{html.escape(data["scope_end"])}。</desc>',
        f'<defs><marker id="{svg_key}-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9Z" fill="#354249"/></marker></defs>',
    ]
    back_index = 0
    for edge in data["edges"]:
        sx, sy = positions[edge["from"]]
        tx, ty = positions[edge["to"]]
        start_x, start_y = sx + node_width, sy + node_height / 2
        end_x, end_y = tx, ty + node_height / 2
        if edge["kind"] not in {"rework", "cancel"} and tx > sx:
            mid_x = (start_x + end_x) / 2
            path = f"M{start_x} {start_y}H{mid_x}V{end_y}H{end_x}"
            label_x, label_y = mid_x, min(start_y, end_y) - 9
        else:
            bottom = height - 36 - back_index * 22
            back_index += 1
            path = f"M{start_x} {start_y}V{bottom}H{end_x - 22}V{end_y}H{end_x}"
            label_x, label_y = (start_x + end_x) / 2, bottom - 8
        kind = html.escape(edge["kind"])
        evidence = STATUS_LABELS[edge["evidence_status"]]
        refs = "、".join(edge["evidence_refs"]) or "无"
        title = f'{edge["id"]}｜{edge["condition"]}｜{evidence}｜证据：{refs}'
        parts.append(f'<path class="connector {kind}" style="marker-end:url(#{svg_key}-arrow)" d="{path}"><title>{html.escape(title)}</title></path>')
        label = edge["label"] or "流转"
        edge_text = f'{edge["id"]} · {label}'
        parts.append(f'<text class="edge-label" x="{label_x}" y="{label_y}">{html.escape(edge_text)}</text>')
    branched_targets = {edge["to"] for edge in data["edges"] if edge["kind"] in {"exception", "timeout", "cancel", "rework"}}
    for node in data["nodes"]:
        x, y = positions[node["id"]]
        branch_class = " branch" if node["id"] in branched_targets else ""
        name = html.escape(node["name"])
        node_class = f"flow-node {node['kind']}-node{branch_class}"
        if node["kind"] == "decision":
            shape = f'<polygon class="decision-shape" points="{node_width / 2},0 {node_width},{node_height / 2} {node_width / 2},{node_height} 0,{node_height / 2}"/>'
        else:
            radius = 32 if node["kind"] in {"start", "end"} else 8
            shape = f'<rect width="{node_width}" height="{node_height}" rx="{radius}"/>'
        raw_name = str(node["name"])
        if len(raw_name) <= 8:
            name_markup = f'<text x="{node_width / 2}" y="48">{name}</text>'
        else:
            first = html.escape(raw_name[:8])
            remainder = raw_name[8:]
            second = html.escape(remainder if len(remainder) <= 9 else remainder[:8] + "…")
            name_markup = (
                f'<text x="{node_width / 2}" y="42"><tspan x="{node_width / 2}" y="42">{first}</tspan>'
                f'<tspan x="{node_width / 2}" y="60">{second}</tspan></text>'
            )
        parts.append(
            f'<g class="{node_class}" data-node="{html.escape(node["id"])}" tabindex="0" role="link" '
            f'aria-label="查看 {html.escape(node["id"])} {name}说明" transform="translate({x} {y})">'
            f'{shape}<text class="node-id" x="{node_width / 2}" y="20">{html.escape(node["id"])}</text>'
            f'{name_markup}</g>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _node_card(node):
    status = node["evidence_status"]
    implications = "；".join(html.escape(item) for item in node["interface_implications"]) or "无"
    exceptions = "；".join(html.escape(item) for item in node["exceptions"]) or "无"
    carrier = CARRIER_LABELS[node["carrier"]]
    if node["carrier_name"]:
        carrier += f"（{node['carrier_name']}）"
    pairs = [
        ("现状事实", node["business_fact"]),
        ("岗位角色", node["actor_role"]),
        ("执行方式", MODE_LABELS[node["execution_mode"]]),
        ("发生载体", carrier),
        ("进入信号", node["entry_or_signal"] or "待确认"),
        ("实际动作", node["business_action"]),
        ("业务规则", "；".join(node["rules"]) or "无"),
        ("软件位置", node["software_location"] or "待确认"),
        ("软件操作", node["software_operation"] or "待确认"),
        ("完成信号", node["completion_signal"] or "待确认"),
        ("状态变化", f"{node['state_before'] or '未定义'} → {node['state_after'] or '未定义'}"),
        ("异常处理", exceptions),
        ("证据引用", "、".join(node["evidence_refs"]) or "无"),
    ]
    if node.get("kind") == "decision":
        pairs.extend([
            ("判断人", node["decider_role"]),
            ("判断依据", "；".join(node["criteria"])),
            ("判不了怎么办", node["fallback"]),
        ])
    details = "".join(f"<dt>{html.escape(label)}</dt><dd>{html.escape(str(value))}</dd>" for label, value in pairs)
    details += f'<dt>软件实现含义</dt><dd><span class="implication">{implications}</span></dd>'
    return (
        f'<article class="card {status}" id="detail-{html.escape(node["id"])}">'
        f'<div class="card-head"><h3>{html.escape(node["id"])} · {html.escape(node["name"])}{" · 决策点" if node.get("kind") == "decision" else ""}</h3>'
        f'<span class="badge">{STATUS_LABELS[status]}</span></div><dl class="fact-grid">{details}</dl></article>'
    )


def render_html(data, template):
    _require_valid(data)
    cards = "".join(_node_card(node) for node in data["nodes"])
    questions = data["open_questions"]
    futures = data["future_expectations"]
    pending_items = "".join(f"<li>{html.escape(item)}</li>" for item in questions)
    pending_items += "".join(f"<li>未来期望：{html.escape(item)}</li>" for item in futures)
    pending = (
        f'<aside class="pending"><h3>产品待设计事项与待确认问题</h3><ul>{pending_items or "<li>无</li>"}</ul></aside>'
    )
    source_rows = "".join(
        f'<tr><td>{html.escape(source["id"])}</td><td>{html.escape(source["type"])}</td><td>{html.escape(source["summary"])}</td></tr>'
        for source in data["sources"]
    )
    source_body = source_rows or '<tr><td colspan="3">无</td></tr>'
    sources = (
        '<section class="sources"><h3>事实来源</h3><table><thead><tr><th>来源</th><th>类型</th><th>摘要</th></tr></thead>'
        f'<tbody>{source_body}</tbody></table></section>'
    )
    node_by_id = {node["id"]: node for node in data["nodes"]}
    edge_by_id = {edge["id"]: edge for edge in data["edges"]}
    scene_order = {"main": 0, "exception": 1, "variant": 2}
    scenes = sorted(data["scenes"], key=lambda scene: (scene_order[scene["type"]], scene["id"]))
    tabs = []
    panels = []
    for index, scene in enumerate(scenes):
        active = " active" if index == 0 else ""
        tabs.append(f'<button class="scene-tab{active}" type="button" data-scene="{html.escape(scene["id"])}" aria-selected="{"true" if index == 0 else "false"}">{html.escape(scene["name"])}</button>')
        scene_edges = [edge_by_id[edge_id] for edge_id in scene["edge_ids"]]
        used_ids = {edge["from"] for edge in scene_edges} | {edge["to"] for edge in scene_edges}
        scene_data = {**data, "nodes": [node for node in data["nodes"] if node["id"] in used_ids], "edges": scene_edges}
        edge_rows = "".join(
            f'<tr><td>{html.escape(edge["id"])}</td><td>{html.escape(edge["label"] or "流转")}</td>'
            f'<td>{html.escape(edge["condition"])}</td><td>{html.escape(STATUS_LABELS[edge["evidence_status"]])}</td>'
            f'<td>{html.escape("、".join(edge["evidence_refs"]) or "无")}</td></tr>'
            for edge in scene_edges
        )
        edge_details = (
            '<div class="edge-details"><h3>流转条件</h3><table><thead><tr><th>连线</th><th>名称</th><th>进入条件</th><th>确认状态</th><th>证据</th></tr></thead>'
            f'<tbody>{edge_rows}</tbody></table></div>'
        )
        panels.append(
            f'<section class="scene-panel{active}" data-scene-panel="{html.escape(scene["id"])}">'
            f'<div class="scene-caption"><strong>{html.escape(scene["name"])}</strong><span>主责：{html.escape("、".join(scene["owner_roles"]))}</span><span>{html.escape(scene["boundary_rule"])}</span></div>'
            f'<div class="diagram-shell">{_build_svg(scene_data, scene["id"].lower())}</div>{edge_details}</section>'
        )
    scene_markup = f'<nav class="scene-tabs" aria-label="流程场景">{"".join(tabs)}</nav><div class="print-all-scenes">{"".join(panels)}</div>'
    replacements = {
        "{{TITLE}}": html.escape(data["process_name"]),
        "{{VERSION}}": html.escape(data["version"]),
        "{{SCENES}}": scene_markup,
        "{{CARDS}}": cards,
        "{{PENDING}}": pending,
        "{{SOURCES}}": sources,
        "{{STATUS_LABEL}}": "已确认" if data["status"] == "confirmed" else "草稿",
        "{{STATUS_CLASS}}": "confirmed" if data["status"] == "confirmed" else "draft",
    }
    output = template
    for marker, value in replacements.items():
        output = output.replace(marker, value)
    return output


def _safe_name(name):
    cleaned = re.sub(r"[\\/:*?\"<>|]", "-", name).strip(" .")
    return cleaned or "未命名流程"


def main(argv=None):
    parser = argparse.ArgumentParser(description="从结构化 JSON 生成流程 Markdown 和离线 HTML")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    _require_valid(data)
    template_path = Path(__file__).resolve().parents[1] / "assets/process-report-template.html"
    template = template_path.read_text(encoding="utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = _safe_name(data["process_name"])
    outputs = {
        args.output_dir / f"{base}-流程说明.md": render_markdown(data),
        args.output_dir / f"{base}-流程图.html": render_html(data, template),
    }
    existing = [str(path) for path in outputs if path.exists()]
    if existing and not args.overwrite:
        parser.error("输出文件已存在；如需更新请使用 --overwrite：" + "，".join(existing))
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
