#!/usr/bin/env python3
"""Tests for scripts/prepare_write_request.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "prepare_write_request.py")


def run_script(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(f"script failed: {proc.stderr.decode('utf-8')}")
    return json.loads(proc.stdout.decode("utf-8"))


class TestPrepareWriteRequest(unittest.TestCase):
    def test_daily_record_maps_correct_columns_and_number_format(self):
        payload = {
            "table": "daily_record",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C", "体脂率": "E"},
            "column_constraints": {
                "C": {"number_format": "0.00", "data_validation": None},
                "E": {"number_format": "0.00%", "data_validation": None},
            },
            "coerced_values": {"晨起体重": 68.5, "体脂率": 0.238},
        }
        result = run_script(payload)
        self.assertEqual(result["errors"], {})
        self.assertEqual(len(result["writes"]), 2)

        write0 = result["writes"][0]
        self.assertEqual(write0["field_name"], "晨起体重")
        self.assertEqual(write0["range"], "C42:C42")
        self.assertEqual(write0["cells"][0][0], {"value": 68.5, "number_format": "0.00"})

        write1 = result["writes"][1]
        self.assertEqual(write1["field_name"], "体脂率")
        self.assertEqual(write1["range"], "E42:E42")
        self.assertEqual(write1["cells"][0][0], {"value": 0.238, "number_format": "0.00%"})

    def test_missing_field_returns_field_not_found(self):
        payload = {
            "table": "daily_record",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C"},
            "column_constraints": {
                "C": {"number_format": "0.00", "data_validation": None},
            },
            "coerced_values": {"体脂率": 0.238},
        }
        result = run_script(payload)
        self.assertEqual(result["writes"], [])
        self.assertIn("FIELD_NOT_FOUND", result["errors"]["体脂率"])

    def test_user_config_uses_row_map(self):
        payload = {
            "table": "user_config",
            "header_map": {"配置选项": "A", "值": "B", "更新时间": "C"},
            "column_constraints": {
                "B": {"number_format": "0.00", "data_validation": None},
            },
            "coerced_values": {"当前体重": 68.5},
            "row_map": {"当前体重": 5},
        }
        result = run_script(payload)
        self.assertEqual(result["errors"], {})
        self.assertEqual(len(result["writes"]), 1)
        self.assertEqual(result["writes"][0]["range"], "B5:B5")
        self.assertEqual(result["writes"][0]["sheet_name"], "用户配置")

    def test_user_config_missing_row_map_fails(self):
        payload = {
            "table": "user_config",
            "header_map": {"配置选项": "A", "值": "B"},
            "column_constraints": {
                "B": {"number_format": "0.00", "data_validation": None},
            },
            "coerced_values": {"当前体重": 68.5},
        }
        result = run_script(payload)
        self.assertEqual(result["writes"], [])
        self.assertIn("ROW_MAP_MISSING", result["errors"]["当前体重"])


if __name__ == "__main__":
    unittest.main()
