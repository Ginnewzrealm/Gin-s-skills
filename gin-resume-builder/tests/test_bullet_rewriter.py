#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_bullet_rewriter.py — X-Y-Z 规则化改写器测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("bullet_rewriter", _MODULE_DIR / "bullet_rewriter.py")
br = importlib.util.module_from_spec(_spec)
sys.modules["bullet_rewriter"] = br
_spec.loader.exec_module(br)

rewrite = br.rewrite


def _item(bullet, fact_id="W1"):
    return {
        "fact_id": fact_id, "org": "绿城科技", "role": "大客户经理",
        "period": "2020.12-2025.06", "bullet": bullet,
    }


def test_xyz_basic():
    selected = [_item("负责丽水560万合同商务谈判，签约落地，回款周期缩短30%")]
    bullets = rewrite(selected)
    assert bullets[0]["rewritten"] == "商务谈判：负责丽水560万合同商务谈判，完成签约落地，实现回款周期缩短30%"
