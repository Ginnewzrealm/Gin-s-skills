#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bullet_rewriter.py — 按 X-Y-Z 公式重写简历条目（N9 第⑦步的硬事实层）。

核心变更（v1.18.3）：
- 不再把 rewritten 简单复制为 original，而是按 X-Y-Z / CAR 公式做规则化改写。
- 同一输入始终输出同一 rewritten，消除 Claude 自由润色带来的非确定性。
- 强制中性表达，检测并拦截贬义词 / 负面自我描述。
- 硬事实（数字、公司、职位、时间）原样保留，改写后必须过 provenance_verifier。

X-Y-Z 公式（详见 references/writing-formulas.md）：
  通过 [X：方法/动作]，完成 [Y：任务]，实现 [Z：可量化结果]

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

# 能力小标题候选词（用于从原句提取或兜底）
CAPABILITY_HINTS = {
    "谈判": "商务谈判", "签约": "商务谈判", "合同": "商务谈判", "客户": "商务谈判",
    "渠道": "渠道拓展", "经销商": "渠道拓展", "终端": "渠道拓展", "分销": "渠道拓展",
    "团队": "团队管理", "人员": "团队管理", "培养": "团队管理", "带领": "团队管理",
    "营收": "业绩增长", "销售": "业绩增长", "回款": "业绩增长", "业绩": "业绩增长",
    "流程": "流程优化", "机制": "机制搭建", "系统": "系统搭建", "平台": "系统搭建",
    "项目": "项目管理", "协调": "跨部门协同", "协同": "跨部门协同", "拉通": "跨部门协同",
    "数据": "数据分析", "分析": "数据分析", "指标": "数据分析",
    "用户": "用户增长", "增长": "用户增长", "转化": "用户增长",
}

# 强动词池（按优先级排序，优先匹配前面的词）
ACTION_VERBS = [
    "主导", "负责", "搭建", "设计", "开发", "优化", "重构", "落地",
    "推动", "谈判", "策划", "分析", "带领", "组织", "整合", "协同",
    "建立", "制定", "推进", "完成", "实现", "提升", "降低", "缩短",
]

# 结果提示词（Z 成分的信号）
RESULT_HINTS = [
    "提升", "提高", "增长", "增加", "降低", "减少", "下降", "节省",
    "缩短", "达成", "完成", "实现", "贡献", "超过", "排名", "获得",
    "增至", "降至", "提升至", "降低至",
]

METRIC_PAT = re.compile(r"\d+(?:\.\d+)?%?|\d+[万千百个]|\d{4}[./年]\d{1,2}")

# 贬义词 / 负面自我描述黑名单
DEROGATORY_WORDS = {
    "只是", "仅仅", "不过是", "随便", "凑合", "应付", "疲于应付",
    "救火", "填坑", "背锅", "背黑锅", "背锅侠", "打杂", "跑腿",
    "被动", "消极", "无奈", "无助", "没辙", "束手无策", "无能为力",
    "边缘化", "被忽视", "被排挤", "吃亏", "受气", "委屈", "苦逼",
    "混日子", "摸鱼", "摆烂", "躺平", "得过且过",
}

# 弱化动词：在结果不够硬实时，把这类词替换成强动词
WEAK_VERBS = {
    "参与": "协同", "协助": "支持", "帮忙": "支持",
    "做了": "完成", "搞了": "完成", "弄了": "完成",
}


def _split_clauses(text):
    """按中文标点拆分成子句。"""
    return [c.strip() for c in re.split(r"[，、；。]", text) if c.strip()]


def _extract_capability_tag(text):
    """从文本提取能力小标题，找不到时返回空字符串。"""
    for hint, tag in CAPABILITY_HINTS.items():
        if hint in text:
            return tag
    return ""


def _contains_derogatory(text):
    """检测是否含贬义词或明显负面自我描述。"""
    for w in DEROGATORY_WORDS:
        if w in text:
            return w
    return ""


