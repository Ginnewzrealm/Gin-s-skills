#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_analyzer.py — N8 JD Analyzer：匹配度打分 + 红标检测 + 策略建议。

打分规则（详见 references/jd-analysis-methodology.md）：
- JD 条目拆分为 Required / Preferred，逐条与知识库比对
- 总分 = Required 覆盖率×70% + Preferred 覆盖率×30%
- 分档：90%+ overqualified / 75-89 强匹配 / 60-74 不错 / 50-59 冲刺 / <50 差距大
- 红标：硬性要求（学历/年限/证书/语言）与知识库事实冲突

用法:
    python3 jd_analyzer.py --jd jd.txt [--kb 路径] [--out 报告路径]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def kb_text(facts):
    parts = [json_like for json_like in [
        " ".join("%s %s" % (k, v) for k, v in facts["basic_info"].items()),
        " ".join(f.get("company", "") + " " + f.get("role", "") + " " + " ".join(f["bullets"]) for f in facts["facts"]),
        " ".join(facts["skills"]),
        " ".join(facts["advantages"]),
    ]]
    return " ".join(parts)


def line_covered(line, kb):
    """条目覆盖率：条目内关键词在知识库中的命中比例。"""
    kws = common.extract_jd_keywords(line)
    if not kws:  # 无词表关键词时退化为长词匹配
        kws = [w for w in re.findall(r"[一-龥]{2,}|[A-Za-z0-9+#.]{2,}", line) if len(w) >= 2]
    if not kws:
        return 1.0, []
    hit = [w for w in kws if w.lower() in kb.lower()]
    return len(hit) / len(kws), [w for w in kws if w.lower() not in kb.lower()]


def detect_red_flags(jd_text, facts):
    flags = []
    # 年限要求 vs 实际年限
    m = re.search(r"(\d+)\s*年[以上以]?[相关]?[工作]?经验", jd_text)
    if m and facts["total_years"] < int(m.group(1)):
        flags.append("年限：JD 要求 %d 年，知识库累计 %.1f 年" % (int(m.group(1)), facts["total_years"]))
    # 学历要求
    m = re.search(r"(博士|硕士|MBA|本科|大专)[及以上]*", jd_text)
    edu_kb = " ".join("%s %s" % (k, v) for k, v in facts["basic_info"].items() if "学历" in k or "教育" in k or "毕业" in k)
    if m and edu_kb and m.group(1) not in edu_kb:
        order = ["大专", "本科", "硕士", "MBA", "博士"]
        try:
            if order.index(m.group(1)) > max(order.index(e) for e in order if e in edu_kb):
                flags.append("学历：JD 要求 %s，知识库记录为 %s" % (m.group(1), edu_kb))
        except ValueError:
            pass
    # 证书/语言硬性要求
    for m in re.finditer(r"(CPA|CFA|PMP|司法考试|律师资格|教师资格证|雅思|托福|英语六级|专八)", jd_text):
        if m.group(1) not in kb_text(facts):
            flags.append("证书/语言：JD 提到 %s，知识库中未见" % m.group(1))
    return flags


def band(score):
    if score >= 90:
        return "overqualified（资历超出，注意薪资与级别预期）"
    if score >= 75:
        return "强匹配（建议尽快投递）"
    if score >= 60:
        return "不错（值得投递，简历需针对性强化）"
    if score >= 50:
        return "冲刺（可投，需在求职信/面试中补足叙事）"
    return "差距大（建议谨慎评估或先补能力）"


def analyze(jd_text, facts):
    required, preferred = common.split_jd_requirements(jd_text)
    kb = kb_text(facts)

    def coverage(lines):
        gaps, total = [], 0.0
        for ln in lines:
            c, miss = line_covered(ln, kb)
            total += c
            gaps.extend(miss)
        return (total / len(lines) * 100) if lines else 100.0, gaps

    req_cov, req_gaps = coverage(required)
    pref_cov, pref_gaps = coverage(preferred)
    score = round(req_cov * 0.7 + pref_cov * 0.3, 1)
    flags = detect_red_flags(jd_text, facts)
    return {
        "score": score, "band": band(score),
        "required": required, "preferred": preferred,
        "req_cov": round(req_cov, 1), "pref_cov": round(pref_cov, 1),
        "gaps": sorted(set(req_gaps + pref_gaps)),
        "red_flags": flags,
    }


def render_report(jd_text, facts, result):
    L = []
    L.append("# JD 匹配度分析报告")
    L.append("")
    L.append("- 匹配度总分：**%.1f / 100**" % result["score"])
    L.append("- 分档结论：**%s**" % result["band"])
    L.append("- Required 覆盖率：%.1f%%（权重 70%%）｜Preferred 覆盖率：%.1f%%（权重 30%%）"
             % (result["req_cov"], result["pref_cov"]))
    L.append("- 候选人：%s｜累计工作年限：%.1f 年"
             % (facts["basic_info"].get("姓名", "（未填）"), facts["total_years"]))
    L.append("")
    L.append("## Required 要求拆解（%d 条）" % len(result["required"]))
    for r in result["required"]:
        L.append("- %s" % r)
    L.append("")
    L.append("## Preferred 加分项（%d 条）" % len(result["preferred"]))
    for p in result["preferred"]:
        L.append("- %s" % p)
    L.append("")
    L.append("## 缺口关键词（知识库未覆盖）")
    L.append("- " + ("、".join(result["gaps"]) if result["gaps"] else "无"))
    L.append("")
    L.append("## 红标项（硬性要求冲突）")
    if result["red_flags"]:
        for f in result["red_flags"]:
            L.append("- 🔴 %s" % f)
    else:
        L.append("- 无")
    L.append("")
    L.append("## 策略建议")
    if result["score"] >= 60:
        L.append("- 建议投递，简历应优先展示与缺口互补的强项，弱化未覆盖要求。")
    else:
        L.append("- 匹配度偏低，如仍想投递，建议用求职信补足动机叙事，并在面试准备中预判缺口质疑。")
    L.append("")
    L.append("---")
    L.append("> 需要我根据这个 JD 生成定制简历吗？（确认后将进入 Resume Pipeline）")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="JD 匹配度分析")
    ap.add_argument("--jd", required=True, help="JD 文本文件路径")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None, help="报告输出路径（缺省写入 生成物/target_roles/）")
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()
    facts = common.load_facts(root)
    result = analyze(jd_text, facts)
    report = render_report(jd_text, facts, result)
    out = args.out or common.out_path(root, "target_roles", "jd分析-%s.md" % common.stamp())
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print("[完成] 匹配度 %.1f（%s）→ %s" % (result["score"], result["band"], out))


if __name__ == "__main__":
    main()
