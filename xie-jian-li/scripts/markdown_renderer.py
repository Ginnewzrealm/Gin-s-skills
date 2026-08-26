#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markdown_renderer.py — 渲染 Markdown 简历（与 html_renderer 同一 resume.json）。

用法:
    python3 markdown_renderer.py --resume resume.json [--kb 路径] [--out out.md]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


# 字段标签：与 html_renderer.SECTION_FIELDS 保持一致
SECTION_FIELDS = {
    "工作经历": {"summary": "核心职责", "bullets": "关键业绩",
                 "skills": "专业能力", "honor": "荣誉奖项"},
    "项目经历": {"description": "项目描述", "bullets": "职责与行动",
                 "impact": "成果与影响"},
}


def render(resume):
    basic = resume.get("basic", {})
    L = ["# %s" % basic.get("姓名", "（姓名）"), ""]
    contact = "　·　".join(basic[k] for k in ("电话", "邮箱", "城市", "求职意向") if basic.get(k))
    if contact:
        L += [contact, ""]
    for sec in resume.get("sections", []):
        fields = SECTION_FIELDS.get(sec["title"], {})
        L.append("## %s" % sec["title"])
        for e in sec.get("entries", []):
            org = e.get("org", "")
            if e.get("org_note"):
                org += "（%s）" % e["org_note"]
            head = " | ".join(x for x in (org, e.get("role"), e.get("period")) if x)
            L.append("### %s" % head)
            if e.get("summary"):
                L.append("**%s**：%s" % (fields.get("summary", "核心职责"), e["summary"]))
            if e.get("description"):
                L.append("**%s**：%s" % (fields.get("description", "项目描述"), e["description"]))
            if fields.get("bullets") and e.get("bullets"):
                L.append("**%s**：" % fields["bullets"])
            for b in e.get("bullets", []):
                L.append("- %s" % b)
            if e.get("skills"):
                L.append("**%s**：%s" % (fields.get("skills", "专业能力"), e["skills"]))
            if e.get("impact"):
                L.append("**%s**：%s" % (fields.get("impact", "成果与影响"), e["impact"]))
            if e.get("honor"):
                L.append("**%s**：%s" % (fields.get("honor", "荣誉奖项"), e["honor"]))
            L.append("")
        for g in sec.get("groups", []):
            L.append("- **%s**：%s" % (g.get("label", ""), "、".join(g.get("items", []))))
        for i in sec.get("items", []):
            if isinstance(i, dict):  # 岗位胜任双字段：能力标签 + 内容体现
                L.append("- **%s**：%s" % (i.get("tag", ""), i.get("text", "")))
            else:
                L.append("- %s" % i)
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="渲染 Markdown 简历")
    ap.add_argument("--resume", required=True)
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.resume, encoding="utf-8") as f:
        resume = json.load(f)
    md = render(resume)
    if args.out:
        out = args.out
    else:
        root = common.kb_root(args.kb)
        out = common.out_path(root, "resumes", "%s-%s.md" % (resume.get("title", "简历"), common.stamp()))
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("[完成] Markdown 简历已生成: %s" % out)


if __name__ == "__main__":
    main()
