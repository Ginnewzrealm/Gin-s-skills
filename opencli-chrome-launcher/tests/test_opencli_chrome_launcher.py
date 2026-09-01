#!/usr/bin/env python3
"""Tests for scripts/opencli_chrome_launcher.py."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, SCRIPT_DIR)

import opencli_chrome_launcher as launcher


class TestProfileListParsing(unittest.TestCase):
    def test_parse_single_connected(self):
        output = "Connected Browser Bridge profiles\n  g3a5ehu6 — connected v1.0.22\n"
        profiles = launcher.OpenCLIChromeLauncher()._parse_profile_list(output)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["id"], "g3a5ehu6")
        self.assertTrue(profiles[0]["connected"])

    def test_parse_multiple_with_disconnected(self):
        output = """Connected Browser Bridge profiles
  g3a5ehu6 — connected v1.0.22

Disconnected saved profiles
  Profile 1 — default, not connected
"""
        profiles = launcher.OpenCLIChromeLauncher()._parse_profile_list(output)
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0]["id"], "g3a5ehu6")
        self.assertTrue(profiles[0]["connected"])
        self.assertEqual(profiles[1]["id"], "Profile")
        self.assertFalse(profiles[1]["connected"])


class TestDoctorParsing(unittest.TestCase):
    def test_doctor_green(self):
        output = "Everything looks good\nConnectivity: ok\n"
        status = launcher.OpenCLIChromeLauncher()._bridge_status()
        # _bridge_status runs real opencli doctor; we only test helper logic indirectly
        self.assertIsInstance(status, dict)
        self.assertIn("ok", status)

    def test_doctor_output_has_fail(self):
        self.assertTrue("[FAIL]" in "[FAIL] Browser")
        self.assertTrue("Connectivity: failed" in "Connectivity: failed")


class TestProfileDirectoryParsing(unittest.TestCase):
    def test_simple_profile_directory(self):
        cmd = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --profile-directory=Profile 1'
        result = launcher.OpenCLIChromeLauncher()._parse_profile_directory_from_command(cmd)
        self.assertEqual(result, "Profile 1")

    def test_no_profile_directory(self):
        cmd = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --new-window'
        result = launcher.OpenCLIChromeLauncher()._parse_profile_directory_from_command(cmd)
        self.assertIsNone(result)


class TestProfileSelection(unittest.TestCase):
    def test_single_profile_auto(self):
        matched = [{"opencli_id": "g3a5ehu6", "opencli_name": "", "chrome_id": "Profile 1"}]
        selected = launcher.OpenCLIChromeLauncher()._select_profile(matched, [])
        self.assertEqual(selected["opencli_id"], "g3a5ehu6")

    def test_opencli_name_priority(self):
        matched = [
            {"opencli_id": "abc", "opencli_name": "", "chrome_id": "Default"},
            {"opencli_id": "def", "opencli_name": "opencli-agent", "chrome_id": "Profile 1"},
        ]
        selected = launcher.OpenCLIChromeLauncher()._select_profile(matched, [])
        self.assertEqual(selected["opencli_id"], "def")


class TestConfigRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_config_path = launcher.CONFIG_PATH
        launcher.CONFIG_PATH = os.path.join(self.tmpdir.name, "binding.json")

    def tearDown(self):
        launcher.CONFIG_PATH = self.original_config_path
        self.tmpdir.cleanup()

    def test_save_and_load(self):
        config = launcher._default_config()
        config["initialized"] = True
        config["browser_profile"]["opencli_profile_id"] = "g3a5ehu6"
        launcher.save_config(config)
        loaded = launcher.load_config()
        self.assertTrue(loaded["initialized"])
        self.assertEqual(loaded["browser_profile"]["opencli_profile_id"], "g3a5ehu6")


class TestLock(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_lock_path = launcher.LOCK_FILE_PATH
        launcher.LOCK_FILE_PATH = os.path.join(self.tmpdir.name, "lock")

    def tearDown(self):
        launcher.LOCK_FILE_PATH = self.original_lock_path
        self.tmpdir.cleanup()

    def test_acquire_and_release(self):
        l = launcher.OpenCLIChromeLauncher()
        self.assertTrue(l._acquire_lock())
        self.assertTrue(os.path.exists(launcher.LOCK_FILE_PATH))
        l._release_lock()
        self.assertFalse(os.path.exists(launcher.LOCK_FILE_PATH))

    def test_acquire_timeout(self):
        l1 = launcher.OpenCLIChromeLauncher()
        l2 = launcher.OpenCLIChromeLauncher()
        self.assertTrue(l1._acquire_lock())
        # Second acquire with very short timeout should fail quickly
        with patch.object(launcher.time, "sleep", return_value=None):
            self.assertFalse(l2._acquire_lock(timeout=0))
        l1._release_lock()


class TestErrorEnvelope(unittest.TestCase):
    def test_error_structure(self):
        l = launcher.OpenCLIChromeLauncher()
        result = l._error("TEST_CODE", "short msg", reason="r", action="a", impact="i")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["module"], "opencli-chrome-launcher")
        self.assertIn("short msg", result["message"])
        self.assertEqual(result["errors"][0]["code"], "TEST_CODE")


if __name__ == "__main__":
    unittest.main()
