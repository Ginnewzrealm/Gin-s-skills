#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_kb_interview.py — KB 访谈测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("kb_interview", _MODULE_DIR / "kb_interview.py")
ki = importlib.util.module_from_spec(_spec)
sys.modules["kb_interview"] = ki
_spec.loader.exec_module(ki)


def test_career_value_radar_prompts_exist():
    prompts = ki.career_value_radar_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) >= 6
    assert any("商业化" in p or "变现" in p for p in prompts)
    assert any("用户洞察" in p or "用户" in p for p in prompts)
