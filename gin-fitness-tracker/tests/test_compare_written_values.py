#!/usr/bin/env python3
"""Tests for scripts/compare_written_values.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "compare_written_values.py")


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


class TestCompareWrittenValues(unittest.TestCase):
    def test_all_match(self):
        payload = {
            "write_plan": {
                "writes": [
                    {"field_name": "晨起体重", "cells": [[{"value": 68.5}]]},
                ]
            },
            "verify_row_values": {"晨起体重": 68.5},
        }
        result = run_script(payload)
        self.assertEqual(result["mismatched"], [])
        self.assertEqual(result["matched"], ["晨起体重"])

    def test_detects_mismatch(self):
        payload = {
            "write_plan": {
                "writes": [
                    {"field_name": "晨起体重", "cells": [[{"value": 68.5}]]},
                ]
            },
            "verify_row_values": {"晨起体重": 69.0},
        }
        result = run_script(payload)
        self.assertEqual(result["matched"], [])
        self.assertEqual(len(result["mismatched"]), 1)
        self.assertEqual(result["mismatched"][0]["field"], "晨起体重")


if __name__ == "__main__":
    unittest.main()
