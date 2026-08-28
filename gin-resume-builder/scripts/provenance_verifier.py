#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""provenance_verifier.py — 溯源校验（N9 第⑧步，简历防编造的最后闸门）。

规则：改写后条目中的硬事实（数字、百分比、公司名、职位、时间段）
必须能在其 fact_id 对应的原始事实中找到。找不到 → 拦截（flag），
由 Claude 引导用户补充事实、修正或删除，不得自动放行。

新增（ASu 优化）：
- 年限一致性检查
- 公司归属检查
- 责任层级匹配检查
- 事实冲突检测

用法:
    python3 provenance_verifier.py --bullets bullets.json [--kb 路径]
退出码:
    0 全部通过
    1 仅警告（可继续）
    2 存在拦截项（必须裁决）
    3 发现事实冲突（两版本矛盾）
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

HARD_FACT_PAT = re.compile(r"\d+(?:\.\d+)?%?|\d{4}[./年]\d{1,2}|[0-9]+[万千百个家名天周月年]")
STRONG_CLAIM_PAT = re.compile(r"主导|负责|0→1|0->1|核心|Owner|owner")


def fact_by_id(facts, fact_id):
    for f in facts["facts"]:
        if f["fact_id"] == fact_id:
            return f
    return None


def fact_source_text(facts, fact_id):
    f = fact_by_id(facts, fact_id)
    if not f:
        return ""
    head = " ".join([f.get("company", ""), f.get("name", ""), f.get("role", ""), f.get("period", "")])
    return head + " " + " ".join(f.get("bullets", []))


def _normalize_period(period):
    """把时间段归一化为可比较字符串：去掉空格、统一分隔符。"""
    if not period:
        return ""
    p = re.sub(r"\s+", "", period)
    p = re.sub(r"[./]", "-", p)
    return p


def period_consistent(bullet_period, fact_period):
    """bullet 的时间段是否与原始事实一致（子串或相等即认为一致）。"""
    b = _normalize_period(bullet_period)
    f = _normalize_period(fact_period)
    if not b or not f:
        return True
    return b in f or f in b or b == f


def has_strong_claim(text):
    return bool(STRONG_CLAIM_PAT.search(text))


def _find_bullet_index(fact, source_fact):
    """根据 source_fact 在 fact['bullets'] 中找对应索引。"""
    if not source_fact or not fact:
        return -1
    src = str(source_fact).strip()
    for idx, b in enumerate(fact.get("bullets", [])):
        if src in b or b in src:
            return idx
    return -1


def _detect_conflicts(bullets):
    """检测同 section_id 下互相矛盾的事实版本。"""
    conflicts = []
    by_section = {}
    for b in bullets:
        sid = b.get("section_id") or b.get("fact_id")
        if not sid:
            continue
        by_section.setdefault(sid, []).append(b)
    for sid, group in by_section.items():
        if len(group) < 2:
            continue
        periods = {b.get("period", "") for b in group if b.get("period")}
        orgs = {b.get("org", "") for b in group if b.get("org")}
        if len(periods) > 1:
            conflicts.append("section_id=%s 存在多个矛盾时间段：%s" % (sid, " / ".join(sorted(periods))))
        if len(orgs) > 1:
            conflicts.append("section_id=%s 存在多个矛盾公司归属：%s" % (sid, " / ".join(sorted(orgs))))
    return conflicts


def verify(bullets, facts):
    results = []
    for b in bullets:
        fact = fact_by_id(facts, b["fact_id"])
        src = fact_source_text(facts, b["fact_id"])
        text = b["rewritten"]
        problems = []
        warnings = []

        # 1. 硬事实溯源
        for tok in set(HARD_FACT_PAT.findall(text)):
            tok = tok.strip()
            if tok and tok not in src:
                problems.append("硬事实「%s」在原始事实 %s 中找不到" % (tok, b["fact_id"]))

        # 2. 名称一致性
        for name in (b.get("org") or "", b.get("role") or ""):
            if name and name in text and name not in src:
                problems.append("名称「%s」与原始事实不一致" % name)

        # 3. 公司归属检查
        if b.get("org") and fact:
            fact_org = fact.get("company") or fact.get("name") or ""
            if fact_org and b["org"] != fact_org and b["org"] not in src:
                problems.append("公司归属错误：%s 的事实来源是 %s" % (b["org"], fact_org))

        # 4. 年限一致性
        if b.get("period") and fact and fact.get("period"):
            if not period_consistent(b["period"], fact["period"]):
                problems.append("年限不一致：bullet 为 %s，原始事实为 %s" % (b["period"], fact["period"]))

        # 5. 责任层级匹配
        if fact and has_strong_claim(text):
            idx = _find_bullet_index(fact, b.get("source_fact"))
            levels = fact.get("responsibility_levels", [])
            level = levels[idx] if 0 <= idx < len(levels) else ""
            if level in ("参与", "", "待确认"):
                problems.append("强主张与责任层级「%s」不匹配" % (level or "未标注"))

        results.append({
            "fact_id": b["fact_id"], "rewritten": text,
            "passed": not problems, "problems": problems, "warnings": warnings,
        })

    conflicts = _detect_conflicts(bullets)
    return results, conflicts


def main():
    ap = argparse.ArgumentParser(description="溯源校验")
    ap.add_argument("--bullets", required=True)
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)
    with open(args.bullets, encoding="utf-8") as f:
        bullets = json.load(f)

    results, conflicts = verify(bullets, facts)
    blocked = [r for r in results if not r["passed"]]
    warned = [r for r in results if r["passed"] and r["warnings"]]

    for r in results:
        icon = "✅" if r["passed"] else "🔴"
        print("  %s [%s] %s" % (icon, r["fact_id"], r["rewritten"]))
        for p in r["problems"]:
            print("      拦截：%s" % p)
        for w in r["warnings"]:
            print("      警告：%s" % w)

    if conflicts:
        print("\n⚠️ 发现事实冲突：")
        for c in conflicts:
            print("    %s" % c)

    print("\n溯源结果：%d 通过 / %d 警告 / %d 拦截 / %d 冲突"
          % (len(results) - len(blocked) - len(warned), len(warned), len(blocked), len(conflicts)))

    if conflicts:
        print("[需处理] 发现事实冲突，请用户裁决后再继续。")
        sys.exit(3)
    if blocked:
        print("[需处理] 请引导用户：补充事实 / 修正条目 / 删除条目，然后重写并复检。")
        sys.exit(2)
    if warned:
        print("[注意] 仅有警告，可继续但建议确认。")
        sys.exit(1)
    print("[通过] 所有溯源校验通过。")


if __name__ == "__main__":
    main()
