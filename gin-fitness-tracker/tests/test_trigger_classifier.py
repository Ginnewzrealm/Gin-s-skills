#!/usr/bin/env python3
"""Tests for scripts/trigger_classifier.py."""
import json
import os
import subprocess
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "trigger_classifier.py")


def classify(message: str, cron: bool = False) -> dict:
    payload = {"message": message, "context": {"cron": cron}}
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(f"script failed: {proc.stderr.decode('utf-8')}")
    return json.loads(proc.stdout.decode("utf-8"))


class TestTriggerClassifier(unittest.TestCase):
    def test_literal_trigger(self):
        result = classify("健身追踪")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "daily_poll")

    def test_literal_with_date(self):
        result = classify("健身追踪 昨天")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "makeup")

    def test_field_fingerprint_weight(self):
        result = classify("晨起体重68.5")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "reply_entry")

    def test_synonym_weight(self):
        result = classify("今早体重68.5kg")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "reply_entry")

    def test_sleep_time_fingerprint(self):
        result = classify("昨晚12点睡的")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "reply_entry")

    def test_entry_verb_record(self):
        result = classify("记录一下体重")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "reply_entry")

    def test_query_this_week(self):
        result = classify("看看这周数据")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "query")

    def test_query_today(self):
        result = classify("今天吃了多少")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "query")

    def test_makeup_with_date(self):
        result = classify("补一下昨天")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "makeup")

    def test_makeup_too_vague(self):
        result = classify("补一下")
        self.assertFalse(result["triggered"])

    def test_init_config(self):
        result = classify("配置健身")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "init")

    def test_sync_xunji(self):
        result = classify("同步讯记")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "sync")

    def test_negative_pdca(self):
        result = classify("帮我做PDCA分析")
        self.assertFalse(result["triggered"])
        self.assertIsNotNone(result["excluded_by"])

    def test_negative_workout_plan(self):
        result = classify("今天练胸")
        self.assertFalse(result["triggered"])

    def test_negative_weekly_report(self):
        result = classify("健身周报")
        self.assertFalse(result["triggered"])

    def test_negative_advice(self):
        result = classify("怎么健身比较好")
        self.assertFalse(result["triggered"])

    def test_cron_daily_poll(self):
        result = classify("", cron=True)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["mode"], "daily_poll")


if __name__ == "__main__":
    unittest.main()
