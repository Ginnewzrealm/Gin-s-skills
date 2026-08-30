#!/usr/bin/env python3
"""Tests for scripts/build_header_map.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "build_header_map.py")


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


class TestBuildHeaderMap(unittest.TestCase):
    def test_normal_mapping(self):
        payload = {
            "annotated_csv": [["日期", "周编号", "晨起体重", "体脂率"]],
            "col_indices": ["A", "B", "C", "D"],
        }
        result = run_script(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["header_map"],
            {"日期": "A", "周编号": "B", "晨起体重": "C", "体脂率": "D"},
        )
        self.assertEqual(result["empty_cols"], [])
        self.assertEqual(result["duplicate_fields"], [])

    def test_empty_columns_do_not_shift_mapping(self):
        """Regression test for the positional-inference bug."""
        payload = {
            "annotated_csv": [
                [
                    "日期",
                    "周编号",
                    "晨起体重",
                    "",
                    "体脂率",
                    "BMI",
                    "",
                    "腰围",
                ]
            ],
            "col_indices": ["A", "B", "C", "D", "E", "F", "G", "H"],
        }
        result = run_script(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["header_map"]["晨起体重"], "C")
        self.assertEqual(result["header_map"]["体脂率"], "E")
        self.assertEqual(result["header_map"]["腰围"], "H")
        self.assertEqual(result["empty_cols"], ["D", "G"])

    def test_duplicate_fields_are_rejected(self):
        payload = {
            "annotated_csv": [["日期", "晨起体重", "体脂率", "晨起体重"]],
            "col_indices": ["A", "B", "C", "D"],
        }
        result = run_script(payload)
        self.assertFalse(result["valid"])
        self.assertIn("DUPLICATE_HEADER", result["error"])
        self.assertEqual(
            result["duplicate_fields"],
            [{"field": "晨起体重", "cols": ["B", "D"]}],
        )

    def test_plain_header_array_is_accepted(self):
        payload = {"headers": ["日期", "晨起体重", "", "体脂率"]}
        result = run_script(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["header_map"]["体脂率"], "D")


if __name__ == "__main__":
    unittest.main()
