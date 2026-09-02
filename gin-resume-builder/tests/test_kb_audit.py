#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_audit", Path(__file__).parent.parent / "scripts" / "kb_audit.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_audit"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_audit_reports_basic_counts(tmp_path):
    root = _make_kb(tmp_path)
    (tmp_path / "原始事实" / "basic_info.md").write_text("- 姓名: 张三\n", encoding="utf-8")
    (tmp_path / "原始事实" / "work_history.md").write_text("## 美团 | PM | 2024-至今\n- 负责增长\n", encoding="utf-8")
    (tmp_path / "原始事实" / "behavioral_evidence").mkdir()
    (tmp_path / "原始事实" / "behavioral_evidence" / "be_work_experience_001.md").write_text("test", encoding="utf-8")

    report = mod.audit(root)
    assert report["structure_ok"] is True
    assert report["counts"]["raw_files"] == 2
    assert report["counts"]["behavioral_evidence"] == 1
    assert report["counts"]["staged"] == 0


def test_audit_flags_missing_structure(tmp_path):
    root = str(tmp_path)
    report = mod.audit(root)
    assert report["structure_ok"] is False
    assert any("原始事实" in issue for issue in report["issues"])
