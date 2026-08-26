#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence_to_skill_detail.py — 将 behavioral_evidence 碎片转换为 skill_details 五维块。

用途：当某条 STAR 行为证据对应一个已知技能时，自动/半自动生成 skill_details.md 条目，
供简历「岗位胜任」或技能详细描述使用。

转换映射：
- 情境 ← Background + Task
- 行动 ← Action
- 结果 ← Result
- 沉淀 ← Key Insight + Boundary
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


def parse_be_file(path):
    """解析单个 be_*.md 文件，返回 frontmatter + 段落 dict。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    fm = parts[1]
    body = parts[2]

    meta = {}
    for line in fm.splitlines():
        m = re.match(r"(\w+):\s*(.*)", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()

    sections = {}
    current_key = None
    for line in body.splitlines():
        if line.startswith("## "):
            current_key = line[3:].strip()
            sections[current_key] = []
        elif current_key is not None:
            sections[current_key].append(line)

    return {
        "meta": meta,
        "sections": {k: "\n".join(v).strip() for k, v in sections.items()},
    }


def convert_to_five_dims(be_data):
    """把 behavioral_evidence 的段落转成 skill_details 的四维。"""
    s = be_data["sections"]
    situation = " ".join(filter(None, [s.get("背景（Background）", ""), s.get("任务（Task）", "")])).strip()
    action_lines = [l.strip("- ") for l in s.get("行动（Action）", "").splitlines() if l.strip().startswith("-")]
    action = "；".join(action_lines) if action_lines else s.get("行动（Action）", "")
    result = s.get("结果（Result）", "")
    insight = s.get("关键判断（Key Insight）", "")
    boundary = s.get("边界条件（Boundary）", "")
    沉淀_parts = [insight]
    if boundary:
        沉淀_parts.append("边界：%s" % boundary)
    沉淀 = "；".join(filter(None, 沉淀_parts))
    return {
        "情境": situation,
        "行动": action,
        "结果": result,
        "沉淀": 沉淀,
    }


def skill_detail_exists(root, skill_name):
    """检查 skill_details.md 是否已有该技能。"""
    text = common.read_raw(root, "skill_details")
    for e in common.parse_entries(text):
        if e["title"] == skill_name:
            return True
    return False


def append_skill_detail(root, skill_name, dims):
    """追加一个技能五维块到 skill_details.md。"""
    path = os.path.join(root, common.DIR_RAW, "skill_details.md")
    lines = ["\n## %s" % skill_name]
    for k in ("情境", "行动", "结果", "沉淀"):
        v = dims.get(k, "").strip()
        if not v:
            v = "（待补充）"
        lines.append("- %s：%s" % (k, v))
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    ap.add_argument("--skill", required=True, help="目标技能名")
    ap.add_argument("--evidence", default=None, help="指定 be_xxx.md 文件名；不指定则自动匹配")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写入")
    args = ap.parse_args()

    root = common.kb_root(args.kb)
    ev_dir = os.path.join(root, common.DIR_RAW, "behavioral_evidence")
    if not os.path.isdir(ev_dir):
        raise SystemExit("[错误] 没有找到 behavioral_evidence 目录")

    candidates = []
    if args.evidence:
        path = os.path.join(ev_dir, args.evidence)
        if not os.path.exists(path):
            raise SystemExit("[错误] 找不到 %s" % args.evidence)
        candidates.append(path)
    else:
        for name in os.listdir(ev_dir):
            if not name.startswith("be_") or not name.endswith(".md"):
                continue
            be = parse_be_file(os.path.join(ev_dir, name))
            if be and args.skill.lower() in be["meta"].get("description", "").lower():
                candidates.append(os.path.join(ev_dir, name))

    if not candidates:
        raise SystemExit("[错误] 没有匹配 '%s' 的 behavioral_evidence 碎片" % args.skill)

    print("找到 %d 条匹配 '%s' 的 STAR 碎片" % (len(candidates), args.skill))

    # 合并多个碎片的五维：每个维度取最长/最完整的一条
    merged = {"情境": [], "行动": [], "结果": [], "沉淀": []}
    for path in candidates:
        be = parse_be_file(path)
        dims = convert_to_five_dims(be)
        for k, v in dims.items():
            if v and v != "（待补充）":
                merged[k].append(v)

    final = {k: "\n".join(v) if k != "行动" else "；".join(v) for k, v in merged.items()}

    print("\n转换后的 skill_details 草稿：")
    print("## %s" % args.skill)
    for k in ("情境", "行动", "结果", "沉淀"):
        print("- %s：%s" % (k, final.get(k, "（待补充）")))

    if args.dry_run:
        print("\n[干跑] 未写入")
        return

    if skill_detail_exists(root, args.skill):
        print("\n[警告] skill_details.md 中已存在 '%s'，跳过写入，请手动合并" % args.skill)
        return

    append_skill_detail(root, args.skill, final)
    print("\n[完成] 已追加到原始事实/skill_details.md")


if __name__ == "__main__":
    main()
