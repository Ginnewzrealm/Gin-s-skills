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


def test_neutral_tone_flag():
    selected = [_item("只是帮忙整理了一下资料，工作比较被动")]
    bullets = rewrite(selected)
    assert bullets[0]["rewritten"] == selected[0]["bullet"]
    assert any("贬义" in g for g in bullets[0]["grey_zones"])


def test_car_pattern():
    selected = [_item("面对日均10万单履约超时问题，重排配送分区算法，超时率从8%降到3%")]
    bullets = rewrite(selected)
    assert "重排配送分区算法" in bullets[0]["rewritten"]
    assert "超时率从8%降到3%" in bullets[0]["rewritten"]
    assert "实现" in bullets[0]["rewritten"]


def test_weak_verb_replacement():
    selected = [_item("协助客户沟通与需求对接，用户满意度提升15%")]
    bullets = rewrite(selected)
    assert "支持" in bullets[0]["rewritten"] or "协同" in bullets[0]["rewritten"]
    assert "提升15%" in bullets[0]["rewritten"]


def test_grey_zone_when_no_metric():
    selected = [_item("负责客户沟通与需求对接")]
    bullets = rewrite(selected)
    assert any("缺少可量化结果" in g for g in bullets[0]["grey_zones"])


def test_hard_facts_preserved():
    selected = [_item("主导丽水560万合同商务谈判，签约落地")]
    bullets = rewrite(selected)
    assert "560万" in bullets[0]["rewritten"]
    assert "丽水" in bullets[0]["rewritten"]
