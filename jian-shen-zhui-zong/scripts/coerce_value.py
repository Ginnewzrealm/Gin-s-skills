#!/usr/bin/env python3
"""
Generic value coercion for Feishu Sheets writes.

Reads a JSON request from stdin:
{
  "header_map": {"体脂率": "D", "早餐时间": "W", "有氧": "AO"},
  "column_constraints": {
    "D": {"number_format": "0.00%", "data_validation": null},
    "W": {"number_format": "h:mm", "data_validation": null},
    "AO": {"number_format": "General", "data_validation": {"items": ["有氧"]}}
  },
  "raw_values": {"体脂率": "21.9%", "早餐时间": "08:30", "有氧": "无"}
}

Writes to stdout:
{
  "coerced": {"体脂率": 0.219, "早餐时间": 0.3541666666666667},
  "errors": {"有氧": "INVALID_OPTION: '无' not in ['有氧']"}
}

Rules (no field-specific logic):
1. data_validation.items exists -> value must be in list, verbatim copy on match
2. number_format contains '%' and value ends with '%' -> divide by 100
3. number_format is time-like and value is HH:mm -> Excel time decimal
4. number_format is numeric -> parse float
5. otherwise -> string
"""

import json
import re
import sys
from typing import Any, Dict, Optional, Tuple


def parse_time_to_decimal(value: str) -> Optional[float]:
    """Convert HH:mm or HH:mm:ss to Excel time decimal (fraction of a day)."""
    value = value.strip()
    parts = value.split(":")
    if len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            return h / 24 + m / (24 * 60)
        except ValueError:
            return None
    if len(parts) == 3:
        try:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h / 24 + m / (24 * 60) + s / (24 * 60 * 60)
        except ValueError:
            return None
    return None


def is_time_format(number_format: Optional[str]) -> bool:
    if not number_format:
        return False
    fmt = number_format.lower()
    return bool(re.search(r"h+:mm(:ss)?", fmt))


def is_numeric_format(number_format: Optional[str]) -> bool:
    if not number_format:
        return False
    # Contains digit placeholders or explicit 0
    return bool(re.search(r"[0#]", number_format))


def is_percentage_format(number_format: Optional[str]) -> bool:
    return bool(number_format and "%" in number_format)


def coerce_value(raw_value: Any, number_format: Optional[str], data_validation: Optional[Dict]) -> Tuple[Any, Optional[str]]:
    """Coerce a single raw value. Returns (coerced_value, error_message)."""
    if raw_value is None or raw_value == "":
        return None, None

    items = (data_validation or {}).get("items") if data_validation else None

    # Rule 1: dropdown validation always wins
    if items:
        if raw_value not in items:
            return None, f"INVALID_OPTION: '{raw_value}' not in {items}"
        return raw_value, None

    fmt = number_format or ""

    # Rule 2: percentage format
    if is_percentage_format(fmt):
        if isinstance(raw_value, str) and raw_value.endswith("%"):
            try:
                return float(raw_value.rstrip("%").strip()) / 100, None
            except ValueError:
                return None, f"PERCENT_FORMAT_ERROR: cannot parse '{raw_value}'"
        try:
            return float(raw_value), None
        except (ValueError, TypeError):
            return None, f"PERCENT_FORMAT_ERROR: cannot parse '{raw_value}'"

    # Rule 3: time format
    if is_time_format(fmt):
        if isinstance(raw_value, str):
            decimal = parse_time_to_decimal(raw_value)
            if decimal is not None:
                return decimal, None
        try:
            return float(raw_value), None
        except (ValueError, TypeError):
            return None, f"TIME_FORMAT_ERROR: cannot parse '{raw_value}'"

    # Rule 4: numeric format
    if is_numeric_format(fmt):
        try:
            return float(raw_value), None
        except (ValueError, TypeError):
            return None, f"NUMBER_FORMAT_ERROR: cannot parse '{raw_value}'"

    # Rule 5: default to string
    return str(raw_value), None


def coerce_all(header_map: Dict[str, str],
               column_constraints: Dict[str, Dict],
               raw_values: Dict[str, Any]) -> Dict[str, Any]:
    coerced: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for field_name, raw_value in raw_values.items():
        col = header_map.get(field_name)
        if not col:
            errors[field_name] = f"FIELD_NOT_FOUND: '{field_name}' not in header_map"
            continue

        constraint = column_constraints.get(col) or {}
        number_format = constraint.get("number_format")
        data_validation = constraint.get("data_validation")

        val, err = coerce_value(raw_value, number_format, data_validation)
        if err:
            errors[field_name] = err
        else:
            coerced[field_name] = val

    return {"coerced": coerced, "errors": errors}


def main() -> None:
    request = json.load(sys.stdin)
    header_map = request.get("header_map", {})
    column_constraints = request.get("column_constraints", {})
    raw_values = request.get("raw_values", {})

    result = coerce_all(header_map, column_constraints, raw_values)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
