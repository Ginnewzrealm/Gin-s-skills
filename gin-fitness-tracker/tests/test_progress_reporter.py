#!/usr/bin/env python3
"""Tests for scripts/progress_reporter.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "progress_reporter.py")


def run_script(payload: dict) -> str:
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(f"script failed: {proc.stderr.decode('utf-8')}")
    return proc.stdout.decode("utf-8")


class TestProgressReporter(unittest.TestCase):
    def test_renders_stage_and_artifacts(self):
        payload = {
            "stage": "VALIDATE",
            "artifacts_status": {
                "write_request": "ready",
                "header_map": "ready",
                "coerced_values": "missing",
            },
        }
        result = run_script(payload)
        self.assertIn("VALIDATE", result)
        self.assertIn("字段元数据类型校验", result)
        self.assertIn("coerced_values", result)
        self.assertIn("当前阻塞", result)


if __name__ == "__main__":
    unittest.main()
