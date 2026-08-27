#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从碎片和主题定义生成最终素材文档。"""

import os
import re

import common
import fragment
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
):
    paths = fragment.list_fragments(material_root, topic)
    v = validate.validate_session(material_root, topic)

    # 按方向分组
    grouped = {s: [] for s in SECTION_ORDER}
    for p in paths:
        fm, body = fragment.read(p)
        direction = fm.get("direction", "")
        if direction in grouped:
            grouped[direction].append((fm, body, p))

    # 生成素材编号
    counter = 1
    numbered = {}
    for s in SECTION_ORDER:
        for item in grouped[s]:
            numbered[item[2]] = counter
            counter += 1

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
    lines.append("---")
    lines.append("")
    lines.append(f"# {topic}")
    lines.append("")
    lines.append("## 真实问题")
    lines.append(key_question)
    lines.append("")
    lines.append("## 给 human-writing 的输入")
    lines.append("")
    lines.append("### 说话位置")
    lines.append(f"- **谁在说**：{scope.get('作者身份', '（待补充）')}")
    lines.append(f"- **为什么现在说**：{scope.get('触发原因', '（待补充）')}")
    material_refs = ", ".join(f"素材 #{i}" for i in numbered.values()) or "（待补充）"
    lines.append(f"- **能托住文章的材料**：{material_refs}")
    lines.append(f"- **明确判断**：{judgment}")
    lines.append(f"- **读者会追问什么**：{reader_question}")
    lines.append("")
    lines.append("### 材料清单")
    lines.append("| 编号 | 来源类型 | 关键原话/事实 | 来源锚点 | 置信度 |")
    lines.append("|------|---------|--------------|---------|--------|")
    for s in SECTION_ORDER:
        for fm, body, p in grouped[s]:
            quote = _extract_field(body, "原话")[:30] + "..."
            anchor = fm.get("anchor", "")
            conf = fm.get("confidence", "")
            lines.append(f"| 素材 #{numbered[p]} | user_verbatim | {quote} | {anchor} | {conf} |")
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
            lines.append("")

    lines.append("## 来源索引")
    lines.append("| 素材编号 | 碎片文件 | 方法 | 置信度 |")
    lines.append("|---------|---------|------|--------|")
    for s in SECTION_ORDER:
        for fm, body, p in grouped[s]:
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


def _extract_field(body, field):
    pattern = rf"## {re.escape(field)}\n(.*?)((?=\n## )|$)"
    m = re.search(pattern, body, re.S)
    if not m:
        return ""
    return m.group(1).strip()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common
