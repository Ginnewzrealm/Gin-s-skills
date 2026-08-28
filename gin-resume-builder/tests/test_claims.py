#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_claims.py — claim 目录结构与字段定义测试。"""
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

ensure_kb_structure = common.ensure_kb_structure
CLAIM_FIELDS = common.CLAIM_FIELDS
read_claims = common.read_claims
write_claim = common.write_claim
write_claims = common.write_claims
CLAIMS_AGGREGATE = common.CLAIMS_AGGREGATE


def _sample_claim(cid="claim-001"):
    return {
        "id": cid,
        "section": "work_history",
        "section_id": "绿城科技-2020.12",
        "source_fact": "丽水560万合同商务谈判，签约落地",
        "candidate_wording": "主导丽水560万合同商务谈判并签约落地",
        "responsibility_level": "主导方案或交付",
        "verification_status": "已确认",
        "allowed_uses": ["中建八局节能改造方向"],
        "interview_details": {
            "decision": "选择直接谈判而非招标",
            "challenge": "预算周期紧张",
            "verification": "合同签署并回款",
            "result": "完成年度大客户指标",
        },
        "boundary": "个人负责商务谈判与合同条款设计，交付由团队共同完成",
        "risk_notes": [],
        "last_verified": "2026-08-28",
    }


def test_ensure_kb_structure_creates_claims_dir():
    with tempfile.TemporaryDirectory() as tmp:
        ensure_kb_structure(tmp)
        assert os.path.isdir(os.path.join(tmp, "原始事实", "claims"))


def test_claim_fields_match_asu_schema():
    assert set(CLAIM_FIELDS) == {
        "id",
        "section",
        "section_id",
        "source_fact",
        "candidate_wording",
        "responsibility_level",
        "verification_status",
        "allowed_uses",
        "interview_details",
        "boundary",
        "risk_notes",
        "last_verified",
    }


def test_write_claim_creates_file_and_aggregate():
    with tempfile.TemporaryDirectory() as tmp:
        ensure_kb_structure(tmp)
        claim = _sample_claim()
        path = write_claim(tmp, claim)
        assert os.path.isfile(path)
        assert path.endswith("claim-001.json")
        agg = os.path.join(tmp, "原始事实", "claims", CLAIMS_AGGREGATE)
        assert os.path.isfile(agg)
        with open(agg, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "claim-001"


def test_write_claim_validates_required_fields():
    with tempfile.TemporaryDirectory() as tmp:
        ensure_kb_structure(tmp)
        claim = _sample_claim()
        claim.pop("boundary")
        try:
            write_claim(tmp, claim)
        except ValueError as e:
            assert "boundary" in str(e)
        else:
            raise AssertionError("缺少必填字段时应抛出 ValueError")


def test_write_claims_creates_sorted_aggregate():
    with tempfile.TemporaryDirectory() as tmp:
        ensure_kb_structure(tmp)
        write_claims(tmp, [_sample_claim("claim-002"), _sample_claim("claim-001")])
        claims = read_claims(tmp)
        assert [c["id"] for c in claims] == ["claim-001", "claim-002"]
        agg = os.path.join(tmp, "原始事实", "claims", CLAIMS_AGGREGATE)
        with open(agg, encoding="utf-8") as f:
            data = json.load(f)
        assert [c["id"] for c in data] == ["claim-001", "claim-002"]


def test_read_claims_empty_when_no_claims_dir():
    with tempfile.TemporaryDirectory() as tmp:
        assert read_claims(tmp) == []
