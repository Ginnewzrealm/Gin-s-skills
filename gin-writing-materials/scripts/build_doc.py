#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从碎片和主题定义生成最终素材文档。"""

import os
import re

import common
import fragment
import session
import topic_def
import validate


SECTION_ORDER = ["钩子", "核心论证", "案例支撑", "结尾升华"]


def build(
    material_root,
    topic,
    key_question,
    scope,
    success_criteria,
    constraints,
    hypotheses,
    judgment,
    reader_question,
    force=False,
):
    paths = fragment.list_fragments(material_root, topic)
    v = validate.validate_session(material_root, topic)
    if v["errors"] and not force:
        raise ValueError("碎片校验失败：" + "；".join(v["errors"]))

    # 按方向分组
    grouped = {s: [] for s in SECTION_ORDER}
    ungrouped = []
    for p in paths:
        fm, body = fragment.read(p)
        direction = fm.get("direction", "")
        if direction in grouped:
            grouped[direction].append((fm, body, p))
        else:
            ungrouped.append((fm, body, p))

    # 生成素材编号
    counter = 1
    numbered = {}
    for s in SECTION_ORDER:
        for item in grouped[s]:
            numbered[item[2]] = counter
            counter += 1
    for item in ungrouped:
        numbered[item[2]] = counter
        counter += 1

    state = session.load_or_create(material_root, topic)
    closure = state.get("closure", {})

    lines = []
    lines.append("---")
    lines.append(f"topic: {topic}")
    lines.append("domain: writing")
    lines.append(f"created: {common.today_str()}")
    lines.append(f"fragments_count: {len(paths)}")
    lines.append("status: material_ready")
    lines.append(f"confirmed_count: {v['confirmed_count']}")
    lines.append(f"fuzzy_count: {v['fuzzy_count']}")
    covered = [s for s in SECTION_ORDER if grouped[s]]
    lines.append(f"sections_covered: {covered}")
    lines.append(f"knowledge_closure: {state.get('closure', {}).get('knowledge', 'open')}")
    lines.append(f"public_material: {closure.get('public_material', 'unknown')}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {topic}")
    lines.append("")
    lines.append("## 原始灵感")
    lines.append(state.get("seed", topic))
    lines.append("")
    lines.append("## 真实问题")
    lines.append(key_question)
    lines.append("")
    lines.append("## 给 human-writing 的输入")
    lines.append("")
    lines.append("### 说话位置")
    for label in ["读者", "文体", "篇幅目标", "在范围内", "不在范围内"]:
        if scope.get(label):
            lines.append(f"- **{label}**：{scope[label]}")
    lines.append(f"- **谁在说**：{scope.get('作者身份', '（待补充）')}")
    lines.append(f"- **为什么现在说**：{scope.get('触发原因', '（待补充）')}")
    material_refs = ", ".join(f"素材 #{i}" for i in numbered.values()) or "（待补充）"
    lines.append(f"- **能托住文章的材料**：{material_refs}")
    lines.append(f"- **明确判断**：{judgment}")
    lines.append(f"- **读者会追问什么**：{reader_question}")
    lines.append("")
    lines.append("### 主线状态")
    lines.append(f"- **主问题**：{state.get('main_qud') or key_question}")
    lines.append(f"- **当前子问题**：{state.get('current_qud') or '（待补充）'}")
    if state.get("p_x_r", {}).get("P"):
        lines.append(f"- **待解释现象**：{state['p_x_r']['P']}")
        lines.append(f"- **对比预期**：{state['p_x_r'].get('X', '')}")
        lines.append(f"- **解释类型**：{state['p_x_r'].get('R', '')}")
    lines.append("")
    lines.append("## 收束状态")
    lines.append(f"- **知识闭环**：{closure.get('knowledge', 'open')}")
    lines.append(f"- **用户已确认**：{'是' if closure.get('confirmed') else '否'}")
    lines.append(f"- **公开素材范围**：{closure.get('public_material', 'unknown')}")
    unresolved = closure.get("unresolved", [])
    if unresolved:
        lines.append("- **未解决问题**：" + "；".join(unresolved))
    else:
        lines.append("- **未解决问题**：（暂无登记）")
    lines.append("")
    lines.append("## 主线与旁支")
    branches = state.get("branches", [])
    if branches:
        for branch in branches:
            lines.append(f"- **{branch.get('id', '')}**：{branch.get('summary', '')}（{branch.get('status', 'queued')}）")
    else:
        lines.append("- （暂无已登记旁支）")
    lines.append("")
    lines.append("### 成功标准")
    for item in success_criteria or ["（待补充）"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("### 约束")
    for item in constraints or ["（待补充）"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("### 材料清单")
    lines.append("| 编号 | 来源类型 | 关键原话/事实 | 来源锚点 | 置信度 |")
    lines.append("|------|---------|--------------|---------|--------|")
    for s in SECTION_ORDER:
        for fm, body, p in grouped[s]:
            quote_field = _extract_field(body, "原话")
            quote = quote_field[:30] + "..." if len(quote_field) > 30 else quote_field
            anchor = fm.get("anchor", "")
            conf = fm.get("confidence", "")
            lines.append(f"| 素材 #{numbered[p]} | {fm.get('source_type', 'user_verbatim')} | {quote} | {anchor} | {conf} |")
    for fm, body, p in ungrouped:
        quote_field = _extract_field(body, "原话")
        quote = quote_field[:30] + "..." if len(quote_field) > 30 else quote_field
        lines.append(f"| 素材 #{numbered[p]} | {fm.get('source_type', 'user_verbatim')} | {quote} | {fm.get('anchor', '')} | {fm.get('confidence', '')} |")
    lines.append("")
    lines.append("### 关键变量")
    for h in hypotheses:
        lines.append(f"- {h}")
    lines.append("")
    lines.append("### 用户当前最想下的判断")
    lines.append(judgment)
    lines.append("")
    lines.append("---")
    lines.append("")

    for s in SECTION_ORDER:
        if not grouped[s]:
            continue
        lines.append(f"## {s}")
        lines.append("")
        for fm, body, p in grouped[s]:
            idx = numbered[p]
            lines.append(f"### 素材 #{idx}")
            for field in ["原话", "场景", "解读", "关联锚点"]:
                val = _extract_field(body, field)
                if field == "解读":
                    lines.append(f"- **{field}**：")
                    for line in val.splitlines():
                        if line.strip().startswith("-"):
                            lines.append(f"  {line.strip()}")
                else:
                    lines.append(f"- **{field}**：{val}")
            lines.append(f"- **方法**：{fm.get('method', '')}")
            lines.append(f"- **置信度**：{fm.get('confidence', '')}")
            lines.append(f"- **角色**：{fm.get('role', 'core')}")
            lines.append(f"- **关系**：{fm.get('relation', 'support')}")
            lines.append(f"- **来源轮次**：{fm.get('source_turn', '')}")
            lines.append("")

    if ungrouped:
        lines.append("## 未分类素材")
        lines.append("")
        for fm, body, p in ungrouped:
            idx = numbered[p]
            lines.append(f"### 素材 #{idx}")
            lines.append(f"- **原话**：{_extract_field(body, '原话')}")
            lines.append(f"- **场景**：{_extract_field(body, '场景')}")
            lines.append(f"- **解读**：{_extract_field(body, '解读')}")
            lines.append(f"- **角色**：{fm.get('role', 'core')}")
            lines.append(f"- **来源轮次**：{fm.get('source_turn', '')}")
            lines.append("")

    lines.append("## 来源索引")
    lines.append("| 素材编号 | 碎片文件 | 方法 | 置信度 |")
    lines.append("|---------|---------|------|--------|")
    for s in SECTION_ORDER:
        for fm, body, p in grouped[s]:
            idx = numbered[p]
            rel = os.path.relpath(p, material_root)
            lines.append(f"| #{idx} | {rel} | {fm.get('method', '')} | {fm.get('confidence', '')} |")
    for fm, body, p in ungrouped:
        idx = numbered[p]
        rel = os.path.relpath(p, material_root)
        lines.append(f"| #{idx} | {rel} | {fm.get('method', '')} | {fm.get('confidence', '')} |")
    lines.append("")
    lines.append("## Retrospective")
    lines.append("- 最薄的素材：（待用户/下次补充）")
    lines.append("- 下次可补的方向：（待用户/下次补充）")

    out_path = common.material_doc_path(material_root, topic)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="从主题定义和素材碎片生成素材文档")
    parser.add_argument("--material-root", required=True, help="素材库根目录")
    parser.add_argument("--topic", required=True, help="主题名")
    parser.add_argument("--judgment", default="（待补充）", help="作者当前判断")
    parser.add_argument("--reader-question", default="（待补充）", help="读者追问")
    parser.add_argument("--force", action="store_true", help="忽略碎片字段校验错误")
    args = parser.parse_args()

    definition = topic_def.read(args.material_root, args.topic)
    path = build(
        material_root=args.material_root,
        topic=args.topic,
        key_question=definition["key_question"],
        scope=definition["scope"],
        success_criteria=definition["success_criteria"],
        constraints=definition["constraints"],
        hypotheses=definition["hypotheses"],
        judgment=args.judgment,
        reader_question=args.reader_question,
        force=args.force,
    )
    print(f"素材文档已生成：{path}")
    return 0


def _extract_field(body, field):
    pattern = rf"## {re.escape(field)}\n(.*?)((?=\n## )|$)"
    m = re.search(pattern, body, re.S)
    if not m:
        return ""
    return m.group(1).strip()


if __name__ == "__main__":
    raise SystemExit(main())
