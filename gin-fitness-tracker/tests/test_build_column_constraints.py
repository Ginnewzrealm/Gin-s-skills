#!/usr/bin/env python3
"""Tests for scripts/build_column_constraints.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "build_column_constraints.py")


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


class TestBuildColumnConstraints(unittest.TestCase):
    def test_normalizes_lark_output(self):
        payload = {
            "cells": [[
                {"cell_styles": {"number_format": "0.00%"}, "value": "24.00%"},
                {"cell_styles": {"number_format": "h:mm"}, "value": "0:00"},
                {"data_validation": {"items": ["🟢有力", "🟢正常", "🔴无力"]}, "value": None},
            ]],
            "col_indices": ["C", "D", "E"],
        }
        result = run_script(payload)
        self.assertEqual(result["column_constraints"]["C"]["number_format"], "0.00%")
        self.assertEqual(result["column_constraints"]["D"]["number_format"], "h:mm")
        self.assertEqual(
            result["column_constraints"]["E"]["data_validation"]["items"],
            ["🟢有力", "🟢正常", "🔴无力"],
        )

    def test_auto_generates_col_indices(self):
        payload = {
            "cells": [[
                {"cell_styles": {"number_format": "0.00"}},
                {"cell_styles": {"number_format": "0.00%"}},
            ]]
        }
        result = run_script(payload)
        self.assertEqual(result["column_constraints"]["A"]["number_format"], "0.00")
        self.assertEqual(result["column_constraints"]["B"]["number_format"], "0.00%")

    def test_general_format_when_no_style(self):
        payload = {
            "cells": [[{"value": "hello"}]],
            "col_indices": ["A"],
        }
        result = run_script(payload)
        self.assertEqual(result["column_constraints"]["A"]["number_format"], "General")
        self.assertIsNone(result["column_constraints"]["A"]["data_validation"])


if __name__ == "__main__":
    unittest.main()