def _replace_weak_verbs(text):
    """把弱化动词替换为中性/强动词。"""
    for weak, strong in WEAK_VERBS.items():
        text = text.replace(weak, strong)
    return text


def _extract_action(clauses):
    """找含强动词的子句作为 X；返回 (动作子句, 剩余子句)。"""
    for v in ACTION_VERBS:
        for i, c in enumerate(clauses):
            if v in c:
                return c, clauses[:i] + clauses[i + 1:]
    # 兜底：返回第一句
    return (clauses[0], clauses[1:]) if clauses else ("", [])


def _extract_result(clauses):
    """找含数字/百分比/结果提示词的子句作为 Z；返回 (结果子句, 剩余子句)。"""
    # 优先：同时含结果提示词与数字
    for i, c in enumerate(clauses):
        if METRIC_PAT.search(c) and any(h in c for h in RESULT_HINTS):
            return c, clauses[:i] + clauses[i + 1:]
    # 次优：含数字
    for i, c in enumerate(clauses):
        if METRIC_PAT.search(c):
            return c, clauses[:i] + clauses[i + 1:]
    return "", clauses


def _normalize_action(action_text):
    """把动作子句整理成以强动词开头的短动作描述。"""
    action_text = _replace_weak_verbs(action_text)
    # 去掉责任层级标记
    _, action_text = common.extract_responsibility_level(action_text)
    # 若已以强动词开头，直接返回
    for v in ACTION_VERBS:
        if action_text.startswith(v):
            return action_text
    # 若句中含强动词，尝试把它提前
    for v in ACTION_VERBS:
        idx = action_text.find(v)
        if idx >= 0:
            return action_text[idx:]
    return action_text


def _compose(capability, action, task, result):
    """按 X-Y-Z 模板组合，输出确定性文案。"""
    parts = []
    if action:
        parts.append(action)
    if task:
        parts.append("完成" + task)
    if result:
        parts.append("实现" + result)
    body = "，".join(parts)
    if capability:
        return f"{capability}：{body}"
    return body


def annotate(bullet):
    """成分标注（硬事实保全与 X-Y-Z 成分检测）。"""
    hard_facts = sorted(set(re.findall(r"\d+(?:\.\d+)?%?|\d{4}[./年]\d{1,2}|[0-9]+[万千百个家名天周月年]", bullet)))
    has_action = any(v in bullet for v in ACTION_VERBS)
    has_result = bool(hard_facts)
    grey = []
    if not has_result:
        grey.append("缺少可量化结果 Z，建议向用户追问量化数据")
    if not has_action:
        grey.append("未识别强动作动词 X，润色时建议以强动词开头")
    return {"hard_facts": hard_facts, "has_action": has_action,
            "has_result": has_result, "grey_zones": grey}


def rewrite(selected):
    """规则化 X-Y-Z/CAR 改写：从原句拆分动作、任务、结果，按模板重组。
    检测到贬义词时直接返回原文并标注灰区，由 Claude 引导用户修正。"""
    out = []
    for item in selected:
        original = item["bullet"]
        a = annotate(original)

        derogatory = _contains_derogatory(original)
        if derogatory:
            a["grey_zones"].append("检测到贬义词或负面表达「%s」，需用户改为中性描述" % derogatory)
            rewritten = original
        else:
            _, cleaned = common.extract_responsibility_level(original)
            clauses = _split_clauses(cleaned)

            # 先拆结果（Z 最 distinctive：带数字+结果提示词），再拆动作（X）
            result, rest = _extract_result(clauses)
            action, rest = _extract_action(rest)
            task = "、".join(rest) if rest else ""

            capability = _extract_capability_tag(original)
            action = _normalize_action(action)

            rewritten = _compose(capability, action, task, result)
            if not rewritten or rewritten == "：":
                rewritten = original
                a["grey_zones"].append("无法自动拆分为 X-Y-Z 结构，需用户补充")

        out.append({
            "fact_id": item["fact_id"], "org": item["org"], "role": item["role"],
            "period": item["period"], "original": original,
            "rewritten": rewritten,
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
