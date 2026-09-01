#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cover_letter_renderer.py — 求职信 / 打招呼语骨架生成（N10）。

脚本职责：读取知识库，挑出与 JD 最相关的亮点，按所选模板
（standard / referral / career-switch / fresh / boss）生成带槽位的 Markdown 骨架，
由 Claude 填充叙事成稿。模板结构详见 references/cover-letter-templates.md。
长模板（邮件/附件场景）成稿 300-500 中文字；boss 模板（IM 打招呼场景）成稿 50-100
中文字、上限 120。可用 --check 配合 --template 校验字数。

用法:
    python3 cover_letter_renderer.py --jd jd.txt --template standard [--kb 路径] [--out out.md]
    python3 cover_letter_renderer.py --jd jd.txt --template boss [--kb 路径]
    python3 cover_letter_renderer.py --check letter.md --template boss   # 字数校验
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import fact_selector
import company_researcher

TEMPLATES = {
    "standard": ["开场钩子：一句话点明应聘岗位与最匹配的卖点",
                 "价值主张：亮点 1-2（量化成果）",
                 "为什么选这家：结合 JD 表达对业务/团队的理解",
                 "强结尾：明确期待面试机会"],
    "referral": ["开场：点明推荐人及其与公司的关系",
                 "价值主张：亮点 1-2（量化成果）",
                 "为什么选这家：结合 JD 表达理解",
                 "强结尾：致谢推荐人 + 期待面试"],
    "career-switch": ["开场钩子：直接回应「为什么转行」——迁移动机一句话",
                      "可迁移能力：亮点 1-2（强调沟通/管理/分析等通用能力）",
                      "为新行业的准备：自学/项目/证书等证据",
                      "强结尾：把「转行」包装成独特价值，期待面试"],
    "fresh": ["开场钩子：岗位 + 应届生身份 + 最相关的校园/实习卖点",
              "价值主张：实习/项目亮点 1-2（量化成果）",
              "为什么选这家：结合 JD 表达理解",
              "强结尾：学习能力强 + 期待面试"],
    "boss": ["身份钩子（≤35 字，必须进消息预览）：岗位 + 年限/领域/最强标签 + 可选公司动态",
             "匹配证据：只写最强的 1 个量化亮点 + 1 个岗位匹配点（技能/行业/资源）",
             "行动号召：提问式结尾，如「想请教这个岗位目前最看重哪个指标？」或「方便发您作品集参考吗？」"],
}

# 各模板中文字数区间（下限, 上限）
LENGTH_RANGES = {
    "boss": (50, 120),       # IM 打招呼：50-100 为佳，120 封顶
    "standard": (300, 500),
    "referral": (300, 500),
    "career-switch": (300, 500),
    "fresh": (300, 500),
}


def check_length(text):
    n = len(re.findall(r"[一-龥]", text))
    return n


def main():
    ap = argparse.ArgumentParser(description="求职信骨架生成 / 字数校验")
    ap.add_argument("--jd", default=None)
    ap.add_argument("--template", choices=list(TEMPLATES), default="standard")
    ap.add_argument("--check", default=None, help="校验成稿字数（区间随 --template，默认 standard 300-500）")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--company", default=None, help="目标公司名称，用于查询研究缓存")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lo, hi = LENGTH_RANGES[args.template]

    if args.check:
        with open(args.check, encoding="utf-8") as f:
            n = check_length(f.read())
        ok = lo <= n <= hi
        if ok:
            status = "✅ 合格（%s 模板区间 %d-%d 字）" % (args.template, lo, hi)
        elif n > hi:
            status = "⚠️ 超长（%s 模板需压缩到 %d-%d 字）" % (args.template, lo, hi)
        else:
            status = "⚠️ 过短（%s 模板需扩充到 %d-%d 字）" % (args.template, lo, hi)
        print("中文字数：%d → %s" % (n, status))
        sys.exit(0 if ok else 2)

    if not args.jd:
        raise SystemExit("[错误] 生成骨架需要 --jd")
    root = common.kb_root(args.kb)
    facts = common.load_facts(root)
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()

    highlights = fact_selector.select(facts, jd_text, top=3)
    name = facts["basic_info"].get("姓名", "（姓名）")
    kind = "打招呼语" if args.template == "boss" else "求职信"
    L = ["# %s骨架（模板：%s）" % (kind, args.template), ""]
    L.append("> 署名：%s｜以下是结构槽位，请 Claude 基于亮点事实填充成 %d-%d 中文字成稿%s。"
             % (name, lo, hi if args.template != "boss" else 120,
                "（上限 %d）" % hi if args.template == "boss" else ""))
    if args.company:
        cached = company_researcher.load_cache(root, args.company)
        if cached:
            L.append("> 公司研究缓存（%s，%s 天内有效）：" % (args.company, 30))
            for src, info in cached.get("sources", {}).items():
                if info.get("notes"):
                    L.append("> - %s：%s" % (src, info["notes"]))
        else:
            L.append("> 公司研究缓存：未命中 %s，如需引用公司动态请先研究。" % args.company)
    L.append("")
    for i, slot in enumerate(TEMPLATES[args.template], 1):
        L.append("## 段落 %d：%s" % (i, slot))
        if "亮点" in slot or "能力" in slot:
            for h in highlights:
                L.append("- 可用亮点 [%s] %s · %s：%s" % (h["fact_id"], h["org"], h["role"], h["bullet"]))
        L.append("")
    md = "\n".join(L)
    out = args.out or common.out_path(root, "cover_letters", "%s骨架-%s-%s.md" % (kind, args.template, common.stamp()))
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("[完成] 骨架已生成: %s（成稿后用 --check <文件> --template %s 校验字数）" % (out, args.template))


if __name__ == "__main__":
    main()
