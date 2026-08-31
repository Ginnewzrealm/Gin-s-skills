#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rank_questions.py — 问题分层与优先级排序（方法论第六步）。

三维坐标 → 量化评分 → 分档：
- 知识深度 L1/L2/L3
- 需求强度 H/M/L（来自 judge.gate4）
- 覆盖面（适用人群细分数）

评分公式：频次×40% + 深度×30% + 覆盖面×30%
档位：P0 ≥ 7 / P1 4-6 / P2 < 4
"""
import re


DEPTH_WEIGHT = {"L1": 10, "L2": 7, "L3": 4}
DEMAND_SCORE = {"passed": 10, "degraded": 5, "rare": 2}

DEPTH_LABEL = {
    "L1": "L1 认知层（是什么）",
    "L2": "L2 方法层（怎么做）",
    "L3": "L3 判断层（怎么选）",
}


def detect_depth(text):
    """从问题文本检测知识深度层级。"""
    # L1：是什么 / 为什么
    if re.search(r"什么是|什么叫|为什么|定义", text):
        return "L1"
    # L3：比较 / 选择
    if re.search(r"哪个|更好|还是|哪个更|比较|vs|选哪个|该不该|要不要", text):
        return "L3"
    # L2：怎么做 / 多少 / 步骤
    if re.search(r"怎么|如何|多少|几个|多久|步骤|方法|流程|怎么办|怎么选|怎么练|怎么吃|怎么喝", text):
        return "L2"
    # 含数字求答视作 L2
    if re.search(r"\d+", text) and re.search(r"几|多少|多久|几个", text):
        return "L2"
    # 默认 L1（询问概念）
    return "L1"


def demand_score(gate4_status):
    """需求强度分数。"""
    return DEMAND_SCORE.get(gate4_status, 5)


def coverage_score(audience_count):
    """覆盖面分数。"""
    if audience_count >= 3:
        return 10
    if audience_count >= 2:
        return 5
    return 2


def compute_priority(question):
    """计算单条问题的优先级分数与档位。"""
    depth = question.get("depth") or detect_depth(question["text"])
    freq_score = demand_score(question.get("gate4", "passed"))
    depth_score = DEPTH_WEIGHT[depth]
    cov_score = coverage_score(question.get("audience_count", 1))
    score = freq_score * 0.4 + depth_score * 0.3 + cov_score * 0.3
    score = round(score, 2)
    if score >= 7:
        tier = "P0"
    elif score >= 4:
        tier = "P1"
    else:
        tier = "P2"
    return {
        "text": question["text"],
        "depth": depth,
        "depth_label": DEPTH_LABEL[depth],
        "demand": question.get("gate4", "passed"),
        "audience_count": question.get("audience_count", 1),
        "score": score,
        "tier": tier,
    }


def rank(questions):
    """批量排序：按 score 降序。"""
    ranked = [compute_priority(q) for q in questions]
    ranked.sort(key=lambda x: -x["score"])
    return ranked


if __name__ == "__main__":
    import sys, json
    data = json.load(sys.stdin)
    print(json.dumps(rank(data), ensure_ascii=False, indent=2))