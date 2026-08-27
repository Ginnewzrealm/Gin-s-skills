#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cli.py — gin-resume-builder 统一 CLI 入口（协调层）。

每个子命令只 import 对应模块，不一次加载全部。
知识库路径统一从 config.yaml 读取，可用 --kb 覆盖。

用法:
    python3 cli.py <子命令> [参数...]
    python3 cli.py help                      # 列出全部子命令
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

# 知识库类子命令与 kb_interview 共用 common.KB_COMMANDS 单一来源，新增命令只需改 common
SCRIPTS = {cmd: ("kb_interview.py", desc) for cmd, desc in common.KB_COMMANDS.items()}
SCRIPTS.update({
    "facts": ("facts_parser.py", "重新生成 facts.yaml"),
    "analyze": ("jd_analyzer.py", "JD 匹配度分析（N8）"),
    "classify": ("jd_classifier.py", "JD Profile 分类"),
    "ats": ("ats_checker.py", "ATS 预检/诊断（N16）"),
    "select": ("fact_selector.py", "事实挑选（N9-⑥）"),
    "rewrite": ("bullet_rewriter.py", "X-Y-Z 改写硬事实层（N9-⑦）"),
    "verify": ("provenance_verifier.py", "溯源校验（N9-⑧）"),
    "render-html": ("html_renderer.py", "渲染 HTML 简历（N9-⑩）"),
    "render-md": ("markdown_renderer.py", "渲染 Markdown 简历"),
    "cover-letter": ("cover_letter_renderer.py", "求职信骨架（N10）"),
    "star-stories": ("star_story_generator.py", "STAR 故事库（N11）"),
    "interview": ("interview_prep_generator.py", "面试清单（N12）"),
    "executive": ("executive_resume_renderer.py", "高管简历（N13）"),
})

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        print("gin-resume-builder CLI 子命令：")
        for cmd, (script, desc) in SCRIPTS.items():
            print("  %-16s %s" % (cmd, desc))
        print("\n用法: python3 cli.py <子命令> [参数...]（参数透传给对应脚本）")
        return
    cmd = sys.argv[1]
    if cmd not in SCRIPTS:
        print("[错误] 未知子命令: %s（用 cli.py help 查看全部）" % cmd)
        sys.exit(1)
    script = os.path.join(HERE, SCRIPTS[cmd][0])
    argv = [sys.executable, script, cmd] + sys.argv[2:] if SCRIPTS[cmd][0] == "kb_interview.py" \
        else [sys.executable, script] + sys.argv[2:]
    sys.exit(subprocess.call(argv))


if __name__ == "__main__":
    main()
