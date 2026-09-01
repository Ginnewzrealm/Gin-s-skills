#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_html_renderer.py — HTML 渲染器测试。"""
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

render = hr.render


def _resume():
    return {
        "title": "李明-高级销售经理-简历",
        "basic": {
            "姓名": "李明",
            "电话": "13800000000",
            "邮箱": "liming@example.com",
            "城市": "杭州",
            "求职意向": "高级销售经理",
        },
        "sections": [
            {
                "title": "岗位胜任",
                "items": [{"tag": "大客户销售", "text": "5 年 B2B 销售经验，擅长复杂合同谈判。"}],
            },
            {
                "title": "工作经历",
                "entries": [
                    {
                        "org": "示例科技",
                        "role": "销售总监",
                        "period": "2020-2025",
                        "summary": "负责华东区大客户拓展与团队管理。",
                        "bullets": ["主导 560 万合同商务谈判并签约落地"],
                    }
                ],
            },
        ],
    }


def test_render_default_html():
    html = render(_resume())
    assert "李明" in html
    assert "示例科技" in html
    assert "13800000000" in html


def test_render_editable_html():
    html = render(_resume(), editable=True)
    assert "contenteditable" in html
    assert "生成 PDF" in html
