#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_pdf_ats_checker.py — ATS PDF 验证测试。"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("pdf_ats_checker", _MODULE_DIR / "pdf_ats_checker.py")
mod = importlib.util.module_from_spec(_spec)
sys.modules["pdf_ats_checker"] = mod
_spec.loader.exec_module(mod)


def test_check_pdf_falls_back_gracefully():
    result = mod.check_pdf("/nonexistent/file.pdf", keywords=[])
    assert result["available"] is False
    assert "extractor" in result


def test_check_pdf_detects_contact_and_keywords(tmp_path):
    pdf = tmp_path / "resume.pdf"
    pdf.write_text("dummy")
    text = "张三 13800138000 zhangsan@example.com Python B2B销售 五年经验 数据分析 项目管理 用户增长 商业化"
    with patch.object(mod, "extract_text_layer", return_value=(text, 1, "pypdf")):
        result = mod.check_pdf(str(pdf), keywords=["python", "b2b销售"])
    assert result["available"] is True
    assert result["extractor"] == "pypdf"
    assert result["contact"]["email"] is True
    assert result["contact"]["phone"] is True
    assert result["keywords"]["coverage"] == 1.0
    assert result["ok"] is True


def test_check_pdf_reports_missing_keyword(tmp_path):
    pdf = tmp_path / "resume.pdf"
    pdf.write_text("dummy")
    with patch.object(mod, "extract_text_layer", return_value=("简历 张三 13800138000", 1, "pypdf")):
        result = mod.check_pdf(str(pdf), keywords=["python"])
    assert result["keywords"]["missing"] == ["python"]
    assert result["ok"] is False


def test_check_pdf_flags_garbled_text(tmp_path):
    pdf = tmp_path / "resume.pdf"
    pdf.write_text("dummy")
    with patch.object(mod, "extract_text_layer", return_value=("简历 张三 zhangsan@example.com 锟斤拷", 1, "pypdf")):
        result = mod.check_pdf(str(pdf))
    assert result["garbled"] is True
    assert result["ok"] is False


def test_check_pdf_flags_too_little_text(tmp_path):
    pdf = tmp_path / "resume.pdf"
    pdf.write_text("dummy")
    with patch.object(mod, "extract_text_layer", return_value=("", 1, "pypdf")):
        result = mod.check_pdf(str(pdf))
    assert result["char_count"] == 0
    assert any("过少" in issue for issue in result["issues"])
