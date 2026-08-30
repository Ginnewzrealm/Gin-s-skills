#!/usr/bin/env python3
"""Tests for scripts/check_existing_values.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "check_existing_values.py")


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


class TestCheckExistingValues(unittest.TestCase):
    def test_detects_existing_and_blank(self):
        payload = {
            "write_plan": {
                "writes": [
                    {"field_name": "晨起体重"},
                    {"field_name": "体脂率"},
                    {"field_name": "大解状态"},
                ]
            },
            "current_row_values": {
                "晨起体重": 68.5,
                "体脂率": "",
                "大解状态": None,
            },
        }
        result = run_script(payload)
        self.assertEqual(len(result["existing"]), 1)
        self.assertEqual(result["existing"][0]["field"], "晨起体重")
        self.assertEqual(result["blank"], ["体脂率", "大解状态"])


if __name__ == "__main__":
    unittest.main()
