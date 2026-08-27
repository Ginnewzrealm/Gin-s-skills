#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""star_story_generator.py — 从知识库提取 STAR 面试故事骨架（N11）。

按关键词把事实条目归入五类故事：领导力 / 解决问题 / 协作 / 成就 / 失败成长。
脚本产出 STAR 四段式骨架（S/T 从事实提取，A/R 留槽位由 Claude 与用户补全），
落盘到 面试素材/star_stories.md（持久资产，N12 依赖其存在性）。
故事指南见 references/star-story-bank.md。

用法:
    python3 star_story_generator.py [--kb 路径]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

CATEGORIES = {
    "领导力": ["带领", "管理", "负责团队", "组建", "搭建团队", "指导", "带人"],
    "解决问题": ["解决", "排查", "修复", "优化", "重构", "攻坚", "难题", "瓶颈"],
    "协作": ["协作", "跨部门", "配合", "联合", "协调", "对接"],
    "成就": ["提升", "增长", "第一", "获奖", "突破", "达成", "超额", "%"],
    "失败成长": ["失败", "教训", "复盘", "踩坑", "返工", "延期"],
}


def categorize(facts):
    stories = {k: [] for k in CATEGORIES}
    for f in facts["facts"]:
        org = f.get("company") or f.get("name") or ""
        for b in f["bullets"]:
            for cat, kws in CATEGORIES.items():
                if any(k in b for k in kws):
                    stories[cat].append({"fact_id": f["fact_id"], "org": org,
                                         "role": f.get("role", ""), "period": f.get("period", ""),
                                         "bullet": b})
                    break
    return stories


def render(facts, stories):
    L = ["# STAR 面试故事库", "",
         "> 生成自知识库原始事实。每故事含完整版骨架 / 精简版 / 一句话版；",
         "> A（行动）与 R（结果）细节由 Claude 与用户对话补全后定稿。", ""]
    for cat, items in stories.items():
        L.append("## %s（%d 个素材）" % (cat, len(items)))
        for it in items:
            L.append("### 素材 [%s] %s · %s（%s）" % (it["fact_id"], it["org"], it["role"], it["period"]))
            L.append("- 原始事实：%s" % it["bullet"])
            L.append("- **S 情境**：%s 期间，在 %s 背景下（待补：业务背景/团队规模）" % (it["period"], it["org"]))
            L.append("- **T 任务**：%s" % it["bullet"][:60])
            L.append("- **A 行动**：（待补：你具体做了什么，分 2-3 步）")
            L.append("- **R 结果**：（待补：量化结果，须与原始事实一致）")
            L.append("- 精简版：（待 Claude 压缩为 3-4 句）")
            L.append("- 一句话版：（待 Claude 压缩为 1 句）")
            L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="STAR 故事库生成")
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)
    stories = categorize(facts)
    md = render(facts, stories)
    out = os.path.join(root, common.DIR_INTERVIEW, "star_stories.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    total = sum(len(v) for v in stories.values())
    print("[完成] STAR 故事库已生成: %s（素材 %d 条，分类 %d/%d 非空）"
          % (out, total, sum(1 for v in stories.values() if v), len(CATEGORIES)))


if __name__ == "__main__":
    main()
