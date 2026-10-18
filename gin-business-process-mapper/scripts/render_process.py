#!/usr/bin/env python3
"""Render validated business-process JSON into human-readable outputs."""

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
