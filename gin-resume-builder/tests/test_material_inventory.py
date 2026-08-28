#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_material_inventory.py — 材料盘点测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("material_inventory", _MODULE_DIR / "material_inventory.py")
inv = importlib.util.module_from_spec(_spec)
sys.modules["material_inventory"] = inv
_spec.loader.exec_module(inv)

inventory = inv.inventory


def test_inventory_returns_top_three_gaps():
    facts = {
        "basic_info": {},
        "facts": [],
        "skills": [],
    }
    gaps = inventory("/tmp", facts)
    assert len(gaps) <= 3
    assert all(level in ("high", "medium", "low") for level, _ in gaps)


def test_inventory_prioritizes_missing_job_intent():
    facts = {
        "basic_info": {"姓名": "张三"},
        "facts": [
            {
                "type": "work",
                "company": "A公司",
                "bullets": ["完成日常工作"],
                "responsibility_levels": [""],
            }
        ],
        "skills": ["Python"],
    }
    gaps = inventory("/tmp", facts)
    assert gaps[0][0] == "high"
    assert "求职意向" in gaps[0][1]


def test_inventory_limits_to_three():
    facts = {
        "basic_info": {},
        "facts": [
            {"type": "work", "company": "A", "bullets": [], "responsibility_levels": []},
            {"type": "work", "company": "B", "bullets": [], "responsibility_levels": []},
            {"type": "work", "company": "C", "bullets": [], "responsibility_levels": []},
            {"type": "work", "company": "D", "bullets": [], "responsibility_levels": []},
        ],
        "skills": [],
    }
    gaps = inventory("/tmp", facts)
    assert len(gaps) == 3


def test_inventory_no_gaps_when_complete():
    facts = {
        "basic_info": {"姓名": "张三", "求职意向": "高级后端工程师"},
        "facts": [
            {
                "type": "work",
                "company": "A公司",
                "bullets": [
                    "**[主导]** 重构订单系统，接口响应从 120ms 降至 45ms",
                    "**[主导]** 设计降级熔断方案，可用性提升至 99.99%",
                    "**[负责模块]** 带领 5 人小组保障日均千万级交易",
                ],
                "responsibility_levels": ["主导方案或交付", "主导方案或交付", "负责模块"],
            },
            {
                "type": "project",
                "name": "订单中心重构",
                "bullets": ["完成分布式迁移"],
            },
        ],
        "skills": ["Java", "Spring Cloud", "Redis"],
    }
    gaps = inventory("/tmp", facts)
    assert gaps == []
