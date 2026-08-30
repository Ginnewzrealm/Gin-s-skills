#!/usr/bin/env python3
"""Tests for scripts/detect_option_pollution.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "detect_option_pollution.py")


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


class TestDetectOptionPollution(unittest.TestCase):
    def test_no_pollution(self):
        payload = {
            "before": {
                "E": {"data_validation": {"items": ["🟢正常", "🔴异常"]}},
            },
            "after": {
                "E": {"data_validation": {"items": ["🟢正常", "🔴异常"]}},
            },
            "header_map": {"大解状态": "E"},
        }
        result = run_script(payload)
        self.assertEqual(result["polluted"], [])

    def test_detects_added_option(self):
        payload = {
            "before": {
                "E": {"data_validation": {"items": ["🟢正常", "🔴异常"]}},
            },
            "after": {
                "E": {"data_validation": {"items": ["🟢正常", "🔴异常", "🟡待定"]}},
            },
            "header_map": {"大解状态": "E"},
        }
        result = run_script(payload)
        self.assertEqual(len(result["polluted"]), 1)
        self.assertEqual(result["polluted"][0]["field"], "大解状态")
        self.assertEqual(result["polluted"][0]["added"], ["🟡待定"])


if __name__ == "__main__":
    unittest.main()
