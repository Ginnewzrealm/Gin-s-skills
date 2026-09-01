#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_migrate_glute_leg.py — 臀髋部/腿部合并迁移脚本测试。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import migrate_glute_leg as migrator


def test_merge_equipment_sections_dedupes_empty_placeholders():
    body1 = "### 杠铃\n（暂无）\n"
    body2 = "### 杠铃\n- [ ] [杠铃深蹲](./腿部/杠铃深蹲.md)\n"
    merged = migrator.merge_equipment_sections(body1, body2)
    assert "### 杠铃" in merged
    assert "- [ ] [杠铃深蹲]" in merged
    # 不应残留多余的「（暂无）」占位
    assert merged.count("（暂无）") == 0


def test_merge_index_updates_relative_links(tmp_path):
    lib_root = tmp_path / "01-训练动作库"
    lib_root.mkdir(parents=True)
    index = lib_root / "动作索引.md"
    index.write_text(
        "# 训练动作索引\n\n"
        "## 臀髋部\n### 杠铃\n- [ ] [杠铃臀冲](./臀髋部/杠铃臀冲.md)\n"
        "## 腿部\n### 杠铃\n- [ ] [杠铃深蹲](./腿部/杠铃深蹲.md)\n"
        "## 核心/腹部\n### 杠铃\n（暂无）\n",
        encoding="utf-8",
    )

    migrator.merge_index(str(tmp_path), dry_run=False)

    text = index.read_text(encoding="utf-8")
    assert "## 臀腿部" in text
    assert "./臀腿部/杠铃臀冲.md" in text
    assert "./臀腿部/杠铃深蹲.md" in text
    assert "./臀髋部/" not in text
    assert "./腿部/" not in text
    assert index.with_suffix(".md.bak").exists()


def test_merge_folders_moves_files(tmp_path):
    lib_root = tmp_path / "01-训练动作库"
    old_glute = lib_root / "臀髋部"
    old_leg = lib_root / "腿部"
    old_glute.mkdir(parents=True)
    old_leg.mkdir(parents=True)
    (old_glute / "杠铃臀冲.md").write_text("---\n", encoding="utf-8")
    (old_leg / "杠铃深蹲.md").write_text("---\n", encoding="utf-8")

    moved, conflicts = migrator.merge_folders(str(tmp_path), dry_run=False)

    assert len(moved) == 2
    assert len(conflicts) == 0
    assert (lib_root / "臀腿部" / "杠铃臀冲.md").exists()
    assert (lib_root / "臀腿部" / "杠铃深蹲.md").exists()


def test_merge_folders_reports_conflicts(tmp_path):
    lib_root = tmp_path / "01-训练动作库"
    old_glute = lib_root / "臀髋部"
    old_leg = lib_root / "腿部"
    old_glute.mkdir(parents=True)
    old_leg.mkdir(parents=True)
    (old_glute / "同名.md").write_text("a", encoding="utf-8")
    (old_leg / "同名.md").write_text("b", encoding="utf-8")

    moved, conflicts = migrator.merge_folders(str(tmp_path), dry_run=False)

    assert len(moved) == 1
    assert len(conflicts) == 1
    assert conflicts[0][0].endswith("同名.md")
