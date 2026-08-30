#!/usr/bin/env python3
"""Tests for scripts/record_fields_once.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "record_fields_once.py")


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


class TestRecordFieldsOnce(unittest.TestCase):
    def test_daily_record_ready(self):
        payload = {
            "table": "daily_record",
            "date": "2026-08-30",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C", "体脂率": "E"},
            "field_metadata": {
                "晨起体重": {"type": "数字", "options": None, "description": "kg"},
                "体脂率": {"type": "数字", "options": None, "description": "%"},
            },
            "column_constraints": {
                "C": {"number_format": "0.00", "data_validation": None},
                "E": {"number_format": "0.00%", "data_validation": None},
            },
            "raw_values": {"晨起体重": "68.5", "体脂率": "21.9%"},
            "current_row_values": {"晨起体重": "", "体脂率": ""},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["errors"], {})
        self.assertEqual(len(result["write_plan"]["writes"]), 2)
        self.assertEqual(result["write_plan"]["writes"][0]["range"], "C42:C42")
        self.assertEqual(result["write_plan"]["writes"][1]["range"], "E42:E42")

    def test_needs_user_input_when_existing_values(self):
        payload = {
            "table": "daily_record",
            "date": "2026-08-30",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C"},
            "field_metadata": {
                "晨起体重": {"type": "数字", "options": None, "description": "kg"},
            },
            "column_constraints": {
                "C": {"number_format": "0.00", "data_validation": None},
            },
            "raw_values": {"晨起体重": "68.5"},
            "current_row_values": {"晨起体重": 67.5},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "needs_user_input")
        self.assertEqual(len(result["existing_values"]["existing"]), 1)
        self.assertEqual(result["existing_values"]["existing"][0]["field"], "晨起体重")

    def test_invalid_value_returns_error(self):
        payload = {
            "table": "daily_record",
            "date": "2026-08-30",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C"},
            "field_metadata": {
                "晨起体重": {"type": "数字", "options": None, "description": "kg"},
            },
            "column_constraints": {
                "C": {"number_format": "0.00", "data_validation": None},
            },
            "raw_values": {"晨起体重": "不是数字"},
            "current_row_values": {"晨起体重": ""},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "error")
        self.assertIn("晨起体重", result["errors"])

    def test_missing_header_map_fails(self):
        payload = {
            "table": "daily_record",
            "date": "2026-08-30",
            "row": 42,
            "field_metadata": {},
            "column_constraints": {},
            "raw_values": {"晨起体重": "68.5"},
            "current_row_values": {},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "error")
        self.assertIn("HEADER_MAP_MISSING", result["errors"]["_header_map"])

    def test_missing_column_constraints_fails(self):
        payload = {
            "table": "daily_record",
            "date": "2026-08-30",
            "row": 42,
            "header_map": {"日期": "A", "晨起体重": "C"},
            "field_metadata": {
                "晨起体重": {"type": "数字", "options": None, "description": "kg"},
            },
            "raw_values": {"晨起体重": "68.5"},
            "current_row_values": {"晨起体重": ""},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "error")
        self.assertIn("COLUMN_CONSTRAINTS_MISSING", result["errors"]["_column_constraints"])

    def test_user_config_uses_row_map(self):
        payload = {
            "table": "user_config",
            "header_map": {"配置选项": "A", "值": "B"},
            "field_metadata": {
                "当前体重": {"type": "数字", "options": None, "description": "kg"},
            },
            "column_constraints": {
                "B": {"number_format": "0.00", "data_validation": None},
            },
            "raw_values": {"当前体重": "68.5"},
            "current_row_values": {"当前体重": ""},
            "row_map": {"当前体重": 5},
        }
        result = run_script(payload)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["write_plan"]["writes"][0]["range"], "B5:B5")


if __name__ == "__main__":
    unittest.main()
