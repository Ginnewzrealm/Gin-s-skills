#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_chrome_launcher_adapter.py"""
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts import chrome_launcher_adapter as adapter


def test_find_launcher_from_env(tmp_path):
    fake = tmp_path / "opencli-chrome-launcher" / "scripts" / "opencli_chrome_launcher.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("# fake", encoding="utf-8")
    with patch.dict(os.environ, {"OPENCLI_CHROME_LAUNCHER_DIR": str(tmp_path / "opencli-chrome-launcher")}):
        found = adapter.find_opencli_chrome_launcher_script()
    assert found == str(fake)


def test_find_launcher_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter.os.path, "isfile", lambda _p: False)
    found = adapter.find_opencli_chrome_launcher_script()
    assert found is None


def test_run_launcher_returns_success_json(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            stdout = json.dumps({"status": "success", "module": "opencli-chrome-launcher"})
            stderr = ""
            returncode = 0
        return R()

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    res = adapter.run_launcher("use", launcher_script=str(fake))
    assert res["status"] == "success"


def test_run_launcher_parses_failed_output(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            stdout = "not json"
            stderr = "boom"
            returncode = 1
        return R()

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    res = adapter.run_launcher("use", launcher_script=str(fake))
    assert res["status"] == "failed"
    assert res["errors"][0]["code"] == "LAUNCHER_OUTPUT_ERROR"


def test_ensure_browser_ready_uses_launcher_when_available(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: str(fake))

    responses = [
        {"status": "success", "module": "opencli-chrome-launcher"},
    ]

    def fake_run_launcher(mode, session=None, launcher_script=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "run_launcher", fake_run_launcher)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True
    assert source == "opencli-chrome-launcher"


def test_ensure_browser_ready_init_when_no_binding(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: str(fake))

    responses = [
        {"status": "failed", "errors": [{"code": "NO_BINDING_CONFIG"}]},
        {"status": "success", "module": "opencli-chrome-launcher"},  # init
        {"status": "success", "module": "opencli-chrome-launcher"},  # use again
    ]

    def fake_run_launcher(mode, session=None, launcher_script=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "run_launcher", fake_run_launcher)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True


def test_ensure_browser_ready_falls_back_to_internal(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: None)

    responses = [
        {"status": "success"},  # init
        {"status": "success"},  # use
    ]

    def fake_internal(mode, session=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "_run_internal_browser_manager", fake_internal)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True
    assert source == "internal-browser-manager"


def test_cleanup_browser_uses_source(monkeypatch, tmp_path):
    cleanup_called = []

    def fake_launcher_cleanup(mode, session=None, launcher_script=None):
        cleanup_called.append(("launcher", mode, session))
        return {"status": "success"}

    monkeypatch.setattr(adapter, "run_launcher", fake_launcher_cleanup)
    adapter.cleanup_browser("collector", source="opencli-chrome-launcher")
    assert cleanup_called == [("launcher", "cleanup", "collector")]


def test_cleanup_browser_falls_back_internal(monkeypatch):
    cleanup_called = []

    def fake_internal(mode, session=None):
        cleanup_called.append(("internal", mode, session))
        return {"status": "success"}

    monkeypatch.setattr(adapter, "_run_internal_browser_manager", fake_internal)
    adapter.cleanup_browser("collector", source="internal-browser-manager")
    assert cleanup_called == [("internal", "cleanup", "collector")]
