#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 plan-writeback-log.json 异常结构。"""

import json
import os
import sys


def repair_log(path):
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        print(f"[提示] 文件不存在，创建规范结构：{path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {"schema_version": "1.0", "records": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    with open(path, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[错误] JSON 解析失败：{e}")
            sys.exit(1)

    if isinstance(raw, list):
        print(f"[修复] 文件是旧版数组，重建为规范结构：{path}")
        data = {"schema_version": "1.0", "records": raw}
    elif isinstance(raw, dict) and "records" in raw:
        print(f"[完成] 文件结构正常：{path}")
        data = raw
        data.setdefault("schema_version", "1.0")
    else:
        print(f"[修复] 文件结构异常，重建为规范结构：{path}")
        data = {"schema_version": "1.0", "records": []}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print("[错误] 请提供 plan-writeback-log.json 的完整路径")
        print("示例：")
        print("  python3 scripts/repair_writeback_log.py ~/Documents/健身知识库/.xunji-writeback/plan-writeback-log.json")
        sys.exit(1)

    data = repair_log(path)
    print(f"[结果] records 数量：{len(data.get('records', []))}")


if __name__ == "__main__":
    main()
