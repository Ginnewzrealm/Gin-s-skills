#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_progress_reporter.py — progress_reporter 单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from progress_reporter import (
    render_macro,
    render_micro,
    render_blocker,
    list_step_ids,
    get_phase_of_step,
)


class TestRenderMacro:
    """宏观进度渲染测试"""

    def test_render_macro_shows_all_phases(self):
        out = render_macro("main", "main_3", ["main_1", "main_2"])
        assert "阶段 1/4：周边界与数据拉取" in out
        assert "阶段 2/4：数据质量校验" in out
        assert "阶段 3/4：扫描与报告生成" in out
        assert "阶段 4/4：写入与通知" in out

    def test_render_macro_marks_completed_phase(self):
        out = render_macro("main", "main_4", ["main_1", "main_2", "main_3"])
        assert "阶段 1/4：周边界与数据拉取 [✓]" in out
        assert "阶段 2/4：数据质量校验 [当前]" in out

    def test_render_macro_highlights_current_phase(self):
        out = render_macro("main", "main_3", ["main_1", "main_2"])
        assert "阶段 1/4：周边界与数据拉取 [当前]" in out

    def test_render_macro_expands_current_phase_steps(self):
        out = render_macro("main", "main_3", ["main_1", "main_2"])
        assert "Step 1 计算本周周号与日期边界" in out
        assert "Step 2 发送开始通知" in out
        assert "Step 3 读取本期 7 天数据与上期输出表" in out

    def test_render_macro_current_step_highlighted(self):
        out = render_macro("main", "main_3", ["main_1", "main_2"])
        assert "Step 3 读取本期 7 天数据与上期输出表" in out
        assert "← 当前" in out

    def test_render_macro_resume_suffix(self):
        out = render_macro("main", "main_3", ["main_1", "main_2"], resume=True)
        assert "（恢复）" in out

    def test_render_macro_init_flow(self):
        out = render_macro("init", "init_4", ["init_1", "init_2", "init_3"])
        assert "阶段 2/4：表结构确认 [当前]" in out
        assert "Step 4 读取表头并建立字段映射" in out
        assert "[需确认]" in out
        assert "[可回环]" in out


class TestRenderMicro:
    """微观进度渲染测试"""

    def test_render_micro_shows_phase_title(self):
        out = render_micro("main", "main_3", ["main_1", "main_2"])
        assert "阶段 1/4：周边界与数据拉取" in out

    def test_render_micro_shows_progress_label(self):
        out = render_micro("main", "main_3", ["main_1", "main_2"])
        assert "Progress:" in out

    def test_render_micro_phase_locator(self):
        out = render_micro("main", "main_3", ["main_1", "main_2"], show_phase_locator=True)
        assert "当前处于 PDCA减脂分析的阶段 1/4：周边界与数据拉取" in out

    def test_render_micro_marks_done_steps(self):
        out = render_micro("main", "main_3", ["main_1", "main_2"])
        assert "[✓] Step 1 计算本周周号与日期边界" in out
        assert "[✓] Step 2 发送开始通知" in out


class TestRenderBlocker:
    """阻塞提示渲染测试"""

    def test_render_blocker_contains_reason(self):
        out = render_blocker("main", "main_4", "数据质量未通过「闸 1 · 覆盖率」")
        assert "⚠️ 当前阻塞：数据质量未通过「闸 1 · 覆盖率」" in out

    def test_render_blocker_contains_options(self):
        out = render_blocker("main", "main_4", "数据质量未通过", [
            "补充缺失的每日记录后，重新说\"跑一下周报\"",
            "输入\"跳过本周\"放弃本期分析",
        ])
        assert "你可以：" in out
        assert "补充缺失的每日记录后" in out
        assert "跳过本周" in out

    def test_render_blocker_contains_current_location(self):
        out = render_blocker("main", "main_4", "数据质量未通过")
        assert "当前位置：阶段 2/4：数据质量校验" in out
        assert "Step 4 执行数据质量双闸" in out


class TestHelpers:
    """辅助函数测试"""

    def test_list_step_ids(self):
        ids = list_step_ids("main")
        assert ids == [f"main_{i}" for i in range(1, 9)]

    def test_get_phase_of_step(self):
        assert get_phase_of_step("main", "main_4") == 2
        assert get_phase_of_step("init", "init_8") == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
