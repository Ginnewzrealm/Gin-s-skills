#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""executive_resume_renderer.py — 高管简历骨架与渲染（N13）。

从知识库提炼量化成就（按数字成果排序取 4-6 条），组装高管结构：
Executive Profile / Core Competencies / Career Highlights /
Professional Experience / Board & Advisory / Education。
脚本产出 resume.json 骨架 + HTML；Profile 与 Board 段落由 Claude 与用户补全。

用法:
    python3 executive_resume_renderer.py [--jd jd.txt] [--kb 路径]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import html_renderer

NUM_PAT = re.compile(r"\d+(\.\d+)?%|\d+[万千百]")


def pick_highlights(facts, top=6):
    cands = []
    for f in facts["facts"]:
        org = f.get("company") or f.get("name") or ""
        for b in f["bullets"]:
            nums = len(NUM_PAT.findall(b))
            if nums:
                cands.append((nums, "[%s] %s：%s" % (f["fact_id"], org, b)))
    cands.sort(key=lambda x: -x[0])
    return [c[1] for c in cands[:top]]


def display_skill(s):
    """KB 技能条目 → 简历展示文本：剥离内部验证元数据。
    通用能力去（证据：…），两类都去 ｜佐证/｜场景 后缀（证据链属于知识库，不上简历）。"""
    s = re.sub(r"｜(佐证|场景)：.*$", "", s)
    s = re.sub(r"（证据：[^）]*）", "", s)
    return s.strip()


def build_resume_json(facts, highlights):
    basic = dict(facts["basic_info"])
    works = [f for f in facts["facts"] if f["type"] == "work"]
    return {
        "title": "%s-高管简历" % basic.get("姓名", ""),
        "basic": basic,
        "sections": [
            {"title": "Executive Profile", "items": ["（待 Claude 撰写：3-4 句高管定位，突出管理半径、业务体量、核心战绩）"]},
            {"title": "Core Competencies", "items": [display_skill(s) for s in facts["skills"][:10]]},
            {"title": "Career Highlights", "items": highlights},
            {"title": "Professional Experience", "entries": [
                {"org": w.get("company"), "role": w.get("role"), "period": w.get("period"),
                 "bullets": w["bullets"]} for w in works]},
            {"title": "Board & Advisory", "items": ["（如无董事会/顾问经历，请用户确认后删除本段）"]},
            {"title": "Education", "items": [basic.get("教育背景", "（待补充）")]},
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="高管简历生成")
    ap.add_argument("--jd", default=None)
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)

    highlights = pick_highlights(facts)
    resume = build_resume_json(facts, highlights)
    html_text = html_renderer.render(resume)
    out = common.out_path(root, "executive_resumes", "高管简历-%s-%s.html" % (facts["basic_info"].get("姓名", ""), common.stamp()))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("[完成] 高管简历骨架已渲染: %s" % out)
    print("[待办] 请 Claude 补全 Executive Profile 段落，并与用户确认 Board & Advisory 是否保留。")


if __name__ == "__main__":
    main()
