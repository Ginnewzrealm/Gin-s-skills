#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_interview", Path(__file__).parent.parent / "scripts" / "kb_interview.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_interview"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_cmd_stage_evidence_creates_preview(tmp_path):
    root = _make_kb(tmp_path)
    sid = mod.cmd_stage_evidence(
        root=root,
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
    assert sid.startswith("st_work_experience_")
    assert (tmp_path / "原始事实" / "待确认" / (sid + ".md")).exists()


def test_cmd_confirm_evidence_writes_and_cleans(tmp_path):
    root = _make_kb(tmp_path)
    sid = mod.cmd_stage_evidence(root=root, domain="work_experience", source="s", description="d",
                                  background="b", task="t", actions=["a"], result="r",
                                  insight="i", boundary="b2", verbatim="v")
    name = mod.cmd_confirm_evidence(root, sid)
    assert name.startswith("be_work_experience_")
    assert (tmp_path / "原始事实" / "behavioral_evidence" / (name + ".md")).exists()
    assert not (tmp_path / "原始事实" / "待确认" / (sid + ".md")).exists()


def test_cmd_reject_evidence_deletes_preview(tmp_path):
    root = _make_kb(tmp_path)
    sid = mod.cmd_stage_evidence(root=root, domain="project_experience", source="s", description="d",
                                  background="b", task="t", actions=["a"], result="r",
                                  insight="i", boundary="b2", verbatim="v")
    mod.cmd_reject_evidence(root, sid)
    staged_dir = tmp_path / "原始事实" / "待确认"
    assert len(list(staged_dir.iterdir())) == 0


def test_cmd_list_staged_shows_items(tmp_path):
    root = _make_kb(tmp_path)
    mod.cmd_stage_evidence(root=root, domain="work_experience", source="s", description="第一项",
                           background="b", task="t", actions=["a"], result="r",
                           insight="i", boundary="b2", verbatim="v")
    mod.cmd_stage_evidence(root=root, domain="work_experience", source="s", description="第二项",
                           background="b", task="t", actions=["a"], result="r",
                           insight="i", boundary="b2", verbatim="v")
    items = mod.cmd_list_staged(root)
    assert len(items) == 2
    assert any("第一项" in desc for _, desc, _ in items)
