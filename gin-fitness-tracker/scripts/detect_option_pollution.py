#!/usr/bin/env python3
"""detect_option_pollution.py — 检测写入后下拉选项是否被静默新增。

输入 JSON：
{
  "before": {"E": {"data_validation": {"items": ["🟢正常", "🔴异常"]}}},
  "after": {"E": {"data_validation": {"items": ["🟢正常", "🔴异常", "🟡待定"]}}},
  "header_map": {"大解状态": "E"}
}

输出 JSON：
{
  "polluted": [
    {"field": "大解状态", "col": "E", "old_count": 2, "new_count": 3, "added": ["🟡待定"]}
  ]
}
"""
import json
import sys
from typing import Any, Dict, List


def detect_option_pollution(payload: Dict[str, Any]) -> Dict[str, Any]:
    before = payload.get("before", {})
    after = payload.get("after", {})
    header_map = payload.get("header_map", {})

    # 反转 header_map：col -> field_name
    col_to_field = {col: field for field, col in header_map.items()}

    polluted: List[Dict[str, Any]] = []

    for col, after_constraint in after.items():
        after_items = (after_constraint.get("data_validation") or {}).get("items") or []
        before_items = (before.get(col, {}).get("data_validation") or {}).get("items") or []

        if not after_items:
            continue

        added = [item for item in after_items if item not in before_items]
        if added:
            polluted.append({
                "field": col_to_field.get(col, col),
                "col": col,
                "old_count": len(before_items),
                "new_count": len(after_items),
                "added": added,
            })

    return {"polluted": polluted}


def main() -> None:
    payload = json.load(sys.stdin)
    result = detect_option_pollution(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
