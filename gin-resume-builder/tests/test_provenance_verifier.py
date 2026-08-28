#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_provenance_verifier.py — 溯源校验测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("provenance_verifier", _MODULE_DIR / "provenance_verifier.py")
prov = importlib.util.module_from_spec(_spec)
sys.modules["provenance_verifier"] = prov
_spec.loader.exec_module(prov)

verify = prov.verify


def _facts():
    return {
        "facts": [
            {
                "fact_id": "W1",
                "type": "work",
                "company": "绿城科技",
                "role": "大客户经理",
                "period": "2020.12-2025.06",
                "bullets": [
                    "**[主导]** 丽水560万合同商务谈判，签约落地",
                    "**[参与]** 省发改委对接会议，介绍绿城经验",
                ],
                "responsibility_levels": ["主导方案或交付", "参与"],
            },
            {
                "fact_id": "W2",
                "type": "work",
                "company": "鼎鹏",
                "role": "销售总监",
                "period": "2016.06-2020.11",
                "bullets": ["负责政府项目资源整合，12年总经验"],
                "responsibility_levels": ["主导方案或交付"],
            },
        ]
    }


def test_pass_when_facts_match():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "org": "绿城科技",
        "role": "大客户经理",
        "period": "2020.12-2025.06",
        "source_fact": "丽水560万合同商务谈判，签约落地",
    }]
    results, conflicts = verify(bullets, _facts())
    assert results[0]["passed"]
    assert not conflicts


def test_block_when_hard_fact_missing():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地，覆盖客户1000家",
        "org": "绿城科技",
        "role": "大客户经理",
        "period": "2020.12-2025.06",
        "source_fact": "丽水560万合同商务谈判，签约落地",
    }]
    results, conflicts = verify(bullets, _facts())
    assert not results[0]["passed"]
    assert any("1000" in p for p in results[0]["problems"])


def test_block_when_org_mismatch():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "org": "鼎鹏",
        "role": "大客户经理",
        "period": "2020.12-2025.06",
        "source_fact": "丽水560万合同商务谈判，签约落地",
    }]
    results, conflicts = verify(bullets, _facts())
    assert not results[0]["passed"]
    assert any("归属" in p for p in results[0]["problems"])


def test_block_when_period_mismatch():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "org": "绿城科技",
        "role": "大客户经理",
        "period": "2016.06-2020.11",
        "source_fact": "丽水560万合同商务谈判，签约落地",
    }]
    results, conflicts = verify(bullets, _facts())
    assert not results[0]["passed"]
    assert any("年限" in p for p in results[0]["problems"])


def test_block_when_strong_claim_with_participation_level():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导省发改委对接会议并介绍绿城经验",
        "org": "绿城科技",
        "role": "大客户经理",
        "period": "2020.12-2025.06",
        "source_fact": "省发改委对接会议，介绍绿城经验",
    }]
    results, conflicts = verify(bullets, _facts())
    assert not results[0]["passed"]
    assert any("责任层级" in p for p in results[0]["problems"])


def test_conflict_when_same_section_id_different_periods():
    bullets = [
        {
            "fact_id": "W1",
            "section_id": "绿城科技-2020.12",
            "rewritten": "主导丽水560万合同商务谈判并签约落地",
            "org": "绿城科技",
            "period": "2020.12-2025.06",
        },
        {
            "fact_id": "W2",
            "section_id": "绿城科技-2020.12",
            "rewritten": "负责政府项目资源整合",
            "org": "绿城科技",
            "period": "2016.06-2020.11",
        },
    ]
    results, conflicts = verify(bullets, _facts())
    assert len(conflicts) > 0
    assert any("2020.12-2025.06" in c and "2016.06-2020.11" in c for c in conflicts)


def test_exit_code_helper():
    """验证结果结构包含 expected 字段，便于调用方判断退出码。"""
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "org": "绿城科技",
        "role": "大客户经理",
        "period": "2020.12-2025.06",
        "source_fact": "丽水560万合同商务谈判，签约落地",
    }]
    results, conflicts = verify(bullets, _facts())
    assert "passed" in results[0]
    assert "problems" in results[0]
    assert "warnings" in results[0]
    assert not conflicts
