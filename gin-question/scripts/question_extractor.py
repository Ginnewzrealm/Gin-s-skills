#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""question_extractor.py — 从抓取的网页内容或搜索结果标题中提取真实问题。

要求：问题必须来自真实网页 title 或正文引用，不推断、不改写。
"""

import re
from html import unescape

from common import is_question_like, normalize_text


def strip_html(html):
    """简单去除 HTML 标签。"""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text)


def extract_from_title(title):
    """从页面标题中提取问题。"""
    if not title:
        return None
    title = title.strip()
    # 去掉常见的后缀，如 " - 知乎"
    title = re.sub(r"[\-–—]\s*(知乎|百度知道|Quora|Reddit|豆瓣|悟空问答|简书).*$", "", title).strip()
    title = title.strip()
    if is_question_like(title) and len(title) >= 5:
        return normalize_text(title)
    return None


def extract_from_content(html, source_url, max_candidates=50):
    """从 HTML 正文中提取候选问题。

    策略：
    - 从 h1/h2/h3 标题、加粗文本、独立段落中提取疑问句
    - 优先提取看起来像用户提问的句子
    """
    text = strip_html(html)
    candidates = []

    # 1. 提取 h1-h3 中的文本
    headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, flags=re.DOTALL)
    for h in headings:
        h = strip_html(h).strip()
        q = extract_from_title(h)
        if q and q not in candidates:
            candidates.append(q)

    # 2. 按句子切分，提取疑问句
    sentences = re.split(r"(?<=[。！？?\n])", text)
    for s in sentences:
        s = s.strip()
        if is_question_like(s) and 5 <= len(s) <= 120:
            q = normalize_text(s)
            if q not in candidates:
                candidates.append(q)
        if len(candidates) >= max_candidates:
            break

    return [{"text": q, "source_url": source_url, "extracted_from": "content"} for q in candidates]


def extract_from_search_result(title, url):
    """当页面无法抓取时，使用搜索结果的页面标题作为问题来源。"""
    q = extract_from_title(title)
    if q:
        return {"text": q, "source_url": url, "extracted_from": "search_title"}
    return None


def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 question_extractor.py <html-file-or-title> [--title]")
        sys.exit(1)
    arg = sys.argv[1]
    is_title = "--title" in sys.argv
    if is_title:
        print(extract_from_title(arg))
    else:
        try:
            with open(arg, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception:
            html = arg
        results = extract_from_content(html, "https://example.com")
        for r in results[:10]:
            print(r["text"])


if __name__ == "__main__":
    main()
