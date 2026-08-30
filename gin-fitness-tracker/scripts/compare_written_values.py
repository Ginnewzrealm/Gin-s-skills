#!/usr/bin/env python3
"""compare_written_values.py — 对比写入值与回读值。

输入 JSON：
{
  "write_plan": {"writes": [{"field_name": "晨起体重", "cells": [[{"value": 68.5}]]}]},
  "verify_row_values": {"晨起体重": 68.5}
}

输出 JSON：
{
  "matched": ["晨起体重"],
  "mismatched": [{"field": "...", "expected": 68.5, "actual": 69.0}],
  "missing": ["..."]
}
"""
import json
import sys
from typing import Any, Dict, List


def _extract_expected(write: Dict[str, Any]) -> Any:
    cells = write.get("cells") or [[]]
    if cells and cells[0]:
        return cells[0][0].get("value")
    return None


def compare_written_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    writes = payload.get("write_plan", {}).get("writes", [])
    actual = payload.get("verify_row_values", {})

    matched: List[str] = []
    mismatched: List[Dict[str, Any]] = []
    missing: List[str] = []

    for write in writes:
        field = write.get("field_name")
        expected = _extract_expected(write)
        if field not in actual:
            missing.append(field)
            continue
        if actual[field] == expected:
            matched.append(field)
        else:
            mismatched.append({
                "field": field,
                "expected": expected,
                "actual": actual[field],
            })

    return {"matched": matched, "mismatched": mismatched, "missing": missing}


def main() -> None:
    payload = json.load(sys.stdin)
    result = compare_written_values(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
