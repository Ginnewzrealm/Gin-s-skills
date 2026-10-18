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
        "## 3. 现状流程概览", "",
    ]
    for edge in data["edges"]:
        status = STATUS_LABELS[edge["evidence_status"]]
        condition = f"（{edge['condition']}）" if edge["condition"] else ""
        lines.append(f"- `{edge['from']}` → `{edge['to']}`：{edge['label']}{condition} · {status}")

    lines.extend(["", "## 4. 节点详细说明", ""])
    for node in data["nodes"]:
        carrier_text = CARRIER_LABELS[node["carrier"]]
        if node["carrier_name"]:
            carrier_text += f"（{node['carrier_name']}）"
        lines.extend([
            f"### {node['id']} · {node['name']}", "",
            f"- **确认状态**：{STATUS_LABELS[node['evidence_status']]}",
            f"- **现状事实**：{node['business_fact']}",
            f"- **执行者**：{node['actor']}",
            f"- **执行方式**：{MODE_LABELS[node['execution_mode']]}",
            f"- **发生载体**：{carrier_text}",
            f"- **进入信号**：{node['entry_or_signal'] or '待确认'}",
            f"- **实际动作**：{node['business_action']}",
            f"- **输入**：{_items(node['inputs'])}",
            f"- **输出**：{_items(node['outputs'])}",
            f"- **完成信号**：{node['completion_signal'] or '待确认'}", "",
        ])

    lines.extend(["## 5. 决策与异常处理", ""])
    for edge in data["edges"]:
        if edge["kind"] != "normal":
            lines.append(f"- **{edge['from']} → {edge['to']}**：{edge['label']}；条件：{edge['condition'] or '待确认'}；{STATUS_LABELS[edge['evidence_status']]}")
    for node in data["nodes"]:
        for exception in node["exceptions"]:
            lines.append(f"- **{node['id']}**：{exception}")
    if lines[-1] == "":
        lines.append("- 无")

    lines.extend(["", "## 6. 状态变化", "", "| 节点 | 操作前 | 操作后 | 状态 |", "|---|---|---|---|"])
    for node in data["nodes"]:
        lines.append(f"| {node['id']} {node['name']} | {node['state_before'] or '未定义'} | {node['state_after'] or '未定义'} | {STATUS_LABELS[node['evidence_status']]} |")

    lines.extend(["", "## 7. 软件实现含义", ""])
    for node in data["nodes"]:
        for implication in node["interface_implications"]:
            lines.append(f"- **{node['id']}**：{implication}（从业务事实推导）")

    lines.extend(["", "## 8. 产品待设计事项", ""])
    if data["open_questions"]:
        for question in data["open_questions"]:
            lines.append(f"- {question}（待设计／待确认）")
    else:
        lines.append("- 无")
    if data["future_expectations"]:
        lines.extend(["", "### 未来期望（不属于现状主流程）", ""])
        lines.extend(f"- {item}" for item in data["future_expectations"])

    lines.extend(["", "## 9. 待确认问题", ""])
    lines.extend(f"- {item}" for item in data["open_questions"])
    if not data["open_questions"]:
        lines.append("- 无")

    lines.extend(["", "## 10. 事实来源与确认状态", "", "| 来源 | 类型 | 摘要 |", "|---|---|---|"])
    for source in data["sources"]:
        lines.append(f"| {source['id']} | {source['type']} | {source['summary']} |")
    lines.append("")
    return "\n".join(lines)


