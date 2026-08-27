#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""provenance_verifier.py — 溯源校验（N9 第⑧步，简历防编造的最后闸门）。

规则：改写后条目中的硬事实（数字、百分比、公司名、职位、时间段）
必须能在其 fact_id 对应的原始事实中找到。找不到 → 拦截（flag），
由 Claude 引导用户补充事实、修正或删除，不得自动放行。

用法:
    python3 provenance_verifier.py --bullets bullets.json [--kb 路径]
退出码: 0 全部通过 / 2 存在拦截项
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

HARD_FACT_PAT = re.compile(r"\d+(\.\d+)?%?|\d{4}[./年]\d{1,2}|[0-9]+[万千百个家名天周月年]")


def fact_source_text(facts, fact_id):
    for f in facts["facts"]:
        if f["fact_id"] == fact_id:
            head = " ".join([f.get("company", ""), f.get("name", ""), f.get("role", ""), f.get("period", "")])
            return head + " " + " ".join(f["bullets"])
    return ""


def verify(bullets, facts):
    results = []
    for b in bullets:
        src = fact_source_text(facts, b["fact_id"])
        text = b["rewritten"]
        problems = []
        for tok in set(HARD_FACT_PAT.findall(text)):
            tok = tok.strip()
            if tok and tok not in src:
                problems.append("硬事实「%s」在原始事实 %s 中找不到" % (tok, b["fact_id"]))
        for name in (b.get("org") or "", b.get("role") or ""):
            if name and name in text and name not in src:
                problems.append("名称「%s」与原始事实不一致" % name)
        results.append({
            "fact_id": b["fact_id"], "rewritten": text,
            "passed": not problems, "problems": problems,
        })
    return results


def main():
    ap = argparse.ArgumentParser(description="溯源校验")
    ap.add_argument("--bullets", required=True)
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)
    with open(args.bullets, encoding="utf-8") as f:
        bullets = json.load(f)

    results = verify(bullets, facts)
    blocked = [r for r in results if not r["passed"]]
    for r in results:
        print(("  ✅ [%s] %s" if r["passed"] else "  🔴 [%s] %s") % (r["fact_id"], r["rewritten"]))
        for p in r["problems"]:
            print("      拦截：%s" % p)
    print("溯源结果：%d 通过 / %d 拦截" % (len(results) - len(blocked), len(blocked)))
    if blocked:
        print("[需处理] 请引导用户：补充事实 / 修正条目 / 删除条目，然后重写并复检。")
        sys.exit(2)


if __name__ == "__main__":
    main()
