#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_claim_binder.py — 主张绑定测试。"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("common", _MODULE_DIR / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)

_spec2 = importlib.util.spec_from_file_location("claim_binder", _MODULE_DIR / "claim_binder.py")
binder = importlib.util.module_from_spec(_spec2)
sys.modules["claim_binder"] = binder
_spec2.loader.exec_module(binder)

bind_claims = binder.bind_claims
write_claims = common.write_claims
read_claims = common.read_claims


def _facts():
    return {
        "facts": [
            {
                "fact_id": "W1",
                "type": "work",
                "company": "绿城科技",
                "role": "大客户经理",
                "period": "2020.12-2025.06",
                "bullets": ["**[主导]** 丽水560万合同商务谈判，签约落地"],
                "responsibility_levels": ["主导方案或交付"],
            }
        ]
    }


def test_bind_claims_generates_required_fields():
    bullets = [{
        "fact_id": "W1",
        "source_fact": "丽水560万合同商务谈判，签约落地",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
        "responsibility_level": "主导方案或交付",
    }]
    claims = bind_claims(bullets, _facts())
    assert len(claims) == 1
    c = claims[0]
    for f in common.CLAIM_FIELDS:
        assert f in c, "缺少字段 %s" % f
    assert c["section"] == "work_history"
    assert c["section_id"].startswith("绿城科技")
    assert c["responsibility_level"] == "主导方案或交付"
    assert c["verification_status"] == "已确认"


def test_bind_claims_uses_user_inputs():
    bullets = [{
        "fact_id": "W1",
        "source_fact": "丽水560万合同商务谈判，签约落地",
        "rewritten": "主导丽水560万合同商务谈判并签约落地",
    }]
    claim_id = "claim-20260828-001"
    bullets[0]["claim_id"] = claim_id
    inputs = {
        claim_id: {
            "boundary": "个人负责谈判与条款，交付由团队完成",
            "interview_details": {
                "decision": "直接谈判",
                "challenge": "预算紧张",
                "verification": "合同签署",
                "result": "完成指标",
            },
        }
    }
    claims = bind_claims(bullets, _facts(), inputs)
    assert claims[0]["boundary"] == "个人负责谈判与条款，交付由团队完成"
    assert claims[0]["interview_details"]["decision"] == "直接谈判"


def test_write_claims_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        common.ensure_kb_structure(tmp)
        bullets = [{
            "fact_id": "W1",
            "source_fact": "丽水560万合同商务谈判，签约落地",
            "rewritten": "主导丽水560万合同商务谈判并签约落地",
            "responsibility_level": "主导方案或交付",
        }]
        claims = bind_claims(bullets, _facts())
        claims[0]["id"] = "claim-test-001"
        write_claims(tmp, claims)
        loaded = read_claims(tmp)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "claim-test-001"
        assert os.path.isfile(os.path.join(tmp, "原始事实", "claims", "claims.json"))
