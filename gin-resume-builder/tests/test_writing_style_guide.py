#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_writing_style_guide.py — 写作风格指南可用性测试。"""
from pathlib import Path


def test_writing_style_guide_exists_and_has_rules():
    path = Path(__file__).parent.parent / "references" / "writing-style-guide.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "禁止" in text
    assert "陈词滥调" in text
    assert "面向未来" in text
