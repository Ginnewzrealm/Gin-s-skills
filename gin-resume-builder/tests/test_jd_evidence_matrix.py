#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_jd_evidence_matrix.py — JD-证据匹配矩阵测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("jd_evidence_matrix", _MODULE_DIR / "jd_evidence_matrix.py")
mod = importlib.util.module_from_spec(_spec)
sys.modules["jd_evidence_matrix"] = mod
_spec.loader.exec_module(mod)

build_matrix = mod.build_matrix


def test_matrix_classifies_direct_match():
    jd = {
        "requirements": [
            {"text": "5 年以上 B2B 销售经验", "type": "required"},
        ]
    }
    facts = {
        "facts": [
            {"fact_id": "W1", "type": "work", "role": "B2B 销售经理", "bullets": ["5 年 B2B 销售经验，负责丽水 560 万合同谈判"]}
        ]
    }
    matrix = build_matrix(jd, facts)
    assert matrix[0]["level"] == "direct"


def test_matrix_classifies_gap():
    jd = {
        "requirements": [
            {"text": "精通 Python 机器学习", "type": "required"},
        ]
    }
    facts = {"facts": []}
    matrix = build_matrix(jd, facts)
    assert matrix[0]["level"] == "absent"
