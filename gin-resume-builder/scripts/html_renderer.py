#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_renderer.py — 渲染 HTML 简历（N9 第⑩步）。

输入 resume.json（由 Claude 在溯源校验通过后组装）：
{
  "title": "张三-高级后端工程师-简历",
  "basic": {"姓名": "张三", "电话": "138…", "邮箱": "…", "城市": "杭州", "求职意向": "高级后端工程师", "学历": "本科", "年龄": "32岁"},
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
    {"title": "技能", "items": ["Python（熟练）"]}    # groups 使用两列，items 保留列表
  ]
}

bullet 若以前缀「能力小标题：」开头（前缀 ≤32 字符），自动渲染为小标题。
字段标签规则见 references/resume-section-standard.md；只有「工作经历」「项目经历」
两个板块会输出标签，其他板块（含高管英文板块）按无标签渲染。

正文数字使用普通字重；主题只改变版式，不删除字段。
正式渲染校验七项基本信息和岗位匹配/岗位胜任板块，缺项抛出 ValueError。

用法:
    python3 html_renderer.py --resume resume.json [--kb 路径] [--out out.html] [--theme minimal|bank|editorial] [--editable]
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

TEMPLATE = os.path.join(common.SKILL_DIR, "assets", "resume_template.html")

# 展示层置顶板块（知识库存储层仍叫 advantages/个人优势，展示层统一为「岗位胜任」；
# 保留「核心亮点」「个人优势」兼容旧数据）
FRONT_SECTIONS = common.FRONT_SECTIONS

