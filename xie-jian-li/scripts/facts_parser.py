#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""facts_parser.py — 解析 knowledge/原始事实/*.md → 自动生成/facts.yaml。

facts.yaml 是后续所有管线脚本的输入起点（Single Source of Truth 的结构化索引）。
事实条目带稳定 fact_id，供溯源校验（provenance_verifier）回查。

用法:
    python3 facts_parser.py [--kb 知识库路径]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def parse_behavioral_evidence(root):
    """解析 kb_path/原始事实/behavioral_evidence/*.md，返回 STAR 证据列表。"""
    ev_dir = os.path.join(root, common.DIR_RAW, "behavioral_evidence")
    if not os.path.isdir(ev_dir):
        return []

    items = []
    for name in os.listdir(ev_dir):
        if not name.startswith("be_") or not name.endswith(".md"):
            continue
        path = os.path.join(ev_dir, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()

        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
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

        items.append({
            "fact_id": meta.get("name", name[:-3]),
            "type": "behavioral_evidence",
            "domain": meta.get("domain", "unknown"),
            "description": meta.get("description", ""),
            "source": meta.get("source", ""),
            "confidence": meta.get("confidence", "fuzzy"),
            "created": meta.get("created", ""),
            "sections": {k: "\n".join(v).strip() for k, v in sections.items()},
        })
    return items


def build_facts(root):
    facts = []

    # 基本信息：- key: value
    basic = {}
    for item in common.parse_bullet_list(common.read_raw(root, "basic_info")):
        m = re.match(r"([^:：]+)[:：]\s*(.*)", item)
        if m:
            basic[m.group(1).strip()] = m.group(2).strip()

    # 工作经历
    for i, e in enumerate(common.parse_entries(common.read_raw(root, "work_history")), 1):
        facts.append({
            "fact_id": "W%d" % i, "type": "work",
            "company": e["title"], "role": e["role"], "period": e["period"],
            "years": common.years_of_experience(e["period"]),
            "bullets": e["bullets"],
        })

    # 项目经历
    for i, e in enumerate(common.parse_entries(common.read_raw(root, "projects")), 1):
        facts.append({
            "fact_id": "P%d" % i, "type": "project",
            "name": e["title"], "role": e["role"], "period": e["period"],
            "bullets": e["bullets"],
        })

    # 技能：两段结构（## 通用能力 / ## 专属能力）；无分节旧格式全部视为专属能力
    raw_skills = common.read_raw(root, "skills")
    skill_sections = common.parse_entries(raw_skills)
    if skill_sections:
        skills_general = []
        skills_domain = []
        for e in skill_sections:
            if e["title"] == "通用能力":
                skills_general.extend(e["bullets"])
            else:
                skills_domain.extend(e["bullets"])
        # 首个 ## 之前的游离 bullet（旧格式残留）按专属能力计
        head = raw_skills.split("## ", 1)[0]
        skills_domain = common.parse_bullet_list(head) + skills_domain
    else:
        skills_general = []
        skills_domain = common.parse_bullet_list(raw_skills)
    skills = skills_general + skills_domain  # 平铺全量（ATS 匹配、摘要统计用）
    advantages = common.parse_bullet_list(common.read_raw(root, "advantages"))

    # 技能详情（## 技能名 + - 维度：内容），深挖产物，见 references/skill-mining-playbook.md
    skill_details = {}
    for e in common.parse_entries(common.read_raw(root, "skill_details")):
        dims = {}
        for b in e["bullets"]:
            m = re.match(r"(情境|行动|结果|沉淀)\s*[:：]\s*(.*)", b)
            if m:
                dims[m.group(1)] = m.group(2).strip()
        skill_details[e["title"]] = dims

    # 行为证据（STAR 碎片），见 references/tacit-mining-methodology.md
    behavioral_evidence = parse_behavioral_evidence(root)

    return {
        "basic_info": basic,
        "facts": facts,
        "skills": skills,
        "skills_structured": {"通用能力": skills_general, "专属能力": skills_domain},
        "skill_details": skill_details,
        "advantages": advantages,
        "behavioral_evidence": behavioral_evidence,
        "total_years": round(sum(f["years"] for f in facts if f["type"] == "work"), 1),
    }


def post_write(root, action_desc):
    """统一审计链：重生成 facts.yaml → meta.json 版本 +1 → 追加 changelog。
    所有写入路径（kb_interview 各命令、手动编辑后的重建）都必须走这里。"""
    data = build_facts(root)
    common.dump_yaml(data, os.path.join(root, common.DIR_AUTO, "facts.yaml"))

    meta_p = os.path.join(root, common.DIR_AUTO, "meta.json")
    meta = {"version": 0}
    if os.path.exists(meta_p):
        with open(meta_p, encoding="utf-8") as f:
            meta = json.load(f)
    meta["version"] = int(meta.get("version", 0)) + 1
    meta["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(meta_p, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    with open(os.path.join(root, common.DIR_AUTO, "changelog.md"), "a", encoding="utf-8") as f:
        f.write("- %s v%d：%s\n" % (meta["updated_at"], meta["version"], action_desc))
    return data, meta["version"]


def main():
    ap = argparse.ArgumentParser(description="Markdown 原始事实 → facts.yaml（含 meta+1 与 changelog 审计）")
    ap.add_argument("--kb", default=None, help="知识库路径（缺省读 config.yaml）")
    args = ap.parse_args()
    root = common.kb_root(args.kb)

    data, ver = post_write(root, "重建 facts.yaml（手动触发）")
    out = os.path.join(root, common.DIR_AUTO, "facts.yaml")
    print("[完成] facts.yaml 已生成: %s（版本 v%d）" % (out, ver))
    print("  工作 %d 段 / 项目 %d 个 / 技能 %d 条（通用 %d / 专属 %d / 详情 %d 个）/ 优势 %d 条 / 行为证据 %d 条 / 总年限 %.1f 年"
          % (sum(1 for f in data["facts"] if f["type"] == "work"),
             sum(1 for f in data["facts"] if f["type"] == "project"),
             len(data["skills"]), len(data["skills_structured"]["通用能力"]),
             len(data["skills_structured"]["专属能力"]),
             len(data.get("skill_details", {})),
             len(data["advantages"]),
             len(data.get("behavioral_evidence", [])),
             data["total_years"]))


if __name__ == "__main__":
    main()
