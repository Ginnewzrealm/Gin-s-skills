#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""interview_prep_generator.py — 面试问题清单生成（N12）。

规则：
- 有 JD → 岗位针对性题（围绕 JD 关键词与项目深挖）；无 JD → 通用行为题。
- STAR 故事库（面试素材/star_stories.md）不存在 → 退出码 3，提示先走 N11。
- 题库 面试素材/question-bank.md 不存在 → 首次运行从内置通用题模式生成，后续增量积累。
- 输出 15-20 题，每题标注简历关联 + STAR 素材分类。

用法:
    python3 interview_prep_generator.py [--jd jd.txt] [--kb 路径] [--count 18]
退出码: 0 成功 / 3 缺 STAR 故事库
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

GENERIC_BANK = [
    ("通用", "请用 2 分钟做一下自我介绍。"),
    ("通用", "你为什么想离开现在的公司？"),
    ("通用", "你近 3 年的职业规划是什么？"),
    ("领导力", "讲一次你带领团队完成目标的经历。"),
    ("解决问题", "讲一个你解决过的最复杂的问题，你是怎么定位的？"),
    ("协作", "讲一次你与其他部门意见不一致时，你是怎么推进的？"),
    ("成就", "你职业生涯中最有成就感的一件事是什么？"),
    ("失败成长", "讲一次失败的经历，你从中吸取了什么教训？"),
    ("通用", "你的优点和缺点分别是什么？"),
    ("通用", "你为什么选择我们公司？"),
]


def ensure_question_bank(root):
    """题库不存在时首次生成（v1 修复点）。"""
    qb = os.path.join(root, common.DIR_INTERVIEW, "question-bank.md")
    if not os.path.exists(qb):
        os.makedirs(os.path.dirname(qb), exist_ok=True)
        with open(qb, "w", encoding="utf-8") as f:
            f.write("# 面试题库（首次运行自动生成，后续增量积累）\n\n")
            for cat, q in GENERIC_BANK:
                f.write("- [%s] %s\n" % (cat, q))
        return True
    return False


def build_questions(facts, jd_text, count):
    questions = []
    if jd_text:
        kws = common.extract_jd_keywords(jd_text)[:6]
        for w in kws:
            questions.append(("岗位针对", "JD 要求「%s」——你过往哪段经历最能证明这项能力？请展开讲。" % w,
                              "对照简历中含「%s」的条目准备量化证据" % w, "成就/解决问题"))
        works = [f for f in facts["facts"] if f["type"] == "work"][-2:]
        for w in works:
            questions.append(("项目深挖", "你在 %s 担任 %s 期间，最大的挑战是什么？怎么解决的？" % (w.get("company"), w.get("role")),
                              "简历 %s 段" % w["fact_id"], "解决问题"))
    for cat, q in GENERIC_BANK:
        questions.append(("通用", q, "结合知识库相应模块回答", cat))
    # 去重并截断到 count
    seen, out = set(), []
    for item in questions:
        if item[1] not in seen:
            seen.add(item[1])
            out.append(item)
        if len(out) >= count:
            break
    return out


def render(questions, has_jd, star_exists):
    mode = "岗位针对性模式（基于 JD）" if has_jd else "通用模式（无 JD）"
    L = ["# 面试问题清单（%s）" % mode, ""]
    if not has_jd:
        L.append("> 提示：有具体 JD 的话发我，能针对性出题。")
        L.append("")
    for i, (typ, q, rel, star) in enumerate(questions, 1):
        L.append("%d. **【%s】%s**" % (i, typ, q))
        L.append("   - 简历关联：%s｜STAR 素材：%s" % (rel, star))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="面试问题清单生成")
    ap.add_argument("--jd", default=None)
    ap.add_argument("--count", type=int, default=18)
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)

    star_p = os.path.join(root, common.DIR_INTERVIEW, "star_stories.md")
    if not os.path.exists(star_p):
        print("[缺依赖] 面试素材/star_stories.md 不存在，请先运行 star_story_generator.py（N11）。")
        sys.exit(3)
    created = ensure_question_bank(root)

    facts = common.load_facts(root)
    jd_text = ""
    if args.jd:
        with open(args.jd, encoding="utf-8") as f:
            jd_text = f.read()
    questions = build_questions(facts, jd_text, args.count)
    md = render(questions, bool(jd_text), True)
    out = common.out_path(root, "interview_prep", "面试清单-%s.md" % common.stamp())
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("[完成] %d 题 → %s%s" % (len(questions), out, "（题库已首次生成）" if created else ""))


if __name__ == "__main__":
    main()
