#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bullet_rewriter.py — 按 X-Y-Z 公式重写简历条目（N9 第⑦步的硬事实层）。

三层控制（Q4 已确认）：
- 硬事实层（本脚本）：数字/角色/时间/公司名原样保留，只做结构化重排，不改写事实
- 表达润色层：由 Claude 在脚本输出基础上润色（本脚本不做）
- 灰区：无法从原句拆出 X/Y/Z 成分时标注 {?}，交给用户确认

X-Y-Z 公式（详见 references/writing-formulas.md）：
  通过 [X：方法/动作]，完成 [Y：任务/职责]，实现 [Z：可量化结果]

用法:
    python3 bullet_rewriter.py --selected picked.json [--kb 路径] [--out bullets.json]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

RESULT_HINT = re.compile(r"提升|提高|增长|降低|减少|节省|达成|完成|实现|带来|贡献|超过|排名|获得|\d+(\.\d+)?%|\d+[万千百]")
ACTION_VERBS = ["负责", "主导", "搭建", "设计", "开发", "优化", "推动", "落地", "运营", "管理", "谈判", "策划", "分析", "重构", "带领", "组织"]


def annotate(bullet):
    """成分标注（脚本不改写句子，只做硬事实保全与 X-Y-Z 成分检测）。
    句子级重写由 Claude 润色层按 references/writing-formulas.md 完成。"""
    hard_facts = sorted(set(re.findall(r"\d+(?:\.\d+)?%?|\d{4}[./年]\d{1,2}|[0-9]+[万千百个家名天周月年]", bullet)))
    has_action = any(v in bullet for v in ACTION_VERBS)
    has_result = bool(hard_facts)  # 含数字即视为已量化（百分比/规模/次数均可）
    grey = []
    if not has_result:
        grey.append("缺少可量化结果 Z，建议向用户追问量化数据")
    if not has_action:
        grey.append("未识别强动作动词 X，润色时建议以强动词开头")
    return {"hard_facts": hard_facts, "has_action": has_action,
            "has_result": has_result, "grey_zones": grey}


def rewrite(selected):
    """硬事实层：base 原样保留（数字/角色/时间不可变），附成分标注。
    Claude 润色层在 base 上重写 rewritten，改写后必须过 provenance_verifier。"""
    out = []
    for item in selected:
        a = annotate(item["bullet"])
        out.append({
            "fact_id": item["fact_id"], "org": item["org"], "role": item["role"],
            "period": item["period"], "original": item["bullet"],
            "rewritten": item["bullet"],  # 润色层替换此字段；未润色时与原句一致
            "hard_facts": a["hard_facts"],
            "has_action": a["has_action"], "has_result": a["has_result"],
            "grey_zones": a["grey_zones"],
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="X-Y-Z 条目改写（硬事实层）")
    ap.add_argument("--selected", required=True, help="fact_selector 输出的 JSON")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.selected, encoding="utf-8") as f:
        selected = json.load(f)

    bullets = rewrite(selected)
    for b in bullets:
        mark = " {?}" if b["grey_zones"] else ""
        print("  [%s]%s %s" % (b["fact_id"], mark, b["rewritten"]))
        for g in b["grey_zones"]:
            print("      灰区：%s" % g)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(bullets, f, ensure_ascii=False, indent=2)
        print("[完成] 已写入: %s" % args.out)


if __name__ == "__main__":
    main()
