#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resume_review_gate.py — 简历渲染前确认闸门（N9 硬闸门）。

职责：
- 读取 resume.json，生成可读的简历文字稿预览
- 维护 review_state.json，记录用户是否确认渲染
- 用户确认前禁止进入 HTML/Markdown 渲染步骤

用法：
    # 生成预览并初始化/重置 review 状态
    python3 resume_review_gate.py --resume resume.json --state review_state.json

    # 用户确认可以渲染
    python3 resume_review_gate.py --approve --state review_state.json

    # 用户要求修改（退出码 2，主 skill 回退到改写/初稿确认）
    python3 resume_review_gate.py --reject --feedback "修改意见" --state review_state.json

    # 仅检查当前状态
    python3 resume_review_gate.py --check --state review_state.json
"""
import argparse
import json
import os
import sys
from datetime import datetime


def load_resume(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_state(path):
    if not os.path.exists(path):
        return {"render_approved": False, "feedback": "", "approved_at": None}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(path, state):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def format_resume_text(resume):
    """把 resume.json 渲染成可读的简历文字稿，用于用户确认。"""
    lines = []

    # 基本信息
    basic = resume.get("basic_info", {})
    name = basic.get("name", "")
    phone = basic.get("phone", "")
    email = basic.get("email", "")
    if name:
        lines.append(f"姓名：{name}")
    if phone:
        lines.append(f"电话：{phone}")
    if email:
        lines.append(f"邮箱：{email}")
    if lines:
        lines.append("")

    # 岗位胜任 / 核心亮点 / 个人优势
    advantages = resume.get("advantages", [])
    if advantages:
        lines.append("【岗位胜任】")
        for item in advantages:
            lines.append(f"- {item}")
        lines.append("")

    # 工作经历
    for work in resume.get("work_history", []):
        title = work.get("title", "")
        role = work.get("role", "")
        period = work.get("period", "")
        header = " | ".join([p for p in (title, role, period) if p])
        lines.append(f"【{header}】")
        for bullet in work.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    # 项目经历
    for proj in resume.get("projects", []):
        title = proj.get("title", "")
        role = proj.get("role", "")
        period = proj.get("period", "")
        header = " | ".join([p for p in (title, role, period) if p])
        lines.append(f"【项目：{header}】")
        for bullet in proj.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    # 技能
    skills = resume.get("skills", [])
    if skills:
        lines.append("【技能】")
        for skill in skills:
            lines.append(f"- {skill}")
        lines.append("")

    # 教育
    education = resume.get("education", [])
    if education:
        lines.append("【教育】")
        for edu in education:
            lines.append(f"- {edu}")
        lines.append("")

    return "\n".join(lines).strip()


def main():
    ap = argparse.ArgumentParser(description="简历渲染前确认闸门")
    ap.add_argument("--resume", help="resume.json 路径")
    ap.add_argument("--state", default="review_state.json", help="review 状态文件路径")
    ap.add_argument("--approve", action="store_true", help="用户确认渲染")
    ap.add_argument("--reject", action="store_true", help="用户要求修改")
    ap.add_argument("--feedback", default="", help="用户修改意见")
    ap.add_argument("--check", action="store_true", help="仅检查当前确认状态")
    args = ap.parse_args()

    state = load_state(args.state)

    if args.check:
        if state.get("render_approved"):
            print("✅ 已确认渲染")
            sys.exit(0)
        else:
            print("⏳ 等待用户确认渲染")
            sys.exit(2)

    if args.approve:
        state["render_approved"] = True
        state["feedback"] = ""
        state["approved_at"] = datetime.now().isoformat()
        save_state(args.state, state)
        print("✅ 已记录渲染确认")
        sys.exit(0)

    if args.reject:
        state["render_approved"] = False
        state["feedback"] = args.feedback
        state["approved_at"] = None
        save_state(args.state, state)
        print("📝 已记录修改意见，等待重新修改后再次确认")
        sys.exit(2)

    if not args.resume:
        raise SystemExit("[错误] 生成预览需要 --resume resume.json")

    resume = load_resume(args.resume)
    preview = format_resume_text(resume)

    # 重置 review 状态为待确认
    state = {
        "render_approved": False,
        "feedback": "",
        "approved_at": None,
        "resume_path": os.path.abspath(args.resume),
        "generated_at": datetime.now().isoformat(),
    }
    save_state(args.state, state)

    print(preview)
    print("\n" + "=" * 40)
    print("以上为简历文字稿预览。请确认内容无误后，再执行渲染。")
    print(f"review 状态已写入：{os.path.abspath(args.state)}")


if __name__ == "__main__":
    main()
