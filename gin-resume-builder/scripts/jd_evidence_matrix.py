#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_evidence_matrix.py — JD-证据匹配矩阵。

用法:
    python3 jd_evidence_matrix.py --jd <jd.json> --facts <facts.json> --out matrix.json
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


LEVEL_ORDER = ["direct", "adjacent", "weak", "absent"]


def _normalize(text):
    return re.sub(r"[^一-龥a-zA-Z0-9]", "", str(text)).lower()


def _keyword_overlap(req_text, fact_text):
    req_tokens = set(_normalize(req_text))
    fact_tokens = set(_normalize(fact_text))
    if not req_tokens:
        return 0.0
    return len(req_tokens & fact_tokens) / len(req_tokens)


def _fact_text(fact):
    parts = []
    parts.extend(fact.get("bullets", []))
    parts.append(fact.get("role", ""))
    parts.append(fact.get("company", ""))
    parts.append(fact.get("name", ""))
    return " ".join(parts)


def _score_fact(req, fact):
    text = _fact_text(fact)
    overlap = _keyword_overlap(req["text"], text)
    if overlap >= 0.6:
        return "direct"
    if overlap >= 0.3:
        return "adjacent"
    if overlap >= 0.1:
        return "weak"
    return None


def build_matrix(jd, facts):
    matrix = []
    for req in jd.get("requirements", []):
        best = None
        matches = []
        for fact in facts.get("facts", []):
            level = _score_fact(req, fact)
            if level:
                matches.append({"fact_id": fact["fact_id"], "level": level})
                if best is None or LEVEL_ORDER.index(level) < LEVEL_ORDER.index(best):
                    best = level
        matrix.append({
            "requirement": req["text"],
            "type": req.get("type", "required"),
            "level": best or "absent",
            "matches": matches,
            "action": _action_for_level(best),
        })
    return matrix


def _action_for_level(level):
    return {
        "direct": "emphasize",
        "adjacent": "bridge",
        "weak": "compress_or_omit",
        "absent": "honest_gap",
    }.get(level, "honest_gap")


def main():
    ap = argparse.ArgumentParser(description="JD-证据匹配矩阵")
    ap.add_argument("--jd", required=True, help="JD JSON 文件")
    ap.add_argument("--facts", required=True, help="facts.json 路径")
    ap.add_argument("--out", required=True, help="输出 matrix.json 路径")
    args = ap.parse_args()

    with open(args.jd, encoding="utf-8") as f:
        jd = json.load(f)
    with open(args.facts, encoding="utf-8") as f:
        facts = json.load(f)

    matrix = build_matrix(jd, facts)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    print("[完成] 已生成匹配矩阵：%s" % args.out)


if __name__ == "__main__":
    main()
