#!/usr/bin/env python3
"""
简单的 assertion checker for gin-question evals.
用法: python3 grade.py <eval-dir>
"""

import json
import os
import sys
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_file_exists(outputs_dir, files):
    results = []
    for fname in files:
        exists = (outputs_dir / fname).exists()
        results.append({
            "text": f"{fname} 存在",
            "passed": exists,
            "evidence": f"{'找到' if exists else '未找到'} {fname}"
        })
    return results

def check_json_schema(outputs_dir, file):
    path = outputs_dir / file
    try:
        data = load_json(path)
        required = ["topic", "generated_at", "exit_reason", "retrieval_rounds", "problems", "pending_validation"]
        missing = [k for k in required if k not in data]
        passed = len(missing) == 0
        return [{
            "text": f"{file} 包含必要字段",
            "passed": passed,
            "evidence": f"缺失字段: {missing}" if missing else "所有必要字段都存在"
        }]
    except Exception as e:
        return [{
            "text": f"{file} 是有效 JSON",
            "passed": False,
            "evidence": str(e)
        }]

def check_min_array_length(outputs_dir, file, path, min_len):
    try:
        data = load_json(outputs_dir / file)
        for key in path.split('.'):
            data = data[key]
        passed = len(data) >= min_len
        return [{
            "text": f"{path} 长度 ≥ {min_len}",
            "passed": passed,
            "evidence": f"实际长度: {len(data)}"
        }]
    except Exception as e:
        return [{
            "text": f"{path} 长度 ≥ {min_len}",
            "passed": False,
            "evidence": str(e)
        }]

def check_all_have_field(outputs_dir, file, path, field):
    try:
        data = load_json(outputs_dir / file)
        for key in path.split('.'):
            data = data[key]
        bad = [i for i, item in enumerate(data) if not item.get(field)]
        passed = len(bad) == 0
        return [{
            "text": f"每条 {path} 都有 {field}",
            "passed": passed,
            "evidence": f"缺失项索引: {bad}" if bad else f"共 {len(data)} 条，全部有 {field}"
        }]
    except Exception as e:
        return [{
            "text": f"每条 {path} 都有 {field}",
            "passed": False,
            "evidence": str(e)
        }]

def check_min_unique_values(outputs_dir, file, path, field, min_val):
    try:
        data = load_json(outputs_dir / file)
        for key in path.split('.'):
            data = data[key]
        values = set(item.get(field) for item in data if item.get(field))
        passed = len(values) >= min_val
        return [{
            "text": f"{field} 唯一值数量 ≥ {min_val}",
            "passed": passed,
            "evidence": f"唯一值: {sorted(values)}"
        }]
    except Exception as e:
        return [{
            "text": f"{field} 唯一值数量 ≥ {min_val}",
            "passed": False,
            "evidence": str(e)
        }]

def check_has_fields(outputs_dir, file, fields):
    try:
        data = load_json(outputs_dir / file)
        missing = [k for k in fields if k not in data]
        passed = len(missing) == 0
        return [{
            "text": f"{file} 包含字段 {fields}",
            "passed": passed,
            "evidence": f"缺失字段: {missing}" if missing else "所有字段都存在"
        }]
    except Exception as e:
        return [{
            "text": f"{file} 包含必要字段",
            "passed": False,
            "evidence": str(e)
        }]

def main():
    eval_dir = Path(sys.argv[1])
    metadata_path = eval_dir / "eval_metadata.json"
    outputs_dir = eval_dir / "outputs"

    if not metadata_path.exists():
        print(f"未找到 {metadata_path}")
        sys.exit(1)

    metadata = load_json(metadata_path)
    results = []

    for assertion in metadata.get("assertions", []):
        check_type = assertion.get("check")
        if check_type == "file_exists":
            results.extend(check_file_exists(outputs_dir, assertion["files"]))
        elif check_type == "json_schema":
            results.extend(check_json_schema(outputs_dir, assertion["file"]))
        elif check_type == "min_array_length":
            results.extend(check_min_array_length(outputs_dir, assertion["file"], assertion["path"], assertion["min"]))
        elif check_type == "all_have_field":
            results.extend(check_all_have_field(outputs_dir, assertion["file"], assertion["path"], assertion["field"]))
        elif check_type == "min_unique_values":
            results.extend(check_min_unique_values(outputs_dir, assertion["file"], assertion["path"], assertion["field"], assertion["min"]))
        elif check_type == "has_fields":
            results.extend(check_has_fields(outputs_dir, assertion["file"], assertion["fields"]))

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    grading = {
        "eval_id": metadata.get("eval_id"),
        "eval_name": metadata.get("eval_name"),
        "pass_rate": passed / total if total else 0,
        "passed": passed,
        "total": total,
        "expectations": results
    }

    out_path = eval_dir / "grading.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(grading, f, ensure_ascii=False, indent=2)

    print(f"评分完成: {passed}/{total} 通过，保存到 {out_path}")

if __name__ == "__main__":
    main()
