#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fact_selector.py — 基于 JD 关键词与 JD Profile 挑选事实（N9 第⑥步）。

评分：bullet 与 JD 关键词重叠数 ×2 + 含数字成果 +1；转行模式下
可迁移能力词（沟通/管理/项目/分析）额外 +1。
输出 JSON 供 bullet_rewriter 使用，并打印人类可读摘要供用户确认。

用法:
    python3 fact_selector.py --jd jd.txt [--profile 技术] [--career-switch] [--top 8] [--kb 路径]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

TRANSFERABLE = ["沟通", "管理", "项目", "协作", "分析", "谈判", "培训", "协调", "策划", "客户"]


def score_bullet(text, jd_kws, career_switch):
    s = sum(2 for w in jd_kws if w.lower() in text.lower())
    if re.search(r"\d+(\.\d+)?%?|[0-9]+[万千百个家名天周月年]", text):
        s += 1  # 量化成果
    if career_switch and any(t in text for t in TRANSFERABLE):
        s += 1
    return s


def select(facts, jd_text, top=8, career_switch=False):
    jd_kws = common.extract_jd_keywords(jd_text)
    cands = []
    for f in facts["facts"]:
        head = f.get("company") or f.get("name") or ""
        for b in f["bullets"]:
            cands.append({
                "fact_id": f["fact_id"], "type": f["type"],
                "org": head, "role": f.get("role", ""), "period": f.get("period", ""),
                "bullet": b, "score": score_bullet(b, jd_kws, career_switch),
            })
    cands.sort(key=lambda x: -x["score"])
    return cands[:top]


def main():
    ap = argparse.ArgumentParser(description="事实挑选")
    ap.add_argument("--jd", required=True)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--career-switch", action="store_true")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--json-out", default=None, help="选中事实 JSON 输出路径")
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()

    picked = select(facts, jd_text, args.top, args.career_switch)
    print("选中事实（%d 条，转行模式=%s）：" % (len(picked), args.career_switch))
    for p in picked:
        print("  [%s|%d分] %s · %s\n      %s" % (p["fact_id"], p["score"], p["org"], p["role"], p["bullet"]))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(picked, f, ensure_ascii=False, indent=2)
        print("[完成] JSON 已写入: %s" % args.json_out)


if __name__ == "__main__":
    main()
