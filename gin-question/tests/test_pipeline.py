#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_pipeline.py — 端到端流水线测试。"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pipeline


def build_sample_manifest():
    return {
        "topic": "减脂",
        "expanded_terms": ["减肥", "瘦身"],
        "retrieval_rounds": 1,
        "search_results": [
            {
                "perspective": "基础",
                "sub_dimension": "What",
                "query": "减脂是什么",
                "results": [
                    {"title": "减脂和减肥有什么区别？ - 知乎", "url": "https://www.zhihu.com/question/1"},
                    {"title": "减脂的科学原理是什么", "url": "https://www.sohu.com/a/1"},
                ],
            },
            {
                "perspective": "旅程",
                "sub_dimension": "瓶颈期",
                "query": "减脂平台期怎么办",
                "results": [
                    {"title": "进入减脂平台期，该怎么办？ - 知乎", "url": "https://www.zhihu.com/question/2"},
                ],
            },
        ],
        "fetched_pages": {
            "https://www.zhihu.com/question/1": "<html><h1>减脂和减肥有什么区别？</h1></html>",
        },
    }


def test_pipeline_run():
    manifest = build_sample_manifest()
    tmpdir = tempfile.mkdtemp()
    try:
        result = pipeline.run(manifest, tmpdir, is_abstract=False)
        assert result["confirmed_count"] + result["pending_count"] >= 1
        assert os.path.exists(os.path.join(tmpdir, "problem_list.json"))
        assert os.path.exists(os.path.join(tmpdir, "problem_list.md"))
        assert os.path.exists(os.path.join(tmpdir, "audit_report.json"))

        with open(os.path.join(tmpdir, "problem_list.json"), "r", encoding="utf-8") as f:
            pl = json.load(f)
        assert pl["topic"] == "减脂"
        assert "problems" in pl
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_pipeline_run()
    print("test_pipeline OK")
