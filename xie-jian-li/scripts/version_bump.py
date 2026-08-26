#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""version_bump.py — 技能版本号自动递增 + 更新日志自动记录。

每次修改本技能后运行：
    python3 scripts/version_bump.py --type patch --note "修复技能区排版"
    python3 scripts/version_bump.py --type minor --note "新增高管简历功能"
    python3 scripts/version_bump.py --type major --note "重构路由架构"

自动完成：
1. 递增 SKILL.md 顶部「当前版本：vX.Y.Z（日期）」的版本号与日期
2. 在「更新日志.md」顶部追加一条记录（日期 + 版本号 + 变更内容）

版本号规则：major = 架构/流程变更；minor = 新功能/新字段/新脚本；patch = 修复与优化
"""
import argparse
import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(ROOT, "SKILL.md")
CHANGELOG = os.path.join(ROOT, "更新日志.md")

VER_RE = re.compile(r"(当前版本：v)(\d+)\.(\d+)\.(\d+)(（\d{4}-\d{2}-\d{2}）)")
TYPES = ("major", "minor", "patch")


def main():
    ap = argparse.ArgumentParser(description="技能版本号自动递增 + 更新日志记录")
    ap.add_argument("--type", required=True, choices=TYPES, help="major/minor/patch")
    ap.add_argument("--note", required=True, help="变更内容摘要（一句话）")
    args = ap.parse_args()

    with open(SKILL_MD, encoding="utf-8") as f:
        skill = f.read()
    m = VER_RE.search(skill)
    if not m:
        print("[失败] SKILL.md 中未找到「当前版本：vX.Y.Z（日期）」版本行")
        sys.exit(2)
    major, minor, patch = int(m.group(2)), int(m.group(3)), int(m.group(4))
    old = "v%d.%d.%d" % (major, minor, patch)
    if args.type == "major":
        major, minor, patch = major + 1, 0, 0
    elif args.type == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = "v%d.%d.%d" % (major, minor, patch)
    today = datetime.date.today().isoformat()

    skill = VER_RE.sub(lambda _: "当前版本：%s（%s）" % (new, today), skill, count=1)
    with open(SKILL_MD, "w", encoding="utf-8") as f:
        f.write(skill)

    entry = "## %s · %s\n\n- %s\n\n" % (new, today, args.note)
    if os.path.exists(CHANGELOG):
        with open(CHANGELOG, encoding="utf-8") as f:
            log = f.read()
        if log.startswith("# 更新日志"):
            head, _, rest = log.partition("\n")
            log = head + "\n\n" + entry + rest.lstrip("\n")
        else:
            log = "# 更新日志\n\n" + entry + log
    else:
        log = "# 更新日志\n\n" + entry
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(log)

    print("[完成] %s → %s（%s）" % (old, new, today))
    print("[完成] 更新日志已追加：%s" % args.note)


if __name__ == "__main__":
    main()
