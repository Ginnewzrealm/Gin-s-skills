#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_renderer.py — 渲染 HTML 简历（N9 第⑩步）。

输入 resume.json（由 Claude 在溯源校验通过后组装）：
{
  "title": "张三-高级后端工程师-简历",
  "basic": {"姓名": "张三", "电话": "138…", "邮箱": "…", "城市": "杭州", "求职意向": "高级后端工程师"},
  "sections": [
    {"title": "岗位胜任", "items": [{"tag": "渠道经营与大区管理能力（5 年经验）",
       "text": "做事方法论与价值主张……"}]},  # 双字段：能力标签 + 内容体现；置顶板块
    {"title": "工作经历", "entries": [{"org": "美团", "org_note": "行业 Top3",
       "role": "高级产品经理", "period": "2024.06-至今",
       "summary": "核心职责一句话",                  # → 标签【核心职责】
       "bullets": ["业绩增长：……"],                  # → 标签【关键业绩】
       "skills": "专业能力一行（可选）",               # → 标签【专业能力】
       "honor": "荣誉奖项一行（可选）"}]},             # → 标签【荣誉奖项】
    {"title": "项目经历", "entries": [{"org": "项目名", "role": "负责人", "period": "…",
       "description": "项目描述一句话",                # → 标签【项目描述】
       "bullets": ["方案设计：……"],                  # → 标签【职责与行动】
       "impact": "成果与影响一句话（可选）"}]},        # → 标签【成果与影响】
    {"title": "技能", "groups": [{"label": "商务能力", "items": ["商务谈判（熟练）"]}]},
    {"title": "技能", "items": ["Python（熟练）"]}    # groups/items 均渲染为圆点 bullet
  ]
}

bullet 若以前缀「能力小标题：」开头（前缀 ≤9 字符），自动加粗为小标题。
字段标签规则见 references/resume-section-standard.md；只有「工作经历」「项目经历」
两个板块会输出标签，其他板块（含高管英文板块）按无标签渲染。

渲染时自动把 bullet / 条目中的量化数字（带 %、ms、万、亿、倍、元、年 等单位的数字）
包成 <span class="metric"> 加粗，方便 HR 快速扫读。

用法:
    python3 html_renderer.py --resume resume.json [--kb 路径] [--out out.html]
