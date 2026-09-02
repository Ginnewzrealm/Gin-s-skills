#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_progress_store.py — progress_store 单元测试。"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest

from progress_store import (
    load_progress,
    save_progress,
    mark_step_done,
    clear_progress,
    is_step_completed,
    get_next_step,
)


class TestLoadProgress:
    """进度读取测试"""

    def test_load_existing_progress(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("""---
flow: init
current_step: init_3
completed_steps:
  - init_1
  - init_2
last_updated: 2026-09-02T14:30:00+08:00
---
""")
            tmp = f.name

        try:
            p = load_progress(tmp)
            assert p["flow"] == "init"
            assert p["current_step"] == "init_3"
            assert p["completed_steps"] == ["init_1", "init_2"]
        finally:
            os.remove(tmp)

    def test_load_missing_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = os.path.join(tmpdir, "no_such_progress.md")
            assert load_progress(missing) is None

    def test_load_invalid_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("这不是进度文件")
            tmp = f.name

        try:
            assert load_progress(tmp) is None
        finally:
            os.remove(tmp)


class TestSaveProgress:
    """进度保存测试"""

    def test_save_progress_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_2", ["main_1"], path)
            assert os.path.isfile(path)
            content = Path(path).read_text(encoding="utf-8")
            assert "flow: main" in content
            assert "current_step: main_2" in content
            assert "- main_1" in content


class TestMarkStepDone:
    """标记完成测试"""

    def test_mark_step_done_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            p = mark_step_done("init", "init_1", path)
            assert "init_1" in p["completed_steps"]
            assert p["current_step"] == "init_1"

            p2 = mark_step_done("init", "init_2", path)
            assert p2["completed_steps"] == ["init_1", "init_2"]
            assert p2["current_step"] == "init_2"


class TestClearProgress:
    """清除进度测试"""

    def test_clear_progress_removes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_1", ["main_1"], path)
            clear_progress(path)
            assert not os.path.exists(path)


class TestIsStepCompleted:
    """步骤完成判断测试"""

    def test_is_step_completed_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_2", ["main_1", "main_2"], path)
            assert is_step_completed("main", "main_1", path) is True
            assert is_step_completed("main", "main_2", path) is True

    def test_is_step_completed_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_1", ["main_1"], path)
            assert is_step_completed("main", "main_2", path) is False


class TestGetNextStep:
    """下一步获取测试"""

    def test_get_next_step_from_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_3", ["main_1", "main_2", "main_3"], path)
            assert get_next_step("main", path) == "main_4"

    def test_get_next_step_from_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            assert get_next_step("main", path) == "main_1"

    def test_get_next_step_last(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "progress.md")
            save_progress("main", "main_8", [f"main_{i}" for i in range(1, 9)], path)
            assert get_next_step("main", path) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
