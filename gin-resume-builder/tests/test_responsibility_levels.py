#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_responsibility_levels.py — 责任层级与验证状态解析测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("common", _MODULE_DIR / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)

extract_responsibility_level = common.extract_responsibility_level
parse_entries = common.parse_entries


def test_extract_responsibility_level_with_marker():
    level, text = extract_responsibility_level("**[主导]** 丽水560万合同商务谈判，签约落地")
    assert level == "主导方案或交付"
    assert text == "丽水560万合同商务谈判，签约落地"


def test_extract_responsibility_level_with_colon():
    level, text = extract_responsibility_level("**[参与]**: 省发改委对接会议，介绍绿城经验")
    assert level == "参与"
    assert text == "省发改委对接会议，介绍绿城经验"


def test_extract_responsibility_level_without_marker():
    level, text = extract_responsibility_level("业绩增长：主导重点客户攻坚，营收增长 30%")
    assert level == ""
    assert text == "业绩增长：主导重点客户攻坚，营收增长 30%"


def test_parse_entries_extracts_responsibility_levels():
    md = """## 绿城科技集团有限公司 | 大客户经理 | 2020.12-2025.06
- **[主导]** 丽水560万合同商务谈判，签约落地
- **[参与]** 省发改委对接会议，介绍绿城经验
- 独立负责华东区域客户续约，续约率 95%
"""
    entries = parse_entries(md)
    assert len(entries) == 1
    e = entries[0]
    assert e["bullets"][0] == "**[主导]** 丽水560万合同商务谈判，签约落地"
    assert e["responsibility_levels"] == ["主导方案或交付", "参与", ""]


def test_parse_entries_empty_for_no_markers():
    md = """## A 公司 | 产品经理 | 2020-2024
- 负责需求分析
- 完成产品上线
"""
    entries = parse_entries(md)
    assert entries[0]["responsibility_levels"] == ["", ""]
