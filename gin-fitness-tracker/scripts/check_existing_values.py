#!/usr/bin/env python3
"""check_existing_values.py — 检查目标字段是否已有值，防止静默覆盖。

输入 JSON：
{
  "write_plan": {"writes": [{"field_name": "晨起体重"}, ...]},
  "current_row_values": {"晨起体重": 68.5, "体脂率": ""}
}

输出 JSON：
{
  "existing": [{"field": "晨起体重", "current_value": 68.5}],
  "blank": ["体脂率"]
}
"""
import json
import sys
from typing import Any, Dict, List


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def check_existing_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    writes = payload.get("write_plan", {}).get("writes", [])
    current = payload.get("current_row_values", {})

    existing: List[Dict[str, Any]] = []
    blank: List[str] = []

    for write in writes:
        field = write.get("field_name")
        if not field:
            continue
        current_value = current.get(field)
        if _is_blank(current_value):
            blank.append(field)
        else:
            existing.append({"field": field, "current_value": current_value})

    return {"existing": existing, "blank": blank}


def main() -> None:
    payload = json.load(sys.stdin)
    result = check_existing_values(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
