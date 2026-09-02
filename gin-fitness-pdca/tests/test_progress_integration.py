#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_progress_integration.py — 进度条模块集成测试。"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from progress_reporter import render_macro, render_micro, render_blocker
from progress_store import load_progress, mark_step_done, clear_progress, get_next_step
from stage_validator import validate_transition, get_loop_target


class TestProgressIntegration:
    """进度条端到端流程测试"""

    def test_init_flow_from_start_to_hard_gate(self):
        """模拟初始化流程从启动到第一个硬闸门"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")

            # 开始：没有进度，渲染宏观仪表盘
            out = render_macro("init", "init_1", [], resume=False)
            assert "阶段 1/4：环境准备 [当前]" in out
            assert "Step 1 检测 lark-cli" in out

            # Step 1 自动完成
            progress = mark_step_done("init", "init_1", path)
            assert progress["current_step"] == "init_1"
            assert get_next_step("init", path) == "init_2"

            # 推进到 Step 2（硬闸门），校验合法
            validate_transition("init", "init_1", "init_2", progress["completed_steps"])

            # Step 2 完成后渲染当前阶段
            progress = mark_step_done("init", "init_2", path)
            out = render_macro("init", "init_2", progress["completed_steps"])
            assert "阶段 1/4：环境准备 [当前]" in out
            assert "[✓] Step 1 检测 lark-cli" in out
            assert "[✓] Step 2 询问并保存电子表格链接" in out
            assert "← 当前" in out

    def test_resume_from_interrupted_init(self):
        """模拟初始化中断后恢复"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            # 预先写入中断状态：已完成 init_1~3，当前在 init_4
            from progress_store import save_progress
            save_progress("init", "init_4", ["init_1", "init_2", "init_3"], path)

            progress = load_progress(path)
            out = render_macro("init", progress["current_step"], progress["completed_steps"], resume=True)
            assert "（恢复）" in out
            assert "阶段 2/4：表结构确认 [当前]" in out
            assert "Step 4 读取表头并建立字段映射" in out
            assert "← 当前" in out

    def test_main_flow_data_gate_blocks_then_recover(self):
        """模拟主流程数据质量硬闸门阻塞与恢复"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")

            # 完成阶段 1
            progress = mark_step_done("main", "main_3", path)
            # 尝试推进到 main_5 跳过 main_4（非法）
            with pytest.raises(Exception):
                validate_transition("main", "main_3", "main_5", progress["completed_steps"])

            # 正常推进到 main_4 硬闸门
            validate_transition("main", "main_3", "main_4", progress["completed_steps"])
            progress = mark_step_done("main", "main_4", path)

            # 渲染阻塞提示
            blocker = render_blocker(
                "main",
                "main_4",
                "数据质量未通过「闸 1 · 覆盖率」",
                ["补充缺失的每日记录后，重新说\"跑一下周报\"", "输入\"跳过本周\"放弃本期分析"],
            )
            assert "⚠️ 当前阻塞" in blocker
            assert "补充缺失的每日记录" in blocker

            # 用户说"重新校验数据"，回环到 main_4
            target = get_loop_target("main", "重新校验数据")
            assert target == "main_4"

    def test_loop_and_rerender(self):
        """模拟回环后重新渲染 checklist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")

            # 完成到 init_5
            progress = mark_step_done("init", "init_5", path)
            target = get_loop_target("init", "修改目标")
            assert target == "init_5"

            # 重新渲染：当前步骤回到 init_5，后续步骤重置
            out = render_macro("init", "init_5", progress["completed_steps"])
            assert "阶段 3/4：目标配置 [当前]" in out
            assert "Step 5 询问目标参数" in out

            out_micro = render_micro("init", "init_5", progress["completed_steps"], show_phase_locator=True)
            assert "当前处于 PDCA减脂分析的阶段 3/4：目标配置" in out_micro


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
