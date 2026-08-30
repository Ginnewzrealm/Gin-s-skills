#!/usr/bin/env python3
"""stage_validator.py — Progress Checklist 阶段硬闸门。

校验当前 Stage 所需的 named artifacts 是否齐全。不满足时返回明确阻塞原因。

输入 JSON：
{
  "stage": "LOAD_DEFS",
  "artifacts": {
    "write_request": {...},
    "header_map": {...},
    "field_metadata": {...},
    "column_constraints": {...}
  }
}

输出 JSON：
{
  "valid": true,
  "stage": "LOAD_DEFS",
  "next_stage": "VALIDATE",
  "missing_artifacts": [],
  "blockers": []
}
"""
import json
import sys
from typing import Any, Dict, List


STAGE_REQUIREMENTS = {
    "LOAD_DEFS": [
        "write_request",
        "header_map",
        "field_metadata",
        "column_constraints",
    ],
    "VALIDATE": [
        "write_request",
        "header_map",
        "field_metadata",
        "column_constraints",
        "validated_values",
        "coerced_values",
        "existing_values",
    ],
    "WRITE": [
        "write_request",
        "header_map",
        "field_metadata",
        "column_constraints",
        "validated_values",
        "coerced_values",
        "existing_values",
        "write_plan",
    ],
    "REPORT": [
        "write_request",
        "header_map",
        "field_metadata",
        "column_constraints",
        "validated_values",
        "coerced_values",
        "existing_values",
        "write_plan",
        "write_response",
        "verify_result",
    ],
}


def stage_validator(stage: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    required = STAGE_REQUIREMENTS.get(stage)
    if required is None:
        return {
            "valid": False,
            "stage": stage,
            "next_stage": None,
            "missing_artifacts": [],
            "blockers": [f"UNKNOWN_STAGE: 未知阶段「{stage}」"],
        }

    missing: List[str] = [name for name in required if name not in artifacts]
    blockers: List[str] = []
    if missing:
        blockers.append(f"{stage} 阶段缺少必要产出物: {', '.join(missing)}")

    # 对 header_map 额外校验：必须有效
    header_map = artifacts.get("header_map")
    if header_map is not None and not header_map.get("valid"):
        blockers.append(
            f"header_map 无效: {header_map.get('error', '未知错误')}"
        )

    valid = not blockers
    next_stage = None
    if valid:
        stages = list(STAGE_REQUIREMENTS.keys())
        idx = stages.index(stage)
        if idx + 1 < len(stages):
            next_stage = stages[idx + 1]

    return {
        "valid": valid,
        "stage": stage,
        "next_stage": next_stage,
        "missing_artifacts": missing,
        "blockers": blockers,
    }


def main() -> None:
    request = json.load(sys.stdin)
    stage = request.get("stage", "")
    artifacts = request.get("artifacts", {})
    result = stage_validator(stage, artifacts)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
