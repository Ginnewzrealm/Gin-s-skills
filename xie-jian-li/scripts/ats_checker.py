#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ats_checker.py — ATS 预检 / 诊断（N9 第②步预检 + N16 独立诊断）。

两类检查（清单详见 references/ats-checklist.md）：
1. 关键词覆盖：JD 关键词在简历文本中的命中率
2. 格式检查：章节名规范、图表/文本框风险、缩写首次出现是否展开

用法:
    python3 ats_checker.py --jd jd.txt --resume resume.md [--kb 路径] [--out 报告路径]
    python3 ats_checker.py --jd jd.txt [--kb 路径]   # 不传简历时对知识库做预检（N9 第②步）
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

STANDARD_SECTIONS = ["基本信息", "个人信息", "工作经历", "工作经歷", "项目经历", "教育背景", "技能", "岗位胜任", "核心亮点", "个人优势", "自我评价"]


def check_keywords(jd_text, resume_text):
    kws = common.extract_jd_keywords(jd_text)
    if not kws:
        return 100.0, [], []
    hit = [w for w in kws if w.lower() in resume_text.lower()]
    miss = [w for w in kws if w.lower() not in resume_text.lower()]
    return round(len(hit) / len(kws) * 100, 1), hit, miss


def check_format(resume_text):
    issues = []
    if not any(s in resume_text for s in STANDARD_SECTIONS):
        issues.append("未检测到标准章节名（如 工作经历/项目经历/教育背景），ATS 可能无法正确归类内容")
    if "|" in resume_text and "---" in resume_text:
        issues.append("检测到 Markdown 表格：部分 ATS 解析表格会乱序，建议正文避免表格")
    for ch in ("[图]", "![", "<img"):
        if ch in resume_text:
            issues.append("检测到图片：ATS 无法读取图片内容，关键信息必须以文字呈现")
            break
    import re
    for m in re.finditer(r"\b[A-Z]{2,6}\b", resume_text):
        abbr = m.group(0)
        if abbr in ("A", "I", "OK", "HR", "JD"):
            continue
        # 首次出现附近若无中文或全称，提示展开
        idx = resume_text.find(abbr)
        ctx = resume_text[max(0, idx - 30):idx]
        if not re.search(r"[一-龥]|[A-Za-z]{6,}\s*\(", ctx):
            issues.append("缩写「%s」首次出现未展开全称，建议首次写「全称（缩写）」" % abbr)
    return sorted(set(issues))


def render(cov, hit, miss, issues, mode):
    L = ["# ATS %s报告" % mode, ""]
    L.append("- JD 关键词覆盖率：**%.1f%%**（命中 %d / 共 %d）" % (cov, len(hit), len(hit) + len(miss)))
    L.append("")
    L.append("## 未覆盖关键词")
    L.append("- " + ("、".join(miss) if miss else "无"))
    L.append("")
    L.append("## 格式检查")
    if issues:
        for i in issues:
            L.append("- ⚠️ %s" % i)
    else:
        L.append("- ✅ 未发现格式风险")
    L.append("")
    L.append("## 建议")
    if miss:
        L.append("- 将未覆盖关键词中真实具备的能力，自然融入简历条目（不得虚构）。")
    if issues:
        L.append("- 按上述格式项逐项修正后复检。")
    if not miss and not issues:
        L.append("- 通过预检，可进入下一步。")
    return "\n".join(L)


def run(jd_text, resume_text, mode, out=None):
    cov, hit, miss = check_keywords(jd_text, resume_text)
    issues = check_format(resume_text)
    report = render(cov, hit, miss, issues, mode)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
    return cov, miss, issues, report


def main():
    ap = argparse.ArgumentParser(description="ATS 检查")
    ap.add_argument("--jd", required=True)
    ap.add_argument("--resume", default=None, help="简历文本/md；缺省则对知识库做预检")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()

    if args.resume:
        with open(args.resume, encoding="utf-8") as f:
            resume_text = f.read()
        mode = "诊断"
        root = common.kb_root(args.kb) if (args.kb or os.path.exists(common.CONFIG_PATH)) else None
        out = args.out or (common.out_path(root, "ats_reports", "ats诊断-%s.md" % common.stamp()) if root else None)
    else:
        root = common.kb_root(args.kb)
        facts = common.load_facts(root)
        resume_text = " ".join([" ".join(f["bullets"]) for f in facts["facts"]] + facts["skills"])
        mode = "预检"
        out = args.out

    cov, miss, issues, report = run(jd_text, resume_text, mode, out)
    print(report)
    if out:
        print("\n[完成] 报告已写入: %s" % out)


if __name__ == "__main__":
    main()
