#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/flow_controller.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from flow_controller import control_flow


def test_control_flow_can_proceed(tmp_path):
    (tmp_path / "progress.md").write_text("当前阶段：template_loaded\n", encoding="utf-8")
    (tmp_path / "context.md").write_text(
        "---\nselected_template:\n  id: shangye-guancha\n  confirmed: true\nrequirements:\n  topic: test\nnarrative_protocol:\n  fully_loaded: true\n  sections:\n    - name: 开头\n---\n",
        encoding="utf-8",
    )

    result = control_flow(tmp_path, "angle_diagnosed")
    assert result["can_proceed"] is True
    assert result["current_stage"] == "template_loaded"
    assert result["next_stage"] == "angle_diagnosed"


def test_control_flow_blocks_when_sub_skill_skipped(tmp_path):
    (tmp_path / "progress.md").write_text("当前阶段：angle_diagnosed\n", encoding="utf-8")
    (tmp_path / "context.md").write_text(
        "---\nselected_template:\n  id: shangye-guancha\n  confirmed: true\nrequirements:\n  topic: test\nnarrative_protocol:\n  fully_loaded: true\n  sections:\n    - name: 开头\n---\n",
        encoding="utf-8",
    )

    result = control_flow(tmp_path, "role_boundary")
    assert result["can_proceed"] is False
    assert any("gin-wechat-article-angle" in err for err in result["errors"])
    assert len(result["skipped_sub_skills"]) > 0
    assert "⚠️ 检测到流程异常" in result["rendered_progress"]


def test_control_flow_invalid_transition(tmp_path):
    (tmp_path / "progress.md").write_text("当前阶段：init\n", encoding="utf-8")
    (tmp_path / "context.md").write_text("---\n---\n", encoding="utf-8")

    result = control_flow(tmp_path, "draft_written")
    assert result["can_proceed"] is False
    assert any("非法阶段转换" in err for err in result["errors"])


def test_control_flow_hard_gate(tmp_path):
    (tmp_path / "progress.md").write_text("当前阶段：outline_generated\n", encoding="utf-8")
    (tmp_path / "context.md").write_text(
        "---\nselected_template:\n  id: shangye-guancha\n  confirmed: true\nrequirements:\n  topic: test\nnarrative_protocol:\n  fully_loaded: true\n  sections:\n    - name: 开头\noutline_candidates:\n  - rank: 1\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "outlines").mkdir()
    (tmp_path / "outlines" / "outline_candidates.md").write_text("# o", encoding="utf-8")

    result = control_flow(tmp_path, "outline_selected")
    assert result["can_proceed"] is True
    assert result["is_hard_gate"] is True