# 板块标题英文小字（展示层双语点缀，数据层仍纯中文）
EN_TITLE = {"岗位匹配": "CORE COMPETENCIES", "岗位胜任": "CORE COMPETENCIES", "工作经历": "WORK EXPERIENCE",
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
TAG_RE = re.compile(r"([^：:]{1,32})[：:](.*)$", re.S)


def esc(s):
    return html.escape(str(s), quote=False)


def rich(s):
    """转义文本；数字保留普通正文样式。"""
    return esc(s)


def rich_bullet(s):
    """能力小标题独立标记，正文与数字保持普通字重。"""
    m = TAG_RE.match(str(s).strip())
    if m:
        return ('<span class="bullet-tag">%s</span>：%s'
                % (esc(m.group(1)), rich(m.group(2).strip())))
    return rich(s)


def rich_item(item):
    """板块 items 条目：{"tag","text"} 双字段显式渲染，纯文本走正则切分。"""
    if isinstance(item, dict):
        return ('<span class="bullet-tag">%s</span>：%s'
                % (rich(str(item.get("tag", "")).rstrip("：: ")), rich(item.get("text", ""))))
    return rich_bullet(item)


def field_content(text):
    """Preserve existing inline labels separated by semicolons; never invent labels."""
    parts = re.split(r"([；;\n])", str(text))
    result = []
    for part in parts:
        match = re.match(r"^([^：:；;。\n]{1,32})([：:])(.*)$", part, re.S)
        if match:
            result.append('<span class="ability-tag">%s</span>%s%s' %
                          (esc(match[1]), esc(match[2]), esc(match[3])))
        else:
            result.append(esc(part))
    return "".join(result)


def item_text(item):
    if isinstance(item, dict):
        return "%s：%s" % (str(item.get("tag", "")).rstrip("：: "), item.get("text", ""))
    return str(item)


def field_line(label, text):
    """一行带字段标签的内容，如 【核心职责】……"""
    return ('<p class="field-line"><span class="field-label">%s</span><span class="field-content">%s</span></p>'
            % (esc(label), field_content(text)))


def _education_section(education):
    """兼容顶层 education；完整保留学校、学历、专业、时间。"""
    if not isinstance(education, list):
        education = [education]
    entries = []
    for item in education:
        if isinstance(item, dict):
            entry = dict(item)
            entry["org"] = item.get("org") or item.get("school", "")
            entry["role"] = "｜".join(str(v) for v in
                                      (item.get("role"), item.get("major"), item.get("degree")) if v)
            entry["period"] = item.get("period") or item.get("dates", "")
            if not entry["org"] and item.get("text"):
                entry["org"] = "：".join(str(v) for v in (item.get("tag"), item["text"]) if v)
        else:
            entry = {"org": str(item)}
        entries.append(entry)
    return {"title": "教育背景", "entries": entries}


GAP_TITLES = {"职业休整期", "职业空窗期", "career break", "career gap"}
GAP_DISPLAY = "职业休整期"


def _is_gap_entry(e):
    """判断是否为职业休整期条目。支持显式标记或组织名匹配。"""
    if e.get("is_gap") is True or e.get("type") == "career_gap":
        return True
    return str(e.get("org", "")).strip().lower() in GAP_TITLES


def _gap_fields(fields):
    """休整期条目的字段标签覆盖：核心职责→核心说明，关键业绩→关键事实。"""
    gap_fields = dict(fields)
    gap_fields["summary"] = "核心说明"
    gap_fields["bullets"] = "关键事实"
    return gap_fields


HEADER_ALIASES = {
    "姓名": ("姓名",),
    "联系电话": ("联系电话", "电话"),
    "邮箱": ("邮箱",),
    "居住地": ("居住地", "城市"),
    "职位": ("求职意向", "求职职位", "职位"),
    "年龄": ("年龄",),
}


def effective_sections(resume):
    """Keep full education records; only synthesize a section for legacy input."""
    sections = list(resume.get("sections", []))
    basic = resume.get("basic", {})
    if (resume.get("education") and not (basic.get("教育背景") or basic.get("学历"))
            and not any(sec.get("title") == "教育背景" for sec in sections)):
        sections.append(_education_section(resume["education"]))
    return sections


def normalized_header(resume):
    """Resolve aliases once, so validation and output use identical values."""
    basic = resume.get("basic", {})
    values = {}
    for label, aliases in HEADER_ALIASES.items():
        values[label] = next((str(basic[k]).strip() for k in aliases
                              if basic.get(k) is not None and str(basic[k]).strip()), "")
    education = str(basic.get("教育背景") or basic.get("学历") or "").strip()
    if not education:
        for section in effective_sections(resume):
            if section.get("title") == "教育背景":
                items = [" ".join(str(e[k]) for k in ("org", "role") if e.get(k))
                         for e in section.get("entries", [])]
                items.extend(item_text(i) for i in section.get("items", []))
                education = "；".join(i for i in items if i.strip())
                if education:
                    break
    values["学历"] = education
    return values


def required_content_errors(resume):
    """Missing facts are reported, never invented or silently omitted."""
    errors = ["缺少基本信息：%s" % key for key, value in normalized_header(resume).items() if not value]
    front = [sec for sec in resume.get("sections", []) if sec.get("title") in FRONT_SECTIONS]
    def usable(item):
        if isinstance(item, dict):
            return bool(str(item.get("tag") or "").strip() and str(item.get("text") or "").strip())
        return bool(str(item or "").strip())
    if not any(sec.get("items") and all(usable(item) for item in sec["items"]) for sec in front):
        errors.append("缺少或为空：岗位匹配/岗位胜任板块")
    return errors


def build_body(resume):
    basic = normalized_header(resume)
    L = ['<header class="header"><h1 class="name">%s</h1>' % esc(basic["姓名"] or "（姓名）")]
    sections = effective_sections(resume)
    contact = [esc(basic[k]) for k in ("联系电话", "邮箱", "居住地", "职位", "学历", "年龄") if basic[k]]
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
        section_kind = ("competencies" if title in FRONT_SECTIONS else
                        {"工作经历": "work", "项目经历": "projects", "技能": "skills", "专业技能": "skills", "专业能力": "skills"}.get(title, "other"))
        L.append('<section class="section" data-section="%s"><h2 class="section-title">%s%s</h2>' % (section_kind, esc(title), en_span))
        for e in sec.get("entries", []):
            is_gap = _is_gap_entry(e)
            entry_fields = _gap_fields(fields) if is_gap else fields
            org = esc(e.get("org", ""))
            if is_gap:
                org = GAP_DISPLAY
            if e.get("org_note"):
                org += '<span class="org-note">（%s）</span>' % esc(e["org_note"])
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
                         + "".join("<li>%s</li>" % rich_item(b) for b in e["bullets"]) + "</ul>")
            if e.get("skills"):
                L.append(field_line(entry_fields.get("skills", "专业能力"), e["skills"]))
            if e.get("impact"):
                L.append(field_line(entry_fields.get("impact", "成果与影响"), e["impact"]))
            if e.get("honor"):
                L.append(field_line(entry_fields.get("honor", "荣誉奖项"), e["honor"]))
            L.append("</div>")
        if sec.get("groups"):
            L.append('<div class="skills-grid">'
                     + "".join('<div class="skill-label">%s</div><div class="skill-content">%s</div>'
                               % (rich(g.get("label", "")), rich("、".join(g.get("items", []))))
                               for g in sec["groups"])
                     + "</div>")
        elif sec.get("items"):
            L.append('<ul class="bullet-list">'
                     + "".join("<li>%s</li>" % rich_item(i) for i in sec["items"]) + "</ul>")
        L.append("</section>")
    return "\n".join(L)


