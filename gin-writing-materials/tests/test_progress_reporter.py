#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/progress_reporter.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from progress_reporter import (
    render_mine,
    render_micro,
    render_blocker,
    get_default_completed,
)


def test_render_mine_shows_current_and_done():
    result = render_mine(
        current_key="topic_defined",
        completed_keys=["project_located"],
    )
    assert "📝 写作素材挖掘进度" in result
    assert "- [✓] Step project_located 定位/创建项目文件夹 [自动]" in result
    assert "- [ ] Step topic_defined 生成主题定义并确认读者/文体/方向 [硬闸门]  ← 当前" in result
    assert "- [ ] Step anchors_loaded 拉取锚点素材到成品库 [自动]" in result


def test_render_mine_completed_steps_before_current():
    result = render_mine(current_key="mining")
    assert "- [✓] Step project_located 定位/创建项目文件夹 [自动]" in result
    assert "- [✓] Step topic_defined 生成主题定义并确认读者/文体/方向 [硬闸门]" in result
    assert "- [✓] Step anchors_loaded 拉取锚点素材到成品库 [自动]" in result
    assert "- [✓] Step domain_selected 选择本次挖掘域 [需确认]" in result
    assert "- [ ] Step mining 对话挖掘素材 [硬闸门] [可回环]  ← 当前" in result


def test_render_micro_for_review():
    result = render_micro("review", current_key="fragments_loaded")
    assert "📝 写作素材 — review" in result
    assert "- [✓] Step 1 定位项目文件夹 [自动]" in result
    assert "- [ ] Step 2 加载已有素材碎片 [自动]  ← 当前" in result


def test_render_blocker():
    result = render_blocker(
        step_name="生成主题定义并确认读者/文体/方向",
        reason="等待你确认主题定义",
        options=['输入 "OK" 或 "确认" 继续', '输入 "修改" 调整主题'],
    )
    assert "⚠️ 当前阻塞：等待你确认主题定义" in result
    assert '输入 "OK" 或 "确认" 继续' in result


def test_get_default_completed_for_mine():
    completed = get_default_completed("domain_selected")
    assert "project_located" in completed
    assert "topic_defined" in completed
    assert "domain_selected" not in completed
