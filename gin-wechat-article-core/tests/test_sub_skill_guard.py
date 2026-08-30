#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/sub_skill_guard.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sub_skill_guard import check_sub_skill_executed


def test_check_sub_skill_ok(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "diagnosis_report.md").write_text("# d", encoding="utf-8")
    (tmp_path / "context.md").write_text("---\nangle_candidates: ok\n---\n", encoding="utf-8")

    errors = check_sub_skill_executed(
        tmp_path,
        "gin-wechat-article-angle",
        ["angle_candidates"],
        ["reports/diagnosis_report.md"],
    )
    assert errors == []


def test_check_sub_skill_missing_context_key(tmp_path):
    (tmp_path / "context.md").write_text("---\n---\n", encoding="utf-8")
    errors = check_sub_skill_executed(
        tmp_path,
        "gin-wechat-article-angle",
        ["angle_candidates"],
        [],
    )
    assert any("angle_candidates" in err for err in errors)


def test_check_sub_skill_missing_file(tmp_path):
    (tmp_path / "context.md").write_text("---\nangle_candidates: ok\n---\n", encoding="utf-8")
    errors = check_sub_skill_executed(
        tmp_path,
        "gin-wechat-article-angle",
        ["angle_candidates"],
        ["reports/diagnosis_report.md"],
    )
    assert any("diagnosis_report.md" in err for err in errors)


def test_check_sub_skill_empty_file(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "diagnosis_report.md").write_text("", encoding="utf-8")
    (tmp_path / "context.md").write_text("---\nangle_candidates: ok\n---\n", encoding="utf-8")
    errors = check_sub_skill_executed(
        tmp_path,
        "gin-wechat-article-angle",
        ["angle_candidates"],
        ["reports/diagnosis_report.md"],
    )
    assert any("为空" in err for err in errors)
