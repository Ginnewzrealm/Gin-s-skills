#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""strong_claim_auditor.py — 强主张审计节点（N9 管线第⑥步）。

扫描待写入 bullet，对包含「主导 / 负责 / 0→1 / 核心 / Owner」等强动词的条目
验证是否能说明：
1. 个人具体做了什么决策/动作
2. 结果中的数字口径或定性可核验结果

无法通过 → 建议降级为「参与」或标注【待确认】。

用法:
    python3 strong_claim_auditor.py --bullets bullets.json [--out audit.json]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

STRONG_VERBS = re.compile(r"主导|负责|0→1|0->1|核心|Owner|owner")
# 可视为具体动作/决策的动词/名词
ACTION_MARKERS = re.compile(
    r"决策|设计|搭建|重构|优化|推动|谈判|落地|落地|交付|带队|带领|统筹|"
    r"策划|执行|实施|完成|实现|建立|制定|拆解|攻坚|突破|闭环"
)
# 量化或定性可核验结果标志
RESULT_MARKERS = re.compile(
    r"\d+(?:\.\d+)?\s?(?:%|万|亿|元|ms|QPS|TPS|家|个|人|天|月|年|倍)|"
    r"完成|达成|通过|上线|落地|交付|签约|回款|晋升|增长|提升|降低|缩短"
)


def _has_specific_action(text):
    return bool(ACTION_MARKERS.search(text))


def _has_result(text):
    return bool(RESULT_MARKERS.search(text))


def audit(bullets):
    """审计 bullets，返回报告列表。"""
    reports = []
    for b in bullets:
        text = b.get("rewritten", "")
        if not STRONG_VERBS.search(text):
            continue
        level = b.get("responsibility_level", "")
        issues = []
        if level == "参与":
            issues.append("责任层级为「参与」，不应使用强动词")
        if not _has_specific_action(text):
            issues.append("未说明个人具体决策/动作")
        if not _has_result(text):
            issues.append("未提供可核验的结果（数字或定性成果）")

        if issues:
            recommendation = "降级为「参与」"
            if level in ("负责模块", "主导方案或交付", "项目负责人"):
                recommendation = "标注【待确认】并补充决策/结果细节"
            reports.append({
                "fact_id": b.get("fact_id", ""),
                "rewritten": text,
                "responsibility_level": level,
                "issues": issues,
                "recommendation": recommendation,
                "passed": False,
            })
        else:
            reports.append({
                "fact_id": b.get("fact_id", ""),
                "rewritten": text,
                "responsibility_level": level,
                "issues": [],
                "recommendation": "通过",
                "passed": True,
            })
    return reports


def main():
    ap = argparse.ArgumentParser(description="强主张审计")
    ap.add_argument("--bullets", required=True, help="待审计 bullets JSON")
    ap.add_argument("--out", default=None, help="审计报告输出路径")
    args = ap.parse_args()

    with open(args.bullets, encoding="utf-8") as f:
        bullets = json.load(f)

    reports = audit(bullets)
    failed = [r for r in reports if not r["passed"]]

    for r in reports:
        icon = "✅" if r["passed"] else "🔴"
        print("  %s [%s] %s" % (icon, r["fact_id"], r["rewritten"]))
        for issue in r["issues"]:
            print("      问题：%s" % issue)
        print("      建议：%s" % r["recommendation"])

    print("\n强主张审计：%d 通过 / %d 需处理" % (len(reports) - len(failed), len(failed)))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        print("[完成] 审计报告已保存: %s" % args.out)

    if failed:
        sys.exit(4)


if __name__ == "__main__":
    main()
