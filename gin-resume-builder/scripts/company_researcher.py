#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""company_researcher.py — 公司研究缓存读写。

用法:
    python3 company_researcher.py --company "示例科技" --query
    python3 company_researcher.py --company "示例科技" --write cache.json
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path


def normalize_name(name):
    """标准化公司名用于文件名。"""
    name = str(name).strip()
    suffixes = ["有限公司", "有限责任公司", "股份公司", "股份有限公司", "集团", "科技", "技术"]
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            stripped = re.sub(r"\s*" + re.escape(suffix) + r"\s*$", "", name)
            if stripped != name:
                name = stripped
                changed = True
                break
    name = re.sub(r"[^一-龥a-zA-Z0-9]+", "-", name).strip("-")
    return name.lower() or "unknown"


def cache_path(root, company):
    return Path(root) / "company_research" / (normalize_name(company) + ".json")


def load_cache(root, company, ttl_days=30):
    path = cache_path(root, company)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    fetched = data.get("fetched_date", "")
    try:
        fetched_date = date.fromisoformat(fetched)
    except ValueError:
        return None
    if date.today() - fetched_date > timedelta(days=ttl_days):
        return None
    return data


def save_cache(root, company, data):
    path = cache_path(root, company)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["company"] = company
    data["fetched_date"] = date.today().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main():
    ap = argparse.ArgumentParser(description="公司研究缓存")
    ap.add_argument("--company", required=True, help="公司名称")
    ap.add_argument("--root", default=".", help="项目根目录")
    ap.add_argument("--query", action="store_true", help="查询缓存")
    ap.add_argument("--write", help="从 JSON 文件写入缓存")
    args = ap.parse_args()

    if args.query:
        cached = load_cache(args.root, args.company)
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"cached": False}, ensure_ascii=False))
    elif args.write:
        with open(args.write, encoding="utf-8") as f:
            data = json.load(f)
        path = save_cache(args.root, args.company, data)
        print("[完成] 缓存已保存：%s" % path)


if __name__ == "__main__":
    main()
