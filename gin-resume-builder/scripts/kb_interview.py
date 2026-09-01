#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_interview.py — 知识库录入与增量更新（N5/N6 的文件操作层）。

设计约束（来自 SOP）：
- 追加写入，不覆盖；冲突时（同公司+同时间段）exit code 2 并打印冲突，由 Claude 展示给用户裁决。
- 每次写入后自动重生成 facts.yaml、meta.json 版本号 +1、追加 changelog。

用法:
    python3 kb_interview.py init [--kb 路径]                 # 初始化目录结构
    python3 kb_interview.py set-basic --data '姓名=张三;城市=杭州' [--kb 路径]
    python3 kb_interview.py append-work --company 美团 --role 高级产品经理 \
        --period '2024.06-至今' --bullets '负责……;达成……' [--kb 路径]
    python3 kb_interview.py append-project --name 增长项目 --role 负责人 \
        --period '2023.01-2023.12' --bullets '……;……' [--kb 路径]
    python3 kb_interview.py append-skill --text 'Python（熟练）' [--kb 路径]
    python3 kb_interview.py append-skill --type general --text '沟通（证据：强）｜场景：……' [--kb 路径]
    python3 kb_interview.py append-advantage --text '跨部门协同：擅长在多方冲突中寻找共赢方案' [--kb 路径]
    python3 kb_interview.py mine --kb 路径 --domain work_experience --source "公司-职位"     # 启动 STAR 深挖
    python3 kb_interview.py validate-skill --kb 路径 --text "技能名"                         # 校验 STAR 证据
    python3 kb_interview.py list-skills [--kb 路径]             # 按通用/专属两段查看技能清单
    python3 kb_interview.py summary [--kb 路径]

退出码: 0 成功 / 2 检测到冲突（未写入）
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import facts_parser
from mining import TacitMiner, SkillValidator


def _radar_reference_path():
    return os.path.join(common.SKILL_DIR, "references", "career-value-radar.md")


def career_value_radar_prompts():
    """从 references/career-value-radar.md 加载高价值提示。"""
    path = _radar_reference_path()
    prompts = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("-"):
            prompts.append(line.lstrip("- ").strip())
    return prompts


def _append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def _post_write(root, action_desc):
    """写入后收尾：统一走 facts_parser.post_write 审计链（facts 重建 + meta+1 + changelog）。"""
    _, ver = facts_parser.post_write(root, action_desc)
    print("[完成] %s；facts.yaml 已更新，版本 v%d" % (action_desc, ver))


def _check_work_conflict(root, company, period):
    """冲突检测：同公司 + 时间段重叠 → 返回冲突条目列表。"""
    conflicts = []
    for e in common.parse_entries(common.read_raw(root, "work_history")):
        if e["title"] == company:
            conflicts.append(e)
    # 同公司即提示复核（时间段精确重叠判断交给 Claude 与用户裁决）
    return conflicts


def cmd_init(root):
    created = common.ensure_kb_structure(root)
    if created:
        print("[完成] 已创建知识库结构：%d 项" % len(created))
    else:
        print("[完成] 知识库结构已存在，无需创建")


def cmd_set_basic(root, data):
    pairs = [p.strip() for p in re.split(r"[;；]", data) if "=" in p]
    if not pairs:
        raise SystemExit("[错误] --data 格式应为 '键=值;键=值'")
    path = os.path.join(root, common.DIR_RAW, "basic_info.md")
    for p in pairs:
        k, v = p.split("=", 1)
        _append(path, "- %s: %s\n" % (k.strip(), v.strip()))
    _post_write(root, "更新基本信息（%d 项）" % len(pairs))


def cmd_append_work(root, company, role, period, bullets):
    conflicts = _check_work_conflict(root, company, period)
    if conflicts:
        print("[冲突] 检测到同公司已有记录，请与用户确认保留哪份或如何合并：")
        for c in conflicts:
            print("  已有：%s | %s | %s" % (c["title"], c["role"], c["period"]))
            for b in c["bullets"]:
                print("    - %s" % b)
        print("  新增：%s | %s | %s" % (company, role, period))
        sys.exit(2)
    path = os.path.join(root, common.DIR_RAW, "work_history.md")
    _append(path, "\n## %s | %s | %s\n" % (company, role, period))
    for b in [x.strip() for x in re.split(r"[;；]", bullets) if x.strip()]:
        _append(path, "- %s\n" % b)
    _post_write(root, "追加工作经历：%s %s" % (company, role))


def cmd_append_project(root, name, role, period, bullets):
    path = os.path.join(root, common.DIR_RAW, "projects.md")
    _append(path, "\n## %s | %s | %s\n" % (name, role, period))
    for b in [x.strip() for x in re.split(r"[;；]", bullets) if x.strip()]:
        _append(path, "- %s\n" % b)
    _post_write(root, "追加项目经历：%s" % name)


def cmd_append_skill(root, text, skill_type="domain"):
    """追加技能到对应分段（通用能力/专属能力），无分节旧格式自动建段。"""
    section = "通用能力" if skill_type == "general" else "专属能力"
    path = os.path.join(root, common.DIR_RAW, "skills.md")
    content = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read()
    titles = [e["title"] for e in common.parse_entries(content)]
    if section not in titles:
        if content.strip() and not content.endswith("\n"):
            content += "\n"
        content += "\n## %s\n" % section
    # 迁移：首个 ## 之前的游离 bullet（旧格式残留）统一并入专属能力段
    lines = content.splitlines()
    first_h = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    loose = [l for l in lines[:first_h] if l.startswith("- ")]
    if loose:
        lines = [l for l in lines[:first_h] if not l.startswith("- ")] + lines[first_h:]
        idx = next((i for i, l in enumerate(lines) if l.startswith("## ") and l[3:].split("|")[0].strip() == "专属能力"), None)
        if idx is None:
            lines.append("## 专属能力")
            idx = len(lines) - 1
        lines[idx + 1:idx + 1] = loose
    out, in_target, inserted = [], False, False
    for line in lines:
        if line.startswith("## "):
            if in_target and not inserted:
                out.append("- %s" % text)
                inserted = True
            in_target = (line[3:].split("|")[0].strip() == section)
        out.append(line)
    if not inserted:
        out.append("- %s" % text)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    _post_write(root, "追加%s：%s" % ("通用能力" if skill_type == "general" else "技能", text))