def _editable_template_path():
    return os.path.join(common.SKILL_DIR, "assets", "editable_resume_base.html")


def _make_editable(body_html):
    """给 body 中的文本容器添加 edit-block 与 contenteditable 属性。"""
    # 给无 class 的 block 元素添加 edit-block；保留已有 class 的元素
    def add_edit_block(m):
        tag = m.group(1) or m.group(3)
        attrs = m.group(2) if m.group(1) else m.group(4)
        if 'class="' in attrs:
            attrs = attrs.replace('class="', 'class="edit-block ')
        else:
            attrs += ' class="edit-block"'
        return '<%s%s contenteditable="true">' % (tag, attrs)

    # 顶部联系信息及经历头部也是叶子文本容器，必须能编辑教育字段。
    pattern = re.compile(
        r'<(h1|h2|p|li)([^>]*)>|<(span)([^>]*class="(?:contact-item|entry-company|entry-position|entry-meta)"[^>]*)>'
    )
    body_html = pattern.sub(add_edit_block, body_html)
    return body_html


def _render_editable(resume, theme="minimal"):
    """Compatibility entry point; editable output uses the locked template."""
    return render(resume, editable=True, theme=theme)


def render(resume, editable=False, theme=None, validate=True):
    theme = theme or resume.get("theme", "minimal")
    if theme not in ("minimal", "bank", "editorial"):
        raise ValueError("未知 theme：%s" % theme)
    if validate:
        errors = required_content_errors(resume)
        if errors:
            raise ValueError("；".join(errors))
    template_path = _editable_template_path() if editable else TEMPLATE
    tpl = Path(template_path).read_text(encoding="utf-8")
    title = resume.get("title", "简历")
    result = tpl.replace("{{TITLE}}", esc(title)).replace("{{BODY}}", build_body(resume))
    css_class = "" if theme == "minimal" else "theme-" + theme
    result = result.replace('<body>', '<body class="%s" data-theme="%s">' % (css_class, theme), 1)
    result = result.replace('<div class="page" id="page" contenteditable="true"', '<div class="page" id="page" contenteditable="%s"' % str(editable).lower(), 1)
    if editable:
        result = result.replace('导出 PDF</button>', '生成 PDF</button>')
    return result


