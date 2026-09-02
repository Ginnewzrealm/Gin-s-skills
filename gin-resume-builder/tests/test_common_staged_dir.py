#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "common", Path(__file__).parent.parent / "scripts" / "common.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["common"] = mod
spec.loader.exec_module(mod)


def test_staged_dir_constant_exists():
    assert hasattr(mod, "DIR_STAGED")
    assert mod.DIR_STAGED == "待确认"
