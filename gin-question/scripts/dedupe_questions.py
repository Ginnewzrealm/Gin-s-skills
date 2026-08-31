#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dedupe_questions.py — 问题去重：精确 + 语义 + 子集。

语义去重默认使用简化字符集合的 Jaccard 相似度；当 sentence-transformers 可用时
可替换为余弦相似度。
"""

import re
from collections import defaultdict


def normalize(text):
    """文本归一化：去首尾空格、统一问号、去除常见无意义助词。"""
    text = text.strip()
    text = text.replace("?", "？")
    # 去除语气词和重复问号
    text = re.sub(r"[吗呢么]+[？?]*$", "？", text)
    text = re.sub(r"[？?]+$", "？", text)
    return text.strip()


def char_set(text):
    """提取文本中的中文字符集合，用于 Jaccard 计算。"""
    return set(re.findall(r"[一-龥]", text))


def jaccard(a, b):
    sa, sb = char_set(a), char_set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def is_subset(short, long_):
    """判断 short 的问题是否是 long_ 的完整子集（按字符集合）。"""
    ss, ls = char_set(short), char_set(long_)
    if not ss:
        return False
    return ss <= ls and len(short) < len(long_)


def dedupe(questions, semantic_threshold=0.85):
    """去重主函数。

    questions: list of dict, 每个 dict 至少包含 'text'
    返回：{
        unique: [dict],
        duplicates_merged: int,
        detail: [{kept, merged: [text...]}]
    }
    """
    # 1. 精确去重
    seen_texts = {}
    unique = []
    for q in questions:
        key = normalize(q.get("text", ""))
        if not key:
            continue
        if key in seen_texts:
            seen_texts[key].append(q)
        else:
            seen_texts[key] = [q]
            unique.append({**q, "_norm": key, "duplicates": []})

    # 2. 语义去重 + 子集去重
    merged_indices = set()
    detail = []

    # 按长度降序，优先保留更长/更具体的问题
    order = sorted(range(len(unique)), key=lambda i: len(unique[i]["_norm"]), reverse=True)

    for i in order:
        if i in merged_indices:
            continue
        kept = unique[i]
        merged_texts = []
        for j in order:
            if i == j or j in merged_indices:
                continue
            candidate = unique[j]
            sim = jaccard(kept["_norm"], candidate["_norm"])
            if sim >= semantic_threshold or is_subset(candidate["_norm"], kept["_norm"]):
                merged_texts.append(candidate.get("text", candidate["_norm"]))
                kept["duplicates"].append(candidate.get("text", candidate["_norm"]))
                merged_indices.add(j)
        detail.append({
            "kept": kept.get("text", kept["_norm"]),
            "merged": merged_texts,
        })

    result = [unique[i] for i in range(len(unique)) if i not in merged_indices]
    # 移除内部使用的 _norm
    for r in result:
        r.pop("_norm", None)

    return {
        "unique": result,
        "duplicates_merged": len(merged_indices),
        "detail": detail,
    }


def main():
    import sys
    import json
    if len(sys.argv) < 2:
        print("用法: python3 dedupe_questions.py '<json数组>'")
        print('示例: python3 dedupe_questions.py \'["减脂是什么？", "什么是减脂？", "减脂"]\'')
        sys.exit(1)
    try:
        arr = json.loads(sys.argv[1])
    except Exception:
        arr = [sys.argv[1]]
    questions = [{"text": t} for t in arr]
    out = dedupe(questions)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
