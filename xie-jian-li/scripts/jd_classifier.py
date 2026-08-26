#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_classifier.py — JD Profile 分类：技术 / 销售 / 运营 / 产品 / 管理。

输出 JSON：{"profile": "...", "scores": {...}, "career_switch_hint": true/false}
career_switch_hint：JD 画像与知识库最近一段工作经历画像不一致时为 true（转行模式提示）。

用法:
    python3 jd_classifier.py --jd jd.txt [--kb 路径]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PROFILE_KEYWORDS = {
    "技术": ["开发", "工程师", "算法", "架构", "后端", "前端", "测试", "运维", "数据开发",
             "Python", "Java", "Go", "Redis", "Kafka", "微服务", "分布式", "高并发", "代码"],
    "销售": ["销售", "BD", "商务", "客户开发", "渠道", "业绩", "签单", "回款", "KA",
             "大客户", "代理商", "招商", "电销"],
    "运营": ["运营", "增长", "活动", "内容", "用户留存", "私域", "社群", "策划",
             "拉新", "转化", "编辑", "新媒体"],
    "产品": ["产品经理", "需求", "PRD", "原型", "用户研究", "竞品", "迭代", " roadmap",
             "功能设计", "用户体验", "Axure"],
    "管理": ["总监", "VP", "负责人", "团队管理", "搭建团队", "战略", "预算", "OKR",
             "部门", "管理者", "总经理", "CEO", "CTO", "COO"],
}


def classify_text(text):
    scores = {}
    for profile, kws in PROFILE_KEYWORDS.items():
        scores[profile] = sum(text.count(k) for k in kws)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "通用"
    return best, scores


def main():
    ap = argparse.ArgumentParser(description="JD Profile 分类")
    ap.add_argument("--jd", required=True)
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()

    profile, scores = classify_text(jd_text)
    result = {"profile": profile, "scores": scores, "career_switch_hint": False}

    if args.kb or os.path.exists(common.CONFIG_PATH):
        try:
            root = common.kb_root(args.kb)
            facts = common.load_facts(root)
            works = [f for f in facts["facts"] if f["type"] == "work"]
            if works:
                last = works[-1]
                kb_profile, _ = classify_text(last.get("company", "") + " " + last.get("role", "") + " " + " ".join(last["bullets"]))
                if kb_profile != "通用" and profile != "通用" and kb_profile != profile:
                    result["career_switch_hint"] = True
                    result["kb_profile"] = kb_profile
        except SystemExit:
            pass

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
