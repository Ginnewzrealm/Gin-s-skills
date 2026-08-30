#!/usr/bin/env python3
"""record_fields_once.py — 一键完成字段校验、转换、写入计划构造和已有值检查。

目标：让 Agent 在拿到用户数据后，只需调用一次本脚本，就能完成从 raw_values 到
write_plan.json 的全部预处理，避免直接拼 lark-cli 或跳过校验步骤。

输入 JSON：
{
  "table": "daily_record",
  "date": "2026-08-30",
  "row": 42,
  "header_map": {"日期": "A", "晨起体重": "C", "体脂率": "E"},
  "field_metadata": {
    "晨起体重": {"type": "数字", "options": null, "description": "..."},
    "体脂率": {"type": "数字", "options": null, "description": "..."}
  },
  "column_constraints": {
    "C": {"number_format": "0.00", "data_validation": null},
    "E": {"number_format": "0.00%", "data_validation": null}
  },
  "raw_values": {"晨起体重": "68.5", "体脂率": "21.9%"},
  "current_row_values": {"晨起体重": "", "体脂率": 0.22},
  "row_map": {},
  "context": {"channel_type": "group"}
}

输出 JSON：
{
  "status": "ready" | "needs_user_input" | "error",
  "table": "daily_record",
  "date": "2026-08-30",
  "write_plan": {
    "writes": [
      {"sheet_name": "每日记录", "range": "C42:C42", "cells": [[{"value": 68.5, "number_format": "0.00"}]], "field_name": "晨起体重"}
    ],
    "errors": {}
  },
  "validated_values": {"晨起体重": 68.5},
  "coerced_values": {"晨起体重": 68.5},
  "existing_values": {"existing": [], "blank": ["晨起体重"]},
  "errors": {},
  "messages": []
}
"""
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def _run_script(script_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """调用同级目录下的另一个脚本，返回其 JSON 输出。"""
    script_path = os.path.join(REPO_ROOT, script_name)
    proc = subprocess.run(
        [sys.executable, script_path],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8")
        raise RuntimeError(f"{script_name} failed: {stderr}")
    return json.loads(proc.stdout.decode("utf-8"))


def record_fields_once(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = payload.get("table", "daily_record")
    date = payload.get("date")
    row = payload.get("row")
    header_map = payload.get("header_map", {})
    field_metadata = payload.get("field_metadata", {})
    column_constraints = payload.get("column_constraints", {})
    raw_values = payload.get("raw_values", {})
    current_row_values = payload.get("current_row_values", {})
    row_map = payload.get("row_map", {})

    messages: List[str] = []

    # 0. 前置硬闸门：必须有 header_map 和 column_constraints
    if not header_map:
        return {
            "status": "error",
            "table": table,
            "date": date,
            "write_plan": {"writes": [], "errors": {}},
            "validated_values": {},
            "coerced_values": {},
            "existing_values": {"existing": [], "blank": []},
            "errors": {"_header_map": "HEADER_MAP_MISSING: 必须提供有效的 header_map"},
            "messages": ["缺少字段→列映射，无法继续。请先读取表头并运行 build_header_map.py。"],
        }

    if not column_constraints:
        return {
            "status": "error",
            "table": table,
            "date": date,
            "write_plan": {"writes": [], "errors": {}},
            "validated_values": {},
            "coerced_values": {},
            "existing_values": {"existing": [], "blank": []},
            "errors": {"_column_constraints": "COLUMN_CONSTRAINTS_MISSING: 必须提供 column_constraints"},
            "messages": ["缺少真实列约束，无法继续。请先调用 lark-sheets 的 read_column_formats。"],
        }

    # 1. 按字段元数据校验类型与选项
    validated_result = _run_script("validate_field_metadata.py", {
        "field_metadata": field_metadata,
        "raw_values": raw_values,
    })
    validated_values = validated_result.get("valid", {})
    validation_errors = validated_result.get("errors", {})

    if validation_errors:
        messages.append(f"字段元数据校验未通过：{', '.join(validation_errors.keys())}")

    # 2. 按真实列约束转换值形态
    # user_config 是行-based：所有字段值都写入「值」列，因此构造临时 header_map 做转换
    if table == "user_config":
        value_col = header_map.get("值")
        coerce_header_map = {field: value_col for field in validated_values.keys() if value_col}
    else:
        coerce_header_map = header_map

    coerce_result = _run_script("coerce_value.py", {
        "header_map": coerce_header_map,
        "column_constraints": column_constraints,
        "raw_values": validated_values,
    })
    coerced_values = coerce_result.get("coerced", {})
    coerce_errors = coerce_result.get("errors", {})

    if coerce_errors:
        messages.append(f"值转换未通过：{', '.join(coerce_errors.keys())}")

    # 合并前两步错误
    combined_errors: Dict[str, str] = {}
    combined_errors.update(validation_errors)
    combined_errors.update(coerce_errors)

    # 只有成功转换的值才进入写入计划
    values_to_write = {k: v for k, v in coerced_values.items() if k not in combined_errors}

    if not values_to_write:
        return {
            "status": "error",
            "table": table,
            "date": date,
            "write_plan": {"writes": [], "errors": {}},
            "validated_values": validated_values,
            "coerced_values": coerced_values,
            "existing_values": {"existing": [], "blank": []},
            "errors": combined_errors,
            "messages": messages or ["没有可写入的字段，请检查输入值。"],
        }

    # 3. 构造写入计划
    prepare_payload = {
        "table": table,
        "row": row,
        "header_map": header_map,
        "column_constraints": column_constraints,
        "coerced_values": values_to_write,
    }
    if table == "user_config":
        prepare_payload["row_map"] = row_map

    write_plan = _run_script("prepare_write_request.py", prepare_payload)

    # 4. 检查已有值
    existing_result = _run_script("check_existing_values.py", {
        "write_plan": write_plan,
        "current_row_values": current_row_values,
    })

    existing = existing_result.get("existing", [])
    if existing:
        messages.append(
            f"以下字段已有值，需要用户确认是否覆盖：{', '.join(str(item['field']) for item in existing)}"
        )

    # 决定状态
    if existing:
        status = "needs_user_input"
    elif write_plan.get("errors") or combined_errors:
        status = "error"
    else:
        status = "ready"

    # 把 prepare_write_request 的错误也合并进来
    for field, err in write_plan.get("errors", {}).items():
        if field not in combined_errors:
            combined_errors[field] = err

    if combined_errors and status == "ready":
        status = "error"

    return {
        "status": status,
        "table": table,
        "date": date,
        "write_plan": write_plan,
        "validated_values": validated_values,
        "coerced_values": coerced_values,
        "existing_values": existing_result,
        "errors": combined_errors,
        "messages": messages,
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = record_fields_once(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
