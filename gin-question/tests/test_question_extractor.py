#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_question_extractor.py — 问题提取来源追踪测试。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import question_extractor


def test_extract_from_content_marks_source():
    """从正文提取的问题应标记 extracted_from=content。"""
    html = "<html><h1>减脂怎么吃？</h1></html>"
    results = question_extractor.extract_from_content(html, "https://example.com", topic="减脂")
    assert len(results) == 1
    assert results[0]["extracted_from"] == "content"


def test_extract_from_search_title_marks_source():
    """从搜索标题提取的问题应标记 extracted_from=search_title。"""
    result = question_extractor.extract_from_search_result(
        "减脂怎么吃？ - 知乎", "https://www.zhihu.com/question/1", topic="减脂"
    )
    assert result is not None
    assert result["extracted_from"] == "search_title"


def test_extract_from_title_returns_text():
    """从页面标题提取的问题返回归一化文本。"""
    result = question_extractor.extract_from_title("减脂怎么吃？", topic="减脂")
    assert result is not None
    assert "减脂怎么吃" in result


if __name__ == "__main__":
    test_extract_from_content_marks_source()
    test_extract_from_search_title_marks_source()
    test_extract_from_title_returns_text()
    print("test_question_extractor OK")
