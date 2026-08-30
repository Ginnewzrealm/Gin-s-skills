#!/usr/bin/env python3
"""build_header_map.py — 从表头行建立字段名→列字母映射。

输入 JSON（两种形式）：
1. lark read_header 原始输出：
   {
     "annotated_csv": [["日期", "晨起体重", "", "体脂率"]],
     "col_indices": ["A", "B", "C", "D"]
   }
2. 纯表头数组：
   {"headers": ["日期", "晨起体重", "", "体脂率"]}

输出 JSON：
{
  "header_map": {"日期": "A", "晨起体重": "B", "体脂率": "D"},
  "empty_cols": ["C"],
  "duplicate_fields": [],
  "valid": true
}
"""
import json
import sys
from typing import Any, Dict, List, Tuple


def _col_letter(index: int) -> str:
    """把 0-based 列索引转换为 A, B, ... AA, AB 等列字母。"""
    index += 1
    letters = []
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))


def build_header_map(payload: Dict[str, Any]) -> Dict[str, Any]:
    annotated_csv = payload.get("annotated_csv")
    col_indices = payload.get("col_indices")
    headers = payload.get("headers")

    if annotated_csv is not None:
        if not annotated_csv or not annotated_csv[0]:
            return {
                "header_map": {},
                "empty_cols": [],
                "duplicate_fields": [],
                "valid": False,
                "error": "EMPTY_HEADER: 表头行为空",
            }
        headers = annotated_csv[0]
    elif headers is None:
        return {
            "header_map": {},
            "empty_cols": [],
            "duplicate_fields": [],
            "valid": False,
            "error": "INPUT_ERROR: 必须提供 annotated_csv 或 headers",
        }

    if col_indices is None:
        col_indices = [_col_letter(i) for i in range(len(headers))]

    if len(headers) != len(col_indices):
        return {
            "header_map": {},
            "empty_cols": [],
            "duplicate_fields": [],
            "valid": False,
            "error": "LENGTH_MISMATCH: headers 与 col_indices 长度不一致",
        }

    header_map: Dict[str, str] = {}
    empty_cols: List[str] = []
    duplicate_fields: List[Dict[str, Any]] = []

    for field_name, col in zip(headers, col_indices):
        name = str(field_name).strip()
        if not name:
            empty_cols.append(col)
            continue

        if name in header_map:
            existing = [header_map[name]]
            # 收集所有出现位置
            for fn, c in zip(headers, col_indices):
                if fn == name and c != existing[0] and c not in existing:
                    existing.append(c)
            existing.sort()
            duplicate_fields.append({"field": name, "cols": existing})
            continue

        header_map[name] = col

    if duplicate_fields:
        dup = duplicate_fields[0]
        return {
            "header_map": header_map,
            "empty_cols": empty_cols,
            "duplicate_fields": duplicate_fields,
            "valid": False,
            "error": f"DUPLICATE_HEADER: 字段「{dup['field']}」出现在多列: {', '.join(dup['cols'])}",
        }

    return {
        "header_map": header_map,
        "empty_cols": empty_cols,
        "duplicate_fields": [],
        "valid": True,
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = build_header_map(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
