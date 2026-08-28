#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""material_inventory.py — 材料盘点最小化补问（简历管线前置环节）。

自动扫描知识库已有内容，按对交付的影响排序，只输出最关键的 3 个补问问题。

用法:
    python3 material_inventory.py [--kb 路径] [--out gaps.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def inventory(root, facts):
    """返回 (优先级, 问题) 列表，按影响从高到低排序。"""
    gaps = []
    basic = facts.get("basic_info", {})

    if not basic.get("求职意向"):
        gaps.append(("high", "请补充求职意向（目标岗位名称），这是匹配 JD 和选择经历的前提。"))

    if not basic.get("姓名"):
        gaps.append(("high", "请补充姓名。"))

    work_facts = [f for f in facts.get("facts", []) if f.get("type") == "work"]
    project_facts = [f for f in facts.get("facts", []) if f.get("type") == "project"]

    if not work_facts:
        gaps.append(("high", "工作经历为空。请至少补充 1-2 段与目标岗位相关的工作经历，否则无法生成简历。"))
    else:
        for f in work_facts:
            org = f.get("company") or f.get("name") or f.get("fact_id", "")
            bullets = f.get("bullets", [])
            if not bullets:
                gaps.append(("high", "【%s】缺少关键业绩 bullet，请补充 3-5 条能体现能力的事实。" % org))
                continue
            if len(bullets) < 3:
                gaps.append(("medium", "【%s】关键业绩 bullet 数量偏少（%d 条），建议补充到 3-5 条以增强说服力。" % (org, len(bullets))))

            levels = f.get("responsibility_levels", [])
            if any(l in ("", "待确认") for l in levels):
                gaps.append(("medium", "【%s】部分 bullet 未标注责任层级（参与/负责模块/主导方案或交付/项目负责人），建议补充以便溯源校验。" % org))

            has_metric = any(common.METRIC_RE.search(b) for b in bullets)
            if not has_metric:
                gaps.append(("medium", "【%s】工作经历中缺少量化数字（如 %%、万、年、倍等），建议补充可验证的业绩数据。" % org))

    if not facts.get("skills"):
        gaps.append(("high", "技能清单为空。请补充与目标岗位相关的技能，否则 ATS 关键词匹配不足。"))

    if not project_facts:
        gaps.append(("low", "项目经历为空。若目标岗位看重项目经验，建议补充 1-2 个代表性项目。"))

    # 按优先级排序
    order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: order[x[0]])
    return gaps[:3]


def main():
    ap = argparse.ArgumentParser(description="材料盘点")
    ap.add_argument("--kb", default=None, help="知识库路径")
    ap.add_argument("--out", default=None, help="输出 JSON 文件路径（可选）")
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)

    gaps = inventory(root, facts)

    if not gaps:
        print("材料盘点：知识库关键信息充足，可直接进入简历管线。")
        items = []
    else:
        print("材料盘点：发现以下 %d 个最需要优先补问的问题（已按影响排序）：\n" % len(gaps))
        items = []
        for i, (level, question) in enumerate(gaps, 1):
            label = {"high": "高", "medium": "中", "low": "低"}[level]
            line = "%d. 【%s】%s" % (i, label, question)
            print(line)
            items.append({"priority": level, "priority_label": label, "question": question})

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print("\n[完成] 盘点结果已保存: %s" % args.out)


if __name__ == "__main__":
    main()