def cmd_append_advantage(root, text):
    """追加个人优势/岗位胜任条目到 advantages.md。"""
    _append(os.path.join(root, common.DIR_RAW, "advantages.md"), "- %s\n" % text)
    _post_write(root, "追加优势：%s" % text)


def cmd_list_skills(root):
    """按「通用能力/专属能力」两段列出全部已确认技能（只读）。"""
    content = common.read_raw(root, "skills")
    sections = common.parse_entries(content)
    if sections:
        total = sum(len(e["bullets"]) for e in sections)
        print("技能清单（共 %d 条）：" % total)
        for e in sections:
            print("  【%s】%d 条" % (e["title"], len(e["bullets"])))
            for i, s in enumerate(e["bullets"], 1):
                print("    %d. %s" % (i, s))
        if not total:
            print("  （空）按 references/skills-inventory-standard.md 的确认门禁录入")
        return
    skills = common.parse_bullet_list(content)
    print("技能清单（共 %d 条，旧格式未分段，全部为专属能力）：" % len(skills))
    for i, s in enumerate(skills, 1):
        print("  %d. %s" % (i, s))
    if not skills:
        print("  （空）按 references/skills-inventory-standard.md 的确认门禁录入")


def cmd_summary(root):
    data = facts_parser.build_facts(root)
    works = [f for f in data["facts"] if f["type"] == "work"]
    projs = [f for f in data["facts"] if f["type"] == "project"]
    print("知识库摘要（%s）" % root)
    print("  基本信息：%d 项" % len(data["basic_info"]))
    for w in works:
        print("  [工作] %s | %s | %s（%.1f 年，%d 条）" % (w["company"], w["role"], w["period"], w["years"], len(w["bullets"])))
    for p in projs:
        print("  [项目] %s | %s | %s（%d 条）" % (p["name"], p["role"], p["period"], len(p["bullets"])))
    ss = data.get("skills_structured", {})
    be = len(data.get("behavioral_evidence", []))
    print("  技能 %d 条（通用 %d / 专属 %d）/ 优势 %d 条 / 行为证据 %d 条 / 总工作年限 %.1f 年"
          % (len(data["skills"]), len(ss.get("通用能力", [])), len(ss.get("专属能力", [])),
             len(data["advantages"]), be, data["total_years"]))


def cmd_mine(root, domain, source, description, radar=False):
    """启动一次 STAR 深挖会话（tacit-mining 模式）。"""
    if radar:
        print("\n## 经历价值雷达（可选深挖方向）\n")
        for p in career_value_radar_prompts()[:8]:
            print("- %s" % p)
        print()
    miner = TacitMiner(root, domain, source)
    print(miner.next_question(""))
    # 实际对话由 Claude 调用本命令的多次交互完成；这里输出第一个问题。


def cmd_validate_skill(root, skill_name):
    """校验某技能的熟练度证据是否足够。"""
    v = SkillValidator(root)
    r = v.validate(skill_name)
    print("技能：%s" % r["skill"])
    print("已声明：%s" % (r["declared"] or "未声明"))
    print("证据数：%d" % r["count"])
    print("建议熟练度：%s" % r["suggested"])
    if r["overclaim"]:
        print("[警告] 已声明档位高于证据支撑，建议降级或继续挖掘")


def main():
    ap = argparse.ArgumentParser(description="知识库录入与增量更新")
    ap.add_argument("command", choices=list(common.KB_COMMANDS))
    ap.add_argument("--kb", default=None)
    ap.add_argument("--data", default="")
    ap.add_argument("--company", default="")
    ap.add_argument("--role", default="")
    ap.add_argument("--period", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--bullets", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--type", choices=["general", "domain"], default="domain",
                    help="append-skill 专用：general=通用能力段，domain=专属能力段（默认）")
    ap.add_argument("--domain", default="work_experience",
                    help="mine 专用：挖掘域 work_experience/project_experience/skill_mastery/advantage_evidence")
    ap.add_argument("--source", default="", help="mine 专用：来源标识，如'公司-职位'")
    ap.add_argument("--description", default="", help="mine 专用：本轮挖掘主题描述")
    ap.add_argument("--radar", action="store_true", help="mine 专用：在 STAR 深挖前先输出经历价值雷达提示")
    args = ap.parse_args()
    root = common.kb_root(args.kb)

    if args.command == "init":
        cmd_init(root)
    elif args.command == "set-basic":
        cmd_set_basic(root, args.data)
    elif args.command == "append-work":
        cmd_append_work(root, args.company, args.role, args.period, args.bullets)
    elif args.command == "append-project":
        cmd_append_project(root, args.name, args.role, args.period, args.bullets)
    elif args.command == "append-skill":
        cmd_append_skill(root, args.text, args.type)
    elif args.command == "append-advantage":
        cmd_append_advantage(root, args.text)
    elif args.command == "list-skills":
        cmd_list_skills(root)
    elif args.command == "summary":
        cmd_summary(root)
    elif args.command == "mine":
        cmd_mine(root, args.domain, args.source, args.description, radar=args.radar)
    elif args.command == "validate-skill":
        cmd_validate_skill(root, args.text)


if __name__ == "__main__":
    main()
