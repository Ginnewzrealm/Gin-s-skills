#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_kb_save_evidence.py — save-evidence 硬闸门写入测试。"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_interview", Path(__file__).parent.parent / "scripts" / "kb_interview.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_interview"] = mod
spec.loader.exec_module(mod)


def test_save_evidence_creates_file(tmp_path):
    root = str(tmp_path)
    # 创建必要目录
    (tmp_path / "原始事实").mkdir()
    (tmp_path / "自动生成").mkdir()
    (tmp_path / "面试素材").mkdir()
    (tmp_path / "生成物").mkdir()

    mod.cmd_save_evidence(
        root=root,
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层", "配客户经理"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        confidence="confirmed",
        verbatim="当时发现只看GMV会漏掉高活跃小体量商户",
    )

    be_dir = tmp_path / "原始事实" / "behavioral_evidence"
    files = list(be_dir.glob("*.md"))
    assert len(files) == 2  # evidence file + map.md
    evidence = [f for f in files if f.name != "map.md"][0]
    text = evidence.read_text(encoding="utf-8")
    assert "商户分层运营" in text
    assert "80万→110万" in text
    assert "活跃度比GMV重要" in text
