#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_star_story_backfill.py — STAR 故事回填 claim interview_details 测试。"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("common", _MODULE_DIR / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)

_spec2 = importlib.util.spec_from_file_location("star_story_generator", _MODULE_DIR / "star_story_generator.py")
gen = importlib.util.module_from_spec(_spec2)
sys.modules["star_story_generator"] = gen
_spec2.loader.exec_module(gen)

categorize = gen.categorize
_backfill_interview_details = gen._backfill_interview_details


def _facts_with_responsibility():
    return {
        "facts": [
            {
                "fact_id": "W1",
                "type": "work",
                "company": "绿城科技",
                "role": "大客户经理",
                "period": "2020.12-2025.06",
                "bullets": ["**[主导]** 带领团队完成大客户攻坚，业绩增长 30%"],
                "responsibility_levels": ["主导方案或交付"],
            }
        ]
    }


def test_backfill_updates_claim_interview_details():
    with tempfile.TemporaryDirectory() as tmp:
        common.ensure_kb_structure(tmp)
        # 先写入一个 claim
        claim = {
            "id": "claim-001",
            "section": "work_history",
            "section_id": "绿城科技-202012",
            "source_fact": "带领团队完成大客户攻坚，业绩增长 30%",
            "candidate_wording": "主导丽水560万合同商务谈判并签约落地",
            "responsibility_level": "主导方案或交付",
            "verification_status": "已确认",
            "allowed_uses": [],
            "interview_details": {
                "decision": "（待用户补充：为什么这样做）",
                "challenge": "（待用户补充：难点是什么）",
                "verification": "（待用户补充：结果怎么验证）",
                "result": "（待用户补充：对业务的影响）",
            },
            "boundary": "个人负责商务谈判",
            "risk_notes": [],
            "last_verified": "2026-08-28",
        }
        common.write_claim(tmp, claim)

        facts = _facts_with_responsibility()
        stories = categorize(facts)
        updated = _backfill_interview_details(tmp, stories)

        assert updated == 1
        loaded = common.read_claims(tmp)
        assert loaded[0]["interview_details"]["result"].startswith("（由 STAR 故事库回填")


def test_backfill_skips_non_placeholder_claims():
    with tempfile.TemporaryDirectory() as tmp:
        common.ensure_kb_structure(tmp)
        claim = {
            "id": "claim-001",
            "section": "work_history",
            "section_id": "绿城科技-202012",
            "source_fact": "带领团队完成大客户攻坚，业绩增长 30%",
            "candidate_wording": "主导丽水560万合同商务谈判并签约落地",
            "responsibility_level": "主导方案或交付",
            "verification_status": "已确认",
            "allowed_uses": [],
            "interview_details": {
                "decision": "已确认",
                "challenge": "已确认",
                "verification": "已确认",
                "result": "已确认",
            },
            "boundary": "个人负责商务谈判",
            "risk_notes": [],
            "last_verified": "2026-08-28",
        }
        common.write_claim(tmp, claim)

        facts = _facts_with_responsibility()
        stories = categorize(facts)
        updated = _backfill_interview_details(tmp, stories)

        assert updated == 0
        loaded = common.read_claims(tmp)
        assert loaded[0]["interview_details"]["result"] == "已确认"
