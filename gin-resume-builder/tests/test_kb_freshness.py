#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_freshness", Path(__file__).parent.parent / "scripts" / "kb_freshness.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_freshness"] = mod
spec.loader.exec_module(mod)

OLD = time.time() - 3600 * 24 * 7  # 一周前


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    projects = tmp_path / "原始事实" / "projects.md"
    projects.write_text("## 测试项目 | 顾问 | 2025-至今\n- 开单流程优化\n", encoding="utf-8")
    return str(tmp_path)


def _write_facts(tmp_path, mtime):
    p = tmp_path / "自动生成" / "facts.yaml"
    p.write_text('{"facts": []}', encoding="utf-8")
    os.utime(p, (mtime, mtime))


def test_stale_triggers_rebuild(tmp_path):
    root = _make_kb(tmp_path)
    _write_facts(tmp_path, OLD)
    # 源文件比 facts.yaml 新 → 过期 → 自动重建
    result = mod.ensure_fresh(root)
    assert result["status"] == "rebuilt"
    assert result["version"] >= 1
    fy = tmp_path / "自动生成" / "facts.yaml"
    proj = tmp_path / "原始事实" / "projects.md"
    assert fy.stat().st_mtime >= proj.stat().st_mtime - 1
    # 重建后索引里能查到源中的事实
    import facts_parser  # sys.path 已由 kb_freshness 注入
    data = facts_parser.build_facts(root)
    assert any(f.get("type") == "project" for f in data["facts"])


def test_fresh_no_rebuild(tmp_path):
    root = _make_kb(tmp_path)
    _write_facts(tmp_path, time.time())  # facts.yaml 最新
    meta_p = tmp_path / "自动生成" / "meta.json"
    meta_p.write_text('{"version": 5, "updated_at": "2026-01-01 00:00"}', encoding="utf-8")
    before = meta_p.stat().st_mtime

    result = mod.ensure_fresh(root)
    assert result["status"] == "fresh"
    assert meta_p.stat().st_mtime == before  # meta 未被触碰


def test_missing_facts_yaml_rebuilt(tmp_path):
    root = _make_kb(tmp_path)  # 不写 facts.yaml
    result = mod.ensure_fresh(root)
    assert result["status"] == "rebuilt"
    assert (tmp_path / "自动生成" / "facts.yaml").exists()


def test_check_only_does_not_rebuild(tmp_path):
    root = _make_kb(tmp_path)
    _write_facts(tmp_path, OLD)
    result = mod.ensure_fresh(root, check_only=True)
    assert result["status"] == "stale"
    assert not (tmp_path / "自动生成" / "meta.json").exists()  # 未重建


def test_empty_source_is_no_source(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    root = str(tmp_path)
    result = mod.ensure_fresh(root)
    assert result["status"] == "no_source"
    assert not (tmp_path / "自动生成" / "facts.yaml").exists()


def test_nested_source_change_detected(tmp_path):
    root = _make_kb(tmp_path)
    _write_facts(tmp_path, time.time() - 10)
    # 深层文件（behavioral_evidence）更新也要触发
    ev = tmp_path / "原始事实" / "behavioral_evidence"
    ev.mkdir()
    p = ev / "be_work_experience_001.md"
    p.write_text("## 证据\n", encoding="utf-8")
    assert mod.status(root) == "stale"
