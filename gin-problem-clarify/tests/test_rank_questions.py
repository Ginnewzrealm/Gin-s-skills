#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_rank_questions.py — 问题分层与优先级排序测试。

依据：方法论第六步
三维坐标：
- 知识深度：L1 认知层（是什么）/ L2 方法层（怎么做）/ L3 判断层（怎么选）
- 需求强度：H 高频 / M 中频 / L 低频（来自 gate4 输出）
- 覆盖面：覆盖人群细分数

优先级分数 = 需求频次得分 × 40% + 知识深度权重 × 30% + 覆盖面得分 × 30%
- 频次得分：H=10, M=5, L=2
- 深度权重：L1=10, L2=7, L3=4
- 覆盖面得分：≥3 人群=10, 1-2 人群=5, 1 极细分=2

档位：P0 ≥ 7 分 / P1 4-6 / P2 < 4
"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("rank_questions", _MODULE_DIR / "rank_questions.py")
rq = importlib.util.module_from_spec(_spec)
sys.modules["rank_questions"] = rq
_spec.loader.exec_module(rq)


def _q(text, gate4="passed", depth="L2", coverage=3, audience_count=3):
    return {"text": text, "gate4": gate4, "depth": depth,
            "coverage": coverage, "audience_count": audience_count}


def test_detect_depth_l1_what_is():
    assert rq.detect_depth("什么是热量缺口") == "L1"


def test_detect_depth_l2_how_to():
    assert rq.detect_depth("每天应该做多少分钟有氧") == "L2"


def test_detect_depth_l3_compare():
    assert rq.detect_depth("力量训练和有氧训练哪个更好") == "L3"


def test_demand_score_H():
    assert rq.demand_score("passed") == 10


def test_demand_score_M():
    assert rq.demand_score("degraded") == 5


def test_demand_score_L():
    assert rq.demand_score("rare") == 2


def test_coverage_score():
    assert rq.coverage_score(5) == 10
    assert rq.coverage_score(2) == 5
    assert rq.coverage_score(1) == 2


def test_compute_priority_p0():
    q = _q("减脂吃什么好", gate4="passed", depth="L2", audience_count=5)
    p = rq.compute_priority(q)
    assert p["score"] >= 7
    assert p["tier"] == "P0"


def test_compute_priority_p2():
    q = _q("极冷门问题", gate4="rare", depth="L3", audience_count=1)
    p = rq.compute_priority(q)
    assert p["score"] < 4
    assert p["tier"] == "P2"


def test_rank_sorts_by_score_desc():
    qs = [
        _q("极冷门", gate4="rare", depth="L3", audience_count=1),
        _q("基础必问", gate4="passed", depth="L1", audience_count=5),
        _q("方法类", gate4="passed", depth="L2", audience_count=3),
    ]
    ranked = rq.rank(qs)
    assert ranked[0]["text"] == "基础必问"
    assert ranked[-1]["text"] == "极冷门"


def test_rank_includes_tier_and_score():
    qs = [_q("Q1", gate4="passed", depth="L2", audience_count=3)]
    ranked = rq.rank(qs)
    assert "tier" in ranked[0]
    assert "score" in ranked[0]
    assert "depth_label" in ranked[0]