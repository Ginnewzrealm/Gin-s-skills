#!/usr/bin/env python3
"""build_column_constraints.py — 把 lark +cells-get 原始输出转换为标准列约束。

输入 JSON：
{
  "cells": [[
    {"cell_styles": {"number_format": "0.00%"}, "value": "24.00%"},
    {"cell_styles": {"number_format": "h:mm"}, "value": "0:00"},
    {"data_validation": {"items": ["🟢有力"]}, "value": null}
  ]],
  "col_indices": ["C", "D", "E"]
}

输出 JSON：
{
  "column_constraints": {
    "C": {"number_format": "0.00%", "data_validation": null},
    "D": {"number_format": "h:mm", "data_validation": null},
    "E": {"number_format": "General", "data_validation": {"items": ["🟢有力"]}}
  }
}
"""
import json
import sys
from typing import Any, Dict, List, Optional


def _col_letter(index: int) -> str:
    index += 1
    letters = []
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))


def build_column_constraints(payload: Dict[str, Any]) -> Dict[str, Any]:
    cells = payload.get("cells")
    col_indices = payload.get("col_indices")

    if not cells or not cells[0]:
        return {
            "column_constraints": {},
            "error": "EMPTY_CELLS: cells 为空",
        }

    row = cells[0]
    if col_indices is None:
        col_indices = [_col_letter(i) for i in range(len(row))]

    if len(row) != len(col_indices):
        return {
            "column_constraints": {},
            "error": "LENGTH_MISMATCH: cells 与 col_indices 长度不一致",
        }

    constraints: Dict[str, Dict[str, Any]] = {}
    for cell, col in zip(row, col_indices):
        number_format = "General"
        cell_styles = cell.get("cell_styles") or {}
        if isinstance(cell_styles, dict):
            number_format = cell_styles.get("number_format") or "General"

        data_validation = cell.get("data_validation")
        if data_validation:
            # Normalize to canonical shape
            data_validation = {"items": data_validation.get("items", [])} if data_validation.get("items") else None

        constraints[col] = {
            "number_format": number_format,
            "data_validation": data_validation,
        }

    return {"column_constraints": constraints}


def main() -> None:
    payload = json.load(sys.stdin)
    result = build_column_constraints(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