"""
import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

TEMPLATE = os.path.join(common.SKILL_DIR, "assets", "resume_template.html")

# 展示层置顶板块（知识库存储层仍叫 advantages/个人优势，展示层统一为「岗位胜任」；
# 保留「核心亮点」「个人优势」兼容旧数据）
FRONT_SECTIONS = common.FRONT_SECTIONS

# 板块标题英文小字（展示层双语点缀，数据层仍纯中文）
EN_TITLE = {"岗位胜任": "CORE COMPETENCIES", "工作经历": "WORK EXPERIENCE",
            "项目经历": "SELECTED PROJECTS", "教育背景": "EDUCATION", "技能": "SKILLS"}

# 量化数字：数字 + 常见计量单位（长单位在前）。不匹配 P99、2021.03 这类字母/点号前的数字
METRIC_RE = common.METRIC_RE

# 字段标签：按板块标题决定每段经历的字段小标题（见 resume-section-standard.md）
SECTION_FIELDS = {
    "工作经历": {"summary": "核心职责", "bullets": "关键业绩",
                 "skills": "专业能力", "honor": "荣誉奖项"},
    "项目经历": {"description": "项目描述", "bullets": "职责与行动",
                 "impact": "成果与影响"},
}

# bullet 能力小标题：「用户增长：……」前缀自动加粗（≤32 字符，允许数字，
# 兼容岗位胜任的「渠道经营与大区管理能力（5 年经验）：……」长标签格式；
# 岗位胜任建议用 {"tag","text"} 双字段显式传入，不依赖正则切分）
TAG_RE = re.compile(r"(%s)(.*)$" % common.TAG_PATTERN[1:], re.S)


def esc(s):
    return html.escape(str(s), quote=False)


def rich(s):
    """转义文本，并把量化数字包成 .metric 加粗。"""
    return METRIC_RE.sub(r'<span class="metric">\1</span>', esc(s))


def rich_bullet(s):
    """bullet 渲染：能力小标题加粗 + 量化数字加粗。"""
    m = TAG_RE.match(str(s).strip())
    if m:
        return ('<span class="bullet-tag">%s</span>：%s'
                % (esc(m.group(1)), rich(m.group(2).strip())))
    return rich(s)


def rich_item(item):
    """板块 items 条目：{"tag","text"} 双字段显式渲染，纯文本走正则切分。"""
    if isinstance(item, dict):
        return ('<span class="bullet-tag">%s</span>：%s'
                % (rich(item.get("tag", "")), rich(item.get("text", ""))))
    return rich_bullet(item)


def field_line(label, text):
    """一行带字段标签的内容，如 【核心职责】……"""
    return ('<p class="field-line"><span class="field-label">%s</span>%s</p>'
            % (esc(label), rich(text)))


EDU_DEGREES = ["博士", "硕士", "MBA", "EMBA", "本科", "大专", "专科"]
EDU_RANK = {d: i for i, d in enumerate(EDU_DEGREES)}  # 数字越小，学历越高


def _extract_degree(text):
    """从文本中提取最高学历关键词（按 EDU_DEGREES 顺序匹配）。"""
    for d in EDU_DEGREES:
        if d in text:
            return d
    return ""


def _simplify_education(text):
    """简化教育背景：只保留学校 + 学历，去掉专业和时间。"""
    text = str(text).strip()
    if not text:
        return ""
    # 按常见分隔符切分：全角竖线、半角竖线、中英文分号、空格、逗号
    parts = re.split(r"[｜|;；\s,，]+", text)
    school = parts[0].strip() if parts else ""
    degree = _extract_degree(text)
    if school and degree:
        return "%s %s" % (school, degree)
    return text


def _pick_highest_education(text):
    """从可能包含多段学历的文本中，只保留最高学历。"""
    text = str(text).strip()
    if not text:
        return ""
    # 先按中英文分号拆成多条学历
    entries = re.split(r"[;；]+", text)
    candidates = []
    for entry in entries:
        simplified = _simplify_education(entry)
        if not simplified:
            continue
        degree = _extract_degree(simplified)
        rank = EDU_RANK.get(degree, 99)
        candidates.append((rank, simplified))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _education_text(section):
    """把教育背景 section 转换为单行简化文本，只取最高学历。"""
    candidates = []
    if section.get("entries"):
        for e in section["entries"]:
            org = e.get("org", "")
            role = e.get("role", "")
            degree = _extract_degree(role) or _extract_degree(org)
            if org and degree:
                candidates.append((EDU_RANK.get(degree, 99), "%s %s" % (org.strip(), degree)))
            elif org:
                candidates.append((99, org.strip()))
    if section.get("items"):
        for i in section["items"]:
            if isinstance(i, dict):
                text = "%s：%s" % (i.get("tag", ""), i.get("text", ""))
            else:
                text = str(i)
            simplified = _simplify_education(text)
            if simplified:
                degree = _extract_degree(simplified)
                candidates.append((EDU_RANK.get(degree, 99), simplified))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _is_gap_entry(e):
    """判断是否为职业空窗期条目。支持显式标记或组织名匹配。"""
    if e.get("is_gap") is True or e.get("type") == "career_gap":
        return True
    org = str(e.get("org", "")).strip().lower()
    return org in ("职业空窗期", "career break", "career gap") or "空窗期" in org


def _gap_fields(fields):
    """空窗期条目的字段标签覆盖：核心职责→核心说明，关键业绩→关键事实。"""
    gap_fields = dict(fields)
    gap_fields["summary"] = "核心说明"
    gap_fields["bullets"] = "关键事实"
    return gap_fields


def build_body(resume):
    basic = resume.get("basic", {})
    L = ['<header class="header"><h1 class="name">%s</h1>' % esc(basic.get("姓名", "（姓名）"))]

    sections = list(resume.get("sections", []))
    # 教育背景统一抽到 header 联系信息行末尾，并简化为“学校 学历”
    edu_text = basic.get("教育背景", "")
    edu_from_basic = bool(edu_text)
    for s in sections[:]:
        if s.get("title") == "教育背景":
            sections.remove(s)
            if not edu_text:
                edu_text = _education_text(s)
                edu_from_basic = False
            break
    # basic 里的原始字符串需要简化并只保留最高学历；section 派生的已经在 _education_text 中处理
    if edu_text and edu_from_basic:
        edu_text = _pick_highest_education(edu_text)

    contact = [esc(basic[k]) for k in ("电话", "邮箱", "城市", "求职意向") if basic.get(k)]
    if edu_text:
        contact.append(esc(edu_text))
    if contact:
        L.append('<div class="contact-row">%s</div>'
                 % "".join('<span class="contact-item">%s</span>' % c for c in contact))
    L.append("</header>")

    # 置顶板块：核心亮点/个人优势 固定排在联系方式之后、其他章节之前
    front = [s for s in sections if s.get("title") in FRONT_SECTIONS]
    rest = [s for s in sections if s.get("title") not in FRONT_SECTIONS]

    for sec in front + rest:
        title = sec["title"]
        fields = SECTION_FIELDS.get(title, {})
        en = EN_TITLE.get(title)
        en_span = '<span class="en">%s</span>' % en if en else ""
        L.append('<section class="section"><h2 class="section-title">%s%s</h2>' % (esc(title), en_span))
        for e in sec.get("entries", []):
            is_gap = _is_gap_entry(e)
            entry_fields = _gap_fields(fields) if is_gap else fields
            org = e.get("org", "")
            if e.get("org_note"):
                org += '<span class="org-note">（%s）</span>' % esc(e["org_note"])
            else:
                org = esc(org)
            role = ("｜" + e["role"]) if e.get("role") else ""
            entry_cls = "entry career-gap" if is_gap else "entry"
            L.append('<div class="%s"><div class="entry-header"><div class="entry-left">'
                     '<span class="entry-company">%s</span><span class="entry-position">%s</span></div>'
                     '<span class="entry-meta">%s</span></div>'
                     % (entry_cls, org, esc(role), esc(e.get("period", ""))))
            # 字段标签：summary/description → bullets → skills → impact → honor
            if e.get("summary"):
                L.append(field_line(entry_fields.get("summary", "核心职责"), e["summary"]))
            if e.get("description"):
                L.append(field_line(entry_fields.get("description", "项目描述"), e["description"]))
            if e.get("bullets"):
                if entry_fields.get("bullets"):
                    L.append('<p class="field-line field-label-only">'
                             '<span class="field-label">%s</span></p>' % esc(entry_fields["bullets"]))
                L.append('<ul class="bullet-list">'
                         + "".join("<li>%s</li>" % rich_bullet(b) for b in e["bullets"]) + "</ul>")
            if e.get("skills"):
                L.append(field_line(entry_fields.get("skills", "专业能力"), e["skills"]))
            if e.get("impact"):
                L.append(field_line(entry_fields.get("impact", "成果与影响"), e["impact"]))
            if e.get("honor"):
                L.append(field_line(entry_fields.get("honor", "荣誉奖项"), e["honor"]))
            L.append("</div>")
        if sec.get("groups"):
            L.append('<ul class="bullet-list">'
                     + "".join('<li><span class="bullet-tag">%s</span>：%s</li>'
                               % (rich(g.get("label", "")), rich("、".join(g.get("items", []))))
                               for g in sec["groups"])
                     + "</ul>")
        elif sec.get("items"):
            L.append('<ul class="bullet-list">'
                     + "".join("<li>%s</li>" % rich_item(i) for i in sec["items"]) + "</ul>")
        L.append("</section>")
    return "\n".join(L)


def render(resume):
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    title = resume.get("title", "简历")
    return tpl.replace("{{TITLE}}", esc(title)).replace("{{BODY}}", build_body(resume))


def main():
    ap = argparse.ArgumentParser(description="渲染 HTML 简历")
    ap.add_argument("--resume", required=True)
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.resume, encoding="utf-8") as f:
        resume = json.load(f)
    html_text = render(resume)
    if args.out:
        out = args.out
    else:
        root = common.kb_root(args.kb)
        out = common.out_path(root, "resumes", "%s-%s.html" % (resume.get("title", "简历"), common.stamp()))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("[完成] HTML 简历已生成: %s" % out)


if __name__ == "__main__":
    main()
