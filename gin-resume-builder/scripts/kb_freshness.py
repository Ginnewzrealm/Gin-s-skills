#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_freshness.py — facts.yaml 新鲜度检查与自动重建。

背景：读取纪律规定事实类检索只走 facts.yaml（自动生成/），
但若用户手动编辑过 原始事实/ 而索引未重建，Agent 按纪律查到的就是旧数据——
查漏了它自然会退回全库乱翻，纪律白写。本脚本在每次技能触发入口（知识库检查环节）
执行：原始事实/ 任一文件比 facts.yaml 新 = 索引过期 → 自动重建（走 post_write 审计链）。

用法：
    python3 scripts/kb_freshness.py --kb <路径>          # 过期则自动重建
    python3 scripts/kb_freshness.py --kb <路径> --check  # 只报告不重建
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import facts_parser

SOURCE_EXTS = {".md", ".markdown", ".txt", ".yaml", ".yml", ".json"}
TOLERANCE = 1.0  # 秒：mtime 浮点抖动容差


def latest_source_mtime(root):
    """原始事实/ 下所有源文件的最新 mtime；目录不存在或无文件返回 0.0"""
    raw = os.path.join(root, common.DIR_RAW)
    latest = 0.0
    if not os.path.isdir(raw):
        return latest
    for dirpath, _dirnames, filenames in os.walk(raw):
        for name in filenames:
            if os.path.splitext(name)[1].lower() not in SOURCE_EXTS:
                continue
            p = os.path.join(dirpath, name)
            try:
                latest = max(latest, os.path.getmtime(p))
            except OSError:
                continue
    return latest


def facts_mtime(root):
    p = os.path.join(root, common.DIR_AUTO, "facts.yaml")
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def status(root):
    """no_source（无源文件）/ fresh（索引最新）/ stale（索引过期或缺失）"""
    src = latest_source_mtime(root)
    if src == 0.0:
        return "no_source"
    fy = facts_mtime(root)
    if fy == 0.0 or src > fy + TOLERANCE:
        return "stale"
    return "fresh"


def ensure_fresh(root, check_only=False):
    """入口检查：stale 且非 check_only → 走 post_write 审计链重建。
    返回 {"status": ..., "version": ...}"""
    st = status(root)
    if st != "stale" or check_only:
        return {"status": st, "version": None}
    data, ver = facts_parser.post_write(root, "索引过期自动重建（kb_freshness 入口检查）")
    return {"status": "rebuilt", "version": ver}


def main():
    ap = argparse.ArgumentParser(description="facts.yaml 新鲜度检查与自动重建")
    ap.add_argument("--kb", default=None, help="知识库路径（缺省读 config.yaml）")
    ap.add_argument("--check", action="store_true", help="只报告不重建")
    args = ap.parse_args()

    root = common.kb_root(args.kb)
    result = ensure_fresh(root, check_only=args.check)
    if result["status"] == "rebuilt":
        print("[完成] facts.yaml 过期，已自动重建（版本 v%d）" % result["version"])
    elif result["status"] == "stale":
        print("[警告] facts.yaml 已过期（源有更新但未重建），请加 --check 移除以自动重建")
    elif result["status"] == "fresh":
        print("[完成] facts.yaml 最新，无需重建")
    else:
        print("[信息] 原始事实/ 无源文件，跳过新鲜度检查")


if __name__ == "__main__":
    main()
