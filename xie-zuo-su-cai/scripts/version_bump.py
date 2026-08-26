#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本号与 CHANGELOG 更新。"""

import argparse
import os
import re
from datetime import date


def _bump_version(current, bump_type):
    parts = [int(x) for x in current.split(".")]
    if len(parts) != 3:
        raise ValueError("版本号必须是 x.y.z 格式")
    major, minor, patch = parts
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError("bump_type 必须是 major/minor/patch")
    return f"{major}.{minor}.{patch}"


def _latest_version(changelog_path):
    if not os.path.exists(changelog_path):
        return "0.0.0"
    with open(changelog_path, encoding="utf-8") as f:
        content = f.read()
    versions = re.findall(r"v(\d+\.\d+\.\d+)", content)
    if not versions:
        return "0.0.0"
    return versions[0]


def bump(changelog_path, bump_type, note):
    current = _latest_version(changelog_path)
    new_ver = _bump_version(current, bump_type)

    today = date.today().strftime("%Y-%m-%d")
    entry = f"## {today} · v{new_ver} · {bump_type}\n- {note}\n\n"
    if os.path.exists(changelog_path):
        with open(changelog_path, encoding="utf-8") as f:
            old = f.read()
    else:
        old = "# CHANGELOG\n\n"
    new_content = old.replace("# CHANGELOG\n", "# CHANGELOG\n" + entry, 1)
    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[完成] 版本已更新：{current} → {new_ver}")


def main():
    ap = argparse.ArgumentParser(description="更新技能版本号与 CHANGELOG")
    ap.add_argument("--type", choices=["major", "minor", "patch"], required=True)
    ap.add_argument("--note", required=True, help="变更摘要")
    args = ap.parse_args()
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bump(
        os.path.join(skill_dir, "CHANGELOG.md"),
        args.type,
        args.note,
    )


if __name__ == "__main__":
    main()