def _resume_to_markdown(resume):
    """把简历数据结构转成中性的 Markdown，用于基础简历.md。"""
    lines = ["# 基础简历\n", ""]
    basic = resume.get("basic", {})
    if basic:
        lines.append("## 基本信息\n")
        for k, v in basic.items():
            lines.append("- %s：%s\n" % (k, v))
        lines.append("\n")
    sections = effective_sections(resume)
    ordered = [sec for sec in sections if sec.get("title") in FRONT_SECTIONS] + [sec for sec in sections if sec.get("title") not in FRONT_SECTIONS]
    for sec in ordered:
        title = sec.get("title", "")
        lines.append("## %s\n" % title)
        if sec.get("items"):
            for item in sec["items"]:
                if isinstance(item, dict):
                    lines.append("- %s：%s\n" % (item.get("tag", ""), item.get("text", "")))
                else:
                    lines.append("- %s\n" % item)
        for group in sec.get("groups", []):
            lines.append("- %s：%s\n" % (group.get("label", ""), "、".join(group.get("items", []))))
        for e in sec.get("entries", []):
            org = e.get("org", "")
            role = e.get("role", "")
            period = e.get("period", "")
            header = " ".join(p for p in [org, "｜" + role if role else "", period] if p)
            lines.append("- %s\n" % header)
            if e.get("summary"):
                lines.append("  - 核心职责：%s\n" % e["summary"])
            if e.get("description"):
                lines.append("  - 项目描述：%s\n" % e["description"])
            if e.get("bullets"):
                lines.append("  - %s：\n" % SECTION_FIELDS.get(title, {}).get("bullets", "主要内容"))
            for b in e.get("bullets", []):
                lines.append("  - %s\n" % item_text(b))
            if e.get("skills"):
                lines.append("  - 专业能力：%s\n" % e["skills"])
            if e.get("impact"):
                lines.append("  - 成果与影响：%s\n" % e["impact"])
            if e.get("honor"):
                lines.append("  - 荣誉奖项：%s\n" % e["honor"])
        lines.append("\n")
    return "".join(lines)


def _style_to_markdown(style_profile):
    """把版式参数转成 Markdown，用于简历版式档案.md。"""
    lines = ["# 简历版式档案\n", ""]
    lines.append("本文件记录当前默认简历的视觉与结构参数，便于后续复用。\n\n")
    for k, v in sorted(style_profile.items()):
        lines.append("- %s：%s\n" % (k, v))
    lines.append("\n最后确认日期：%s\n" % date.today().isoformat())
    return "".join(lines)


def save_workspace(resume, style_profile, base_html_path):
    """保存可复用工作空间文件。

    输出：
    - 基础简历.md
    - 简历版式档案.md
    - 基础简历.html（可编辑母版）
    """
    root = Path(base_html_path).parent
    base_md = root / "基础简历.md"
    style_md = root / "简历版式档案.md"

    html_text = render(resume, editable=True, theme=style_profile.get("theme"))
    base_md.write_text(_resume_to_markdown(resume), encoding="utf-8")
    style_md.write_text(_style_to_markdown(style_profile), encoding="utf-8")

    # 校验已通过，保存可编辑母版
    with open(base_html_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    return base_md, style_md, Path(base_html_path)


def main():
    ap = argparse.ArgumentParser(description="渲染 HTML 简历")
    ap.add_argument("--resume", required=True)
    ap.add_argument("--kb", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--editable", action="store_true", help="生成可编辑 HTML")
    ap.add_argument("--theme", choices=["minimal", "bank", "editorial"], default=None, help="视觉主题（默认读取 resume.theme，否则 minimal）")
    args = ap.parse_args()
    with open(args.resume, encoding="utf-8") as f:
        resume = json.load(f)
    try:
        html_text = render(resume, editable=args.editable, theme=args.theme)
    except ValueError as exc:
        print("[失败] %s" % exc, file=sys.stderr)
        return 2
    if args.out:
        out = args.out
    else:
        root = common.kb_root(args.kb)
        filename = "%s-%s.html" % (resume.get("title", "简历"), common.stamp())
        out = common.out_path(root, "生成物", filename)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("[完成] HTML 简历已生成: %s" % out)


if __name__ == "__main__":
    sys.exit(main())
