#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_company_researcher.py — 公司研究缓存测试。"""
import importlib.util
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("company_researcher", _MODULE_DIR / "company_researcher.py")
cr = importlib.util.module_from_spec(_spec)
sys.modules["company_researcher"] = cr
_spec.loader.exec_module(cr)


def test_normalize_company_name():
    assert cr.normalize_name(" 示例科技 有限公司 ") == "示例"
    assert cr.normalize_name("Acme Corp.") == "acme-corp"


def test_cache_path_and_ttl():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_path = cr.cache_path(root, "示例科技")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "company": "示例科技",
            "fetched_date": (date.today() - timedelta(days=10)).isoformat(),
            "sources": {},
        }), encoding="utf-8")
        cached = cr.load_cache(root, "示例科技")
        assert cached is not None
        assert cached["company"] == "示例科技"
