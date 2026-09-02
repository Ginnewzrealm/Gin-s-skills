#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_staged_evidence.py — 暂存证据生命周期测试。"""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "staged_evidence", Path(__file__).parent.parent / "scripts" / "staged_evidence.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["staged_evidence"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_stage_creates_markdown_and_json(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层", "配客户经理"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        verbatim="当时发现只看GMV会漏掉高活跃小体量商户",
    )
    staged_dir = tmp_path / "原始事实" / "待确认"
    md = staged_dir / (sid + ".md")
    js = staged_dir / (sid + ".json")
    assert md.exists()
    assert js.exists()
    assert "商户分层运营" in md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["domain"] == "work_experience"
    assert data["star"]["Result"] == "80万→110万"


def test_confirm_moves_to_behavioral_evidence(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        verbatim="原话",
    )
    name = store.confirm(sid)
    assert name.startswith("be_work_experience_")
    evidence_dir = tmp_path / "原始事实" / "behavioral_evidence"
    assert (evidence_dir / (name + ".md")).exists()
    assert not (tmp_path / "原始事实" / "待确认" / (sid + ".md")).exists()
    assert not (tmp_path / "原始事实" / "待确认" / (sid + ".json")).exists()


def test_reject_deletes_preview_files(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="project_experience",
        source="增长项目",
        description="测试",
        background="背景",
        task="任务",
        actions=["行动"],
        result="结果",
        insight="判断",
        boundary="边界",
        verbatim="",
    )
    store.reject(sid)
    staged_dir = tmp_path / "原始事实" / "待确认"
    assert len(list(staged_dir.iterdir())) == 0