def _layout_nodes(data):
    levels = {data["nodes"][0]["id"]: 0}
    rows = {data["nodes"][0]["id"]: 0}
    outgoing = {}
    for edge in data["edges"]:
        outgoing.setdefault(edge["from"], []).append(edge)
    queue = [data["nodes"][0]["id"]]
    while queue:
        source = queue.pop(0)
        edges = outgoing.get(source, [])
        for offset, edge in enumerate(edges):
            target = edge["to"]
            next_level = levels[source] + 1
            if target not in levels or next_level > levels[target]:
                levels[target] = next_level
                row = rows[source]
                if len(edges) > 1 and offset:
                    row = rows[source] + offset
                if edge["kind"] in {"exception", "timeout", "cancel", "rework"}:
                    row = max(1, row)
                rows[target] = row
                queue.append(target)
    max_level = max(levels.values(), default=0)
    for index, node in enumerate(data["nodes"]):
        levels.setdefault(node["id"], max_level + 1 + index)
        rows.setdefault(node["id"], 0)
    return levels, rows


def _build_svg(data):
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
        f'<svg viewBox="0 0 {width} {height}" style="width:{width}px;min-width:{width}px" role="img" aria-labelledby="flow-title flow-desc">',
        f'<title id="flow-title">{html.escape(data["process_name"])}</title>',
        f'<desc id="flow-desc">从{html.escape(data["scope_start"])}到{html.escape(data["scope_end"])}。</desc>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9Z" fill="#354249"/></marker></defs>',
    ]
    for edge in data["edges"]:
        sx, sy = positions[edge["from"]]
        tx, ty = positions[edge["to"]]
        start_x, start_y = sx + node_width, sy + node_height / 2
        end_x, end_y = tx, ty + node_height / 2
        if tx > sx:
            mid_x = (start_x + end_x) / 2
            path = f"M{start_x} {start_y}H{mid_x}V{end_y}H{end_x}"
            label_x, label_y = mid_x, min(start_y, end_y) - 9
        else:
            bottom = height - 36
            path = f"M{start_x} {start_y}V{bottom}H{end_x - 22}V{end_y}H{end_x}"
            label_x, label_y = (start_x + end_x) / 2, bottom - 8
        kind = html.escape(edge["kind"])
        parts.append(f'<path class="connector {kind}" d="{path}"/>')
        label = edge["label"] or edge["condition"]
        if label:
            parts.append(f'<text class="edge-label" x="{label_x}" y="{label_y}">{html.escape(label)}</text>')
    branched_targets = {edge["to"] for edge in data["edges"] if edge["kind"] != "normal"}
    for node in data["nodes"]:
        x, y = positions[node["id"]]
        branch_class = " branch" if node["id"] in branched_targets else ""
        name = html.escape(node["name"])
        parts.append(
            f'<g class="flow-node{branch_class}" data-node="{html.escape(node["id"])}" tabindex="0" role="link" '
            f'aria-label="查看 {html.escape(node["id"])} {name}说明" transform="translate({x} {y})">'
            f'<rect width="{node_width}" height="{node_height}" rx="8"/>'
            f'<text class="node-id" x="{node_width / 2}" y="20">{html.escape(node["id"])}</text>'
            f'<text x="{node_width / 2}" y="48">{name}</text></g>'
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
        ("执行者", node["actor"]),
        ("执行方式", MODE_LABELS[node["execution_mode"]]),
        ("发生载体", carrier),
        ("进入信号", node["entry_or_signal"] or "待确认"),
        ("实际动作", node["business_action"]),
        ("完成信号", node["completion_signal"] or "待确认"),
        ("状态变化", f"{node['state_before'] or '未定义'} → {node['state_after'] or '未定义'}"),
        ("异常处理", exceptions),
    ]
    details = "".join(f"<dt>{html.escape(label)}</dt><dd>{html.escape(str(value))}</dd>" for label, value in pairs)
    details += f'<dt>软件实现含义</dt><dd><span class="implication">{implications}</span></dd>'
    return (
        f'<article class="card {status}" id="detail-{html.escape(node["id"])}">'
        f'<div class="card-head"><h3>{html.escape(node["id"])} · {html.escape(node["name"])}</h3>'
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
    replacements = {
        "{{TITLE}}": html.escape(data["process_name"]),
        "{{VERSION}}": html.escape(data["version"]),
        "{{SVG}}": _build_svg(data),
        "{{CARDS}}": cards,
        "{{PENDING}}": pending,
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
