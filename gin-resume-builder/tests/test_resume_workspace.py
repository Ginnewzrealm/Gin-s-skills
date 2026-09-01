#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_resume_workspace.py — 可复用工作空间测试。"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("html_renderer", _MODULE_DIR / "html_renderer.py")
hr = importlib.util.module_from_spec(_spec)
sys.modules["html_renderer"] = hr
_spec.loader.exec_module(hr)


def _resume():
    return {
        "title": "李明-高级销售经理-简历",
        "basic": {"姓名": "李明", "电话": "13800000000", "邮箱": "liming@example.com"},
        "sections": [],
    }


def test_save_workspace_creates_three_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resume = _resume()
        style_profile = {
            "page_size": "A4",
            "body_font": "Source Han Sans SC",
            "body_size_pt": 10.5,
            "margin_mm": 15,
            "theme_color": "#2563eb",
        }
        base_html = root / "基础简历.html"
        hr.save_workspace(resume, style_profile, str(base_html))
        assert (root / "基础简历.md").exists()
        assert (root / "简历版式档案.md").exists()
        assert base_html.exists()
        md_text = (root / "基础简历.md").read_text(encoding="utf-8")
        assert "李明" in md_text
