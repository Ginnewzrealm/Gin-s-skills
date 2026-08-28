#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_strong_claim_auditor.py — 强主张审计测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("strong_claim_auditor", _MODULE_DIR / "strong_claim_auditor.py")
auditor = importlib.util.module_from_spec(_spec)
sys.modules["strong_claim_auditor"] = auditor
_spec.loader.exec_module(auditor)

audit = auditor.audit


def test_pass_when_strong_claim_has_action_and_result():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地，回款周期缩短 30%",
        "responsibility_level": "主导方案或交付",
    }]
    reports = audit(bullets)
    assert reports[0]["passed"]


def test_fail_when_participation_uses_strong_verb():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "responsibility_level": "参与",
    }]
    reports = audit(bullets)
    assert not reports[0]["passed"]
    assert any("参与" in i for i in reports[0]["issues"])


def test_fail_when_missing_result():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导客户沟通与需求对接",
        "responsibility_level": "主导方案或交付",
    }]
    reports = audit(bullets)
    assert not reports[0]["passed"]
    assert any("结果" in i for i in reports[0]["issues"])


def test_no_report_when_no_strong_verb():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "参与客户沟通会议，记录会议纪要",
        "responsibility_level": "参与",
    }]
    reports = audit(bullets)
    assert reports == []


def test_recommendation_for_high_level():
    bullets = [{
        "fact_id": "W1",
        "rewritten": "主导客户沟通",
        "responsibility_level": "主导方案或交付",
    }]
    reports = audit(bullets)
    assert not reports[0]["passed"]
    assert "待确认" in reports[0]["recommendation"]
