#!/usr/bin/env python3
"""prepare_write_request.py — 根据 header_map 和 column_constraints 构造 +cells-set payload。

这是字段定位的核心硬闸门：Agent 不得自己构造 range，所有 range 必须由本脚本生成。

输入 JSON：
{
  "table": "daily_record",
  "row": 42,
  "header_map": {"日期": "A", "晨起体重": "C", "体脂率": "E"},
  "column_constraints": {
    "C": {"number_format": "0.00", "data_validation": null},
    "E": {"number_format": "0.00%", "data_validation": null}
  },
  "coerced_values": {"晨起体重": 68.5, "体脂率": 0.238}
}

用户配置表（行-based）需额外传入 row_map：
{
  "table": "user_config",
  "header_map": {"配置选项": "A", "值": "B"},
  "column_constraints": {"B": {"number_format": "0.00"}},
  "coerced_values": {"当前体重": 68.5},
  "row_map": {"当前体重": 5}
}

输出 JSON：
{
  "writes": [
    {
      "sheet_name": "每日记录",
      "range": "C42:C42",
      "cells": [[{"value": 68.5, "number_format": "0.00"}]],
      "field_name": "晨起体重"
    }
  ],
  "errors": {}
}
"""
import json
import sys
from typing import Any, Dict, List


SHEET_NAMES = {
    "daily_record": "每日记录",
    "user_config": "用户配置",
}


def prepare_write_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = payload.get("table", "daily_record")
    row = payload.get("row")
    header_map = payload.get("header_map", {})
    column_constraints = payload.get("column_constraints", {})
    coerced_values = payload.get("coerced_values", {})
    row_map = payload.get("row_map", {})

    sheet_name = SHEET_NAMES.get(table, table)

    writes: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}

    for field_name, value in coerced_values.items():
        if table == "user_config":
            field_row = row_map.get(field_name)
            if field_row is None:
                errors[field_name] = f"ROW_MAP_MISSING: 用户配置表字段「{field_name}」缺少对应行号"
                continue
            target_row = field_row
            # 用户配置表按行存储，值写在「值」列
            col = header_map.get("值")
            if not col:
                errors[field_name] = "CONFIG_ERROR: 用户配置表表头缺少「值」列"
                continue
        else:
            col = header_map.get(field_name)
            if not col:
                errors[field_name] = f"FIELD_NOT_FOUND: '{field_name}' 不在当前表头行中"
                continue
            if row is None:
                errors[field_name] = "ROW_MISSING: daily_record 缺少目标行号"
                continue
            target_row = row

        constraint = column_constraints.get(col) or {}
        number_format = constraint.get("number_format") or "General"

        writes.append({
            "sheet_name": sheet_name,
            "range": f"{col}{target_row}:{col}{target_row}",
            "cells": [[{"value": value, "number_format": number_format}]],
            "field_name": field_name,
        })

    return {"writes": writes, "errors": errors}


def main() -> None:
    payload = json.load(sys.stdin)
    result = prepare_write_request(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
