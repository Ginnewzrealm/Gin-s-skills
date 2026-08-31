#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_judge_questions.py — 问题判定四关卡测试。

依据：方法论第四步
关卡 1：有明确的信息需求（认知缺口）
关卡 2：有可回答的答案空间（基于事实/数据/共识）
关卡 3：有实际的行动指向（回答后能指导行动）
关卡 4：有真实的足够需求频次（≥2 次跨来源，或 ≥5 次单来源）

判定结果：passed / degraded（频次低）/ rejected
"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("judge_questions", _MODULE_DIR / "judge_questions.py")
jq = importlib.util.module_from_spec(_spec)
sys.modules["judge_questions"] = jq
_spec.loader.exec_module(jq)


def _q(text, freq=5, sources=3):
    return {"text": text, "frequency": freq, "source_count": sources}


def test_gate1_passes_with_info_need():
    q = _q("什么是热量缺口")
    r = jq.judge(q)
    assert r["gate1"] == "passed"


def test_gate1_rejects_pure_emotion():
    q = _q("减脂好难啊")
    r = jq.judge(q)
    assert r["gate1"] == "rejected"
    assert r["status"] == "rejected"


def test_gate1_rejects_vacuous_question():
    q = _q("减脂是什么")
    r = jq.judge(q)
    assert r["gate1"] == "rejected"
    assert r["status"] == "rejected"


def test_gate1_accepts_specific_what_is():
    q = _q("什么是热量缺口")
    r = jq.judge(q)
    assert r["gate1"] == "passed"


def test_gate1_passes_mixed_emotion_with_ask():
    q = _q("减脂好难，我该怎么办")
    r = jq.judge(q)
    assert r["gate1"] == "passed"


def test_gate2_rejects_value_judgment():
    q = _q("减脂到底有没有意义")
    r = jq.judge(q)
    assert r["gate2"] == "rejected"
    assert r["status"] == "rejected"


def test_gate2_passes_researchable_question():
    q = _q("力量训练和有氧训练哪个更适合减脂")
    r = jq.judge(q)
    assert r["gate2"] == "passed"


def test_gate3_rejects_pure_theory():
    q = _q("减脂这个概念最早是谁提出的")
    r = jq.judge(q)
    assert r["gate3"] == "rejected"
    assert r["status"] == "rejected"


def test_gate3_passes_actionable_question():
    q = _q("体脂率降到多少算健康")
    r = jq.judge(q)
    assert r["gate3"] == "passed"


def test_gate4_rejects_single_occurrence_low_freq():
    q = _q("减脂期间能不能喝咖啡", freq=1, sources=1)
    r = jq.judge(q)
    assert r["gate4"] == "rejected"
    assert r["status"] == "rejected"


def test_gate4_degrades_low_quality_single_source():
    q = _q("某个稍微冷门但有内容的问题", freq=2, sources=1)
    r = jq.judge(q)
    assert r["gate4"] == "degraded"


def test_gate4_rejects_single_occurrence():
    q = _q("我有一个独特问题", freq=1, sources=1)
    r = jq.judge(q)
    assert r["gate4"] == "rejected"
    assert r["status"] == "rejected"


def test_gate4_passes_high_frequency():
    q = _q("减脂吃什么好", freq=8, sources=2)
    r = jq.judge(q)
    assert r["gate4"] == "passed"
    assert r["status"] == "passed"


def test_full_pass_through_all_gates():
    q = _q("减脂期间碳水应该吃多少", freq=10, sources=3)
    r = jq.judge(q)
    assert r["status"] == "passed"
    assert r["gate1"] == "passed"
    assert r["gate2"] == "passed"
    assert r["gate3"] == "passed"
    assert r["gate4"] == "passed"