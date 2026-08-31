#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_dedupe_questions.py — 问题去重与合并规则测试。

依据：问题定义与澄清方法论（修订版）第三步
三条规则：
1. 语义等价：主体/目标/信息需求都相同 → 合并
2. 泛化合并：一条是另一条的特例 → 合并为通用表述
3. 冲突保留：看似相同但预设不同 → 保留为两条
"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("dedupe_questions", _MODULE_DIR / "dedupe_questions.py")
dq = importlib.util.module_from_spec(_spec)
sys.modules["dedupe_questions"] = dq
_spec.loader.exec_module(dq)


def _raw(items):
    """构造原始问题池：[(原始表述, 来源, 频次)]"""
    return [
        {"raw": r, "source": s, "frequency": f}
        for r, s, f in items
    ]


def test_semantic_equivalence_merges():
    pool = _raw([
        ("减脂吃什么好", "知乎", 1),
        ("减脂期间饮食怎么安排", "百度知道", 1),
    ])
    result = dq.dedupe(pool)
    assert len(result) == 1
    assert "吃" in result[0]["raw"]
    assert result[0]["frequency"] == 2
    assert len(result[0]["merged_from"]) == 2


def test_different_info_need_keeps_separate():
    pool = _raw([
        ("减脂吃什么好", "知乎", 1),
        ("减脂期间运动怎么选", "百度知道", 1),
    ])
    result = dq.dedupe(pool)
    assert len(result) == 2


def test_generalization_merge():
    pool = _raw([
        ("减脂期间早餐吃什么", "知乎", 1),
        ("减脂期间午餐吃什么", "百度知道", 1),
    ])
    result = dq.dedupe(pool)
    assert len(result) == 1
    assert "每餐" in result[0]["raw"] or "三餐" in result[0]["raw"]


def test_conflict_preserved():
    pool = _raw([
        ("断碳饮食能减脂吗", "知乎", 1),
        ("断碳饮食有害吗", "百度知道", 1),
    ])
    result = dq.dedupe(pool)
    assert len(result) == 2


def test_frequency_sum_after_merge():
    pool = _raw([
        ("减脂吃什么好", "知乎", 3),
        ("减脂期间饮食怎么安排", "百度知道", 5),
    ])
    result = dq.dedupe(pool)
    assert result[0]["frequency"] == 8


def test_empty_pool():
    assert dq.dedupe([]) == []