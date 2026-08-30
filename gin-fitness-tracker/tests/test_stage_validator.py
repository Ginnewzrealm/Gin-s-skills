#!/usr/bin/env python3
"""Tests for scripts/stage_validator.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "stage_validator.py")


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


class TestStageValidator(unittest.TestCase):
    def test_load_defs_valid(self):
        payload = {
            "stage": "LOAD_DEFS",
            "artifacts": {
                "write_request": {"table": "daily_record"},
                "header_map": {"valid": True},
                "field_metadata": {},
                "column_constraints": {},
            },
        }
        result = run_script(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["next_stage"], "VALIDATE")

    def test_load_defs_missing_header_map(self):
        payload = {
            "stage": "LOAD_DEFS",
            "artifacts": {
                "write_request": {"table": "daily_record"},
                "field_metadata": {},
                "column_constraints": {},
            },
        }
        result = run_script(payload)
        self.assertFalse(result["valid"])
        self.assertIn("header_map", result["missing_artifacts"])

    def test_validate_missing_coerced_values(self):
        payload = {
            "stage": "VALIDATE",
            "artifacts": {
                "write_request": {},
                "header_map": {"valid": True},
                "field_metadata": {},
                "column_constraints": {},
                "validated_values": {},
            },
        }
        result = run_script(payload)
        self.assertFalse(result["valid"])
        self.assertIn("coerced_values", result["missing_artifacts"])

    def test_write_requires_write_plan(self):
        payload = {
            "stage": "WRITE",
            "artifacts": {
                "write_request": {},
                "header_map": {"valid": True},
                "field_metadata": {},
                "column_constraints": {},
                "validated_values": {},
                "coerced_values": {},
                "existing_values": {},
            },
        }
        result = run_script(payload)
        self.assertFalse(result["valid"])
        self.assertIn("write_plan", result["missing_artifacts"])


if __name__ == "__main__":
    unittest.main()
