#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resume_structure_check.py — 简历结构校验（渲染前的质量闸）。

按 references/resume-section-standard.md 的合格线检查 resume.json：
- 工作经历每段：核心职责必填；bullet ≥3 条；含数字 bullet ≥2 条
- 项目经历每个：项目描述必填；bullet ≥2 条；含数字 bullet ≥1 条
- 岗位胜任板块：存在且 2-3 条（缺失/超量只警告）
- 技能板块：存在（缺失只警告）
- bullet 能力小标题（「用户增长：……」）：缺失只警告

用法:
    python3 resume_structure_check.py --resume resume.json

退出码:
    0 = 通过（允许警告）
    2 = 存在硬性失败项，须修正后重新组装，禁止渲染
"""
import argparse
import json
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

# 从 common.py 共享（单一来源）
METRIC_RE = common.METRIC_RE
TAG_RE = re.compile(common.TAG_PATTERN)
FRONT_SECTIONS = common.FRONT_SECTIONS


def has_metric(text):
    return bool(METRIC_RE.search(text))


def main():
    ap = argparse.ArgumentParser(description="简历结构校验（渲染前质量闸）")
    ap.add_argument("--resume", required=True)
    args = ap.parse_args()
    with open(args.resume, encoding="utf-8") as f:
        resume = json.load(f)

    errors, warnings = [], []
    sections = {s.get("title"): s for s in resume.get("sections", [])}

    # ---- 工作经历 ----
    work = sections.get("工作经历")
    if not work:
        errors.append("缺少「工作经历」板块")
    else:
        for i, e in enumerate(work.get("entries", []), 1):
            name = e.get("org", "第%d段" % i)
            if not (e.get("summary") or "").strip():
                errors.append("工作经历「%s」缺少【核心职责】" % name)
            bullets = e.get("bullets", [])
            if len(bullets) < 3:
                errors.append("工作经历「%s」【关键业绩】bullet 仅 %d 条，不足 3 条" % (name, len(bullets)))
            n_metric = sum(1 for b in bullets if has_metric(b))
            if len(bullets) >= 3 and n_metric < 2:
                errors.append("工作经历「%s」含数字的 bullet 仅 %d 条，不足 2 条" % (name, n_metric))
            for b in bullets:
                if not TAG_RE.match(str(b).strip()):
                    warnings.append("工作经历「%s」有 bullet 缺能力小标题：%.20s…" % (name, b))

    # ---- 项目经历 ----
    proj = sections.get("项目经历")
    if proj is not None:
        for i, e in enumerate(proj.get("entries", []), 1):
            name = e.get("org", "第%d个" % i)
            if not (e.get("description") or "").strip():
                errors.append("项目经历「%s」缺少【项目描述】" % name)
            bullets = e.get("bullets", [])
            if len(bullets) < 2:
                errors.append("项目经历「%s」【职责与行动】bullet 仅 %d 条，不足 2 条" % (name, len(bullets)))
            n_metric = sum(1 for b in bullets if has_metric(b))
            if len(bullets) >= 2 and n_metric < 1:
                errors.append("项目经历「%s」没有含数字的 bullet" % name)
            for b in bullets:
                if not TAG_RE.match(str(b).strip()):
                    warnings.append("项目经历「%s」有 bullet 缺能力小标题：%.20s…" % (name, b))

    # ---- 岗位胜任 ----
    front = None
    for t in FRONT_SECTIONS:
        if t in sections:
            front = sections[t]
            break
    if not front:
        warnings.append("缺少「岗位胜任」置顶板块（建议 2-3 条与 JD 呼应的优势）")
    else:
        n = len(front.get("items", []))
        if n < 2 or n > 3:
            warnings.append("「岗位胜任」当前 %d 条，建议 2-3 条" % n)

    # ---- 技能 ----
    if not any(t in sections for t in ("技能", "专业技能", "Skills")):
        warnings.append("缺少「技能」板块（ATS 关键词主要靠它）")

    # ---- 报告 ----
    print("简历结构校验报告")
    print("板块：%s" % "、".join(s.get("title", "?") for s in resume.get("sections", [])))
    if errors:
        print("\n[失败] %d 项（须修正后重新组装，禁止渲染）：" % len(errors))
        for e in errors:
            print("  ✗ %s" % e)
    if warnings:
        print("\n[警告] %d 项：" % len(warnings))
        for w in warnings:
            print("  ! %s" % w)
    if not errors:
        print("\n校验通过，可以渲染。")
    else:
        print("\n校验未通过。")
    sys.exit(2 if errors else 0)


if __name__ == "__main__":
    main()
