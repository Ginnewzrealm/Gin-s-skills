#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_audit.py — 知识库结构与写入审计。

用法：
    python3 scripts/kb_audit.py --kb <路径>
    python3 scripts/kb_audit.py --kb <路径> --since 2026-09-01
"""
import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def _exists(root, *parts):
    return os.path.isdir(os.path.join(root, *parts))


def _count_files(root, *parts):
    d = os.path.join(root, *parts)
    if not os.path.isdir(d):
        return 0
    return len([n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n))])


def _recent_files(root, since_str):
    try:
        since = datetime.strptime(since_str, "%Y-%m-%d")
    except ValueError:
        raise SystemExit("[错误] --since 格式应为 YYYY-MM-DD")
    result = []
    for base in (common.DIR_RAW, common.DIR_AUTO, common.DIR_INTERVIEW, common.DIR_OUTPUT):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            for name in filenames:
                path = os.path.join(dirpath, name)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime >= since:
                    result.append((path, mtime.isoformat()))
    return result


def audit(root, since=None):
    report = {
        "path": root,
        "structure_ok": True,
        "issues": [],
        "counts": {},
        "recent_files": [],
    }

    required = [common.DIR_RAW, common.DIR_AUTO, common.DIR_INTERVIEW, common.DIR_OUTPUT]
    for d in required:
        if not _exists(root, d):
            report["structure_ok"] = False
            report["issues"].append("缺少目录：%s" % d)

    if report["structure_ok"]:
        raw_count = 0
        for key in common.RAW_FILES:
            p = os.path.join(root, common.DIR_RAW, common.RAW_FILES[key])
            if os.path.exists(p) and os.path.getsize(p) > 0:
                raw_count += 1
        report["counts"]["raw_files"] = raw_count
        report["counts"]["behavioral_evidence"] = _count_files(root, common.DIR_RAW, "behavioral_evidence")
        report["counts"]["staged"] = _count_files(root, common.DIR_RAW, common.DIR_STAGED) // 2  # md + json
        report["counts"]["claims"] = _count_files(root, common.DIR_RAW, "claims")

        staged_dir = os.path.join(root, common.DIR_RAW, common.DIR_STAGED)
        if os.path.isdir(staged_dir):
            stale = []
            threshold = datetime.now() - timedelta(days=7)
            for name in os.listdir(staged_dir):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(staged_dir, name)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime < threshold:
                    stale.append(name)
            if stale:
                report["issues"].append("待确认区有 %d 条超过 7 天未确认：%s" % (len(stale), ", ".join(sorted(stale))))

    if since:
        report["recent_files"] = _recent_files(root, since)

    return report


def main():
    ap = argparse.ArgumentParser(description="知识库审计")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--since", help="只列出该日期以来修改过的文件（YYYY-MM-DD）")
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    report = audit(root, since=args.since)

    print("知识库路径：%s" % report["path"])
    print("结构完整：%s" % ("是" if report["structure_ok"] else "否"))
    for k, v in report["counts"].items():
        print("  %s：%d" % (k, v))
    if report["recent_files"]:
        print("\n最近修改文件：")
        for path, mtime in sorted(report["recent_files"], key=lambda x: x[1], reverse=True):
            print("  %s  (%s)" % (path, mtime))
    if report["issues"]:
        print("\n注意：")
        for issue in report["issues"]:
            print("  - %s" % issue)
        sys.exit(1)
    print("\n审计通过")


if __name__ == "__main__":
    main()
