#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_stage_validator.py — stage_validator 单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from stage_validator import (
    StageValidationError,
    validate_transition,
    is_hard_gate,
    get_loop_target,
    list_loop_commands,
    next_step_id,
)


class TestValidateTransition:
    """阶段转换校验测试"""

    def test_valid_next_step(self):
        validate_transition("main", "main_3", "main_4", ["main_1", "main_2", "main_3"])

    def test_same_step_retry_allowed(self):
        validate_transition("main", "main_3", "main_3", ["main_1", "main_2", "main_3"])

    def test_illegal_skip_forward(self):
        with pytest.raises(StageValidationError):
            validate_transition("main", "main_3", "main_5", ["main_1", "main_2", "main_3"])

    def test_skip_forward_when_intermediate_completed(self):
        validate_transition("main", "main_3", "main_5", ["main_1", "main_2", "main_3", "main_4"])

    def test_hard_gate_not_confirmed_blocks_progress(self):
        with pytest.raises(StageValidationError) as exc_info:
            validate_transition("main", "main_4", "main_5", ["main_1", "main_2", "main_3"])
        assert "硬闸门" in str(exc_info.value)

    def test_hard_gate_confirmed_allows_progress(self):
        validate_transition("main", "main_4", "main_5", ["main_1", "main_2", "main_3", "main_4"])

    def test_start_from_none(self):
        validate_transition("init", None, "init_1", [])

    def test_unknown_flow(self):
        with pytest.raises(StageValidationError):
            validate_transition("unknown", None, "main_1", [])

    def test_unknown_step(self):
        with pytest.raises(StageValidationError):
            validate_transition("main", "main_1", "main_99", ["main_1"])

    def test_backward_to_completed_step_allowed(self):
        validate_transition("main", "main_5", "main_3", ["main_1", "main_2", "main_3", "main_4"])

    def test_backward_to_uncompleted_step_blocked(self):
        with pytest.raises(StageValidationError):
            validate_transition("main", "main_5", "main_2", ["main_1", "main_3", "main_4"])


class TestHardGate:
    """硬闸门判断测试"""

    def test_main_data_gate_is_hard_gate(self):
        assert is_hard_gate("main", "main_4") is True

    def test_auto_step_not_hard_gate(self):
        assert is_hard_gate("main", "main_1") is False

    def test_init_hard_gates(self):
        assert is_hard_gate("init", "init_2") is True
        assert is_hard_gate("init", "init_5") is True
        assert is_hard_gate("init", "init_6") is True


class TestLoop:
    """回环映射测试"""

    def test_loop_target_mapping(self):
        assert get_loop_target("init", "修改目标") == "init_5"
        assert get_loop_target("init", "修改定时") == "init_6"
        assert get_loop_target("main", "重新扫描") == "main_5"

    def test_unknown_loop_command(self):
        assert get_loop_target("init", "随便说说") is None

    def test_list_loop_commands(self):
        cmds = list_loop_commands("init")
        assert "重新映射字段" in cmds
        assert "修改目标" in cmds


class TestNextStep:
    """下一步获取测试"""

    def test_next_step(self):
        assert next_step_id("main", "main_3") == "main_4"

    def test_next_step_from_none(self):
        assert next_step_id("main", None) == "main_1"

    def test_next_step_last(self):
        assert next_step_id("main", "main_8") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
