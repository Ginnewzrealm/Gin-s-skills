#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gin-resume-builder 公共工具层：配置读取、知识库解析、JD 关键词提取、日期处理。
所有脚本模块共用；本模块不依赖任何其他模块。仅用标准库。
"""
import json
import os
import re
from datetime import date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.yaml")

# 知识库标准目录（见 references/knowledge-structure.md）
DIR_RAW = "原始事实"
DIR_AUTO = "自动生成"
DIR_INTERVIEW = "面试素材"
DIR_OUTPUT = "生成物"
DIR_STAGED = "待确认"
CLAIMS_DIR = os.path.join(DIR_RAW, "claims")
CLAIMS_AGGREGATE = "claims.json"

# Claim 字段标准（见 references/knowledge-structure.md）
CLAIM_FIELDS = (
    "id",
    "section",
    "section_id",
    "source_fact",
    "candidate_wording",
    "responsibility_level",
    "verification_status",
    "allowed_uses",
    "interview_details",
    "boundary",
    "risk_notes",
    "last_verified",
)

RAW_FILES = {
    "basic_info": "basic_info.md",
    "work_history": "work_history.md",
    "projects": "projects.md",
    "skills": "skills.md",
    "skill_details": "skill_details.md",
    "advantages": "advantages.md",
    "internal_notes": "internal_notes.md",
}

# kb_interview 子命令单一来源（argparse choices 与 cli.py 调度都读这里，新增命令只改这一处）
KB_COMMANDS = {
    "init": "初始化知识库目录结构",
    "set-basic": "写入/更新基本信息",
    "append-work": "追加工作经历（含冲突检测）",
    "append-project": "追加项目经历",
    "append-skill": "追加技能（须用户确认后写入）",
    "append-advantage": "追加个人优势/岗位胜任条目",
    "list-skills": "查看技能清单",
    "summary": "知识库摘要",
    "mine": "启动 STAR 隐性知识挖掘会话",
    "save-evidence": "把用户确认后的 STAR 行为证据直接写入知识库",
    "stage-evidence": "把整理好的 STAR 证据先写入待确认区",
    "confirm-evidence": "把待确认证据迁移到 behavioral_evidence/",
    "reject-evidence": "删除待确认证据",
    "list-staged": "列出待确认证据",
    "validate-skill": "校验技能 STAR 证据是否足够",
}

OUTPUT_SUBDIRS = [
    "resumes", "target_roles", "cover_letters", "interview_prep",
    "executive_resumes", "cold_emails", "app_forms", "ats_reports",
]

# 简历渲染与结构校验共享常量（单一来源，见 references/resume-section-standard.md）
# 数字 + 常见计量单位，用于高亮/校验量化指标
METRIC_RE = re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"(\d+(?:\.\d+)?\s?(?:万元|亿元|QPS|qps|TPS|tps|ms|%|万|亿|倍|元|年|k|K|w|W|\+))"
)
# 能力小标题：≤32 字 + 全角/半角冒号
TAG_PATTERN = r"^[^：:]{1,32}："
# 置顶板块候选名
FRONT_SECTIONS = ("岗位胜任", "核心亮点", "个人优势")

# 责任层级标准（由低到高）
RESPONSIBILITY_LEVELS = ("参与", "负责模块", "主导方案或交付", "项目负责人")
RESPONSIBILITY_ALIASES = {
    "参与": "参与",
    "负责": "负责模块",
    "负责模块": "负责模块",
    "主导": "主导方案或交付",
    "主导方案": "主导方案或交付",
    "主导方案或交付": "主导方案或交付",
    "项目负责人": "项目负责人",
    "负责人": "项目负责人",
    "Owner": "项目负责人",
}
DEFAULT_VERIFICATION_STATUS = "待确认"
_RESPONSIBILITY_RE = re.compile(
    r"^\*\*\[(" + "|".join(re.escape(k) for k in sorted(RESPONSIBILITY_ALIASES.keys(), key=len, reverse=True)) + r")\]\*\*\s*[：:]?\s*"
)


def extract_responsibility_level(bullet):
    """从 bullet 文本中提取责任层级前缀，返回 (标准层级, 去掉前缀后的文本)。
    无层级时返回 ('', 原文本)。"""
    m = _RESPONSIBILITY_RE.match(str(bullet).strip())
    if m:
        return RESPONSIBILITY_ALIASES[m.group(1)], bullet[m.end():].strip()
    return "", str(bullet).strip()

# JD 关键词提取用的技术与能力词表（可按需扩充）
TECH_VOCAB = [
    "Python", "Java", "Go", "Golang", "C++", "JavaScript", "TypeScript", "Rust",
    "Redis", "Kafka", "MySQL", "PostgreSQL", "MongoDB", "Elasticsearch", "Docker",
    "Kubernetes", "K8s", "Linux", "AWS", "GCP", "Azure", "Spark", "Flink", "Hadoop",
    "React", "Vue", "Node.js", "Django", "Flask", "Spring", "微服务", "高并发",
    "分布式", "机器学习", "深度学习", "大模型", "LLM", "NLP", "CV", "推荐系统",
    "数据分析", "AB测试", "A/B测试", "SQL", "Excel", "SQL", "Tableau", "PowerBI",
]
ABILITY_VOCAB = [
    "项目管理", "团队管理", "跨部门协作", "客户成功", "商务拓展", "BD", "增长",
    "用户增长", "私域", "电商", "供应链", "财务分析", "预算管理", "绩效考核",
    "招聘", "培训", "品牌", "市场营销", "内容运营", "活动策划", "渠道管理",
    "售前", "售后", "客户沟通", "需求分析", "产品设计", "PRD", "竞品分析",
    "数据分析", "指标体系", "OKR", "KPI", "敏捷", "Scrum",
]


def load_config():
    """读取技能目录 config.yaml（简单 key: value 格式），返回 dict。"""
    cfg = {"kb_path": ""}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^(\w+)\s*:\s*(.*)$", line.strip())
                if m:
                    cfg[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return cfg


def kb_root(cli_kb=None):
    """解析知识库根路径：CLI 参数优先，其次 config.yaml。"""
    path = cli_kb or load_config().get("kb_path") or ""
    if not path:
        raise SystemExit("[错误] 未配置知识库路径。请用 --kb 指定，或在 config.yaml 写入 kb_path。")
    return os.path.abspath(os.path.expanduser(path))


def ensure_kb_structure(root):
    """初始化标准知识库目录结构，返回新建了哪些目录。"""
    created = []
    for d in (DIR_RAW, DIR_AUTO, DIR_INTERVIEW, DIR_OUTPUT):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            os.makedirs(p, exist_ok=True)
            created.append(p)
    for sub in OUTPUT_SUBDIRS:
        os.makedirs(os.path.join(root, DIR_OUTPUT, sub), exist_ok=True)
    for key, fname in RAW_FILES.items():
        p = os.path.join(root, DIR_RAW, fname)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                f.write("# %s\n" % key)
            created.append(p)
    # 主张（Claim）记录目录
    claims_dir = os.path.join(root, CLAIMS_DIR)
    if not os.path.isdir(claims_dir):
        os.makedirs(claims_dir, exist_ok=True)
        created.append(claims_dir)
    return created


def kb_structure_ok(root):
    """检查知识库结构完整性（N3 判定逻辑）。"""
    return os.path.isdir(os.path.join(root, DIR_RAW)) and os.path.isdir(os.path.join(root, DIR_AUTO))


def read_raw(root, key):
    p = os.path.join(root, DIR_RAW, RAW_FILES[key])
    if not os.path.exists(p):
        return ""
    with open(p, encoding="utf-8") as f:
        return f.read()


def _claims_path(root):
    return os.path.join(root, CLAIMS_DIR)


def _claim_file_path(root, claim_id):
    return os.path.join(root, CLAIMS_DIR, "%s.json" % claim_id)


def _aggregate_path(root):
    return os.path.join(root, CLAIMS_DIR, CLAIMS_AGGREGATE)


def read_claims(root):
    """读取所有单个 claim 文件，返回按 claim_id 排序的列表。"""
    d = _claims_path(root)
    if not os.path.isdir(d):
        return []
    claims = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json") or name == CLAIMS_AGGREGATE:
            continue
        p = os.path.join(d, name)
        try:
            with open(p, encoding="utf-8") as f:
                claims.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return claims


def write_claim(root, claim, update_aggregate=True):
    """写入单个 claim 文件，并自动维护 claims.json 汇总文件。"""
    missing = [f for f in CLAIM_FIELDS if f not in claim]
    if missing:
        raise ValueError("claim 缺少必填字段: %s" % ", ".join(missing))
    if not isinstance(claim.get("id"), str) or not claim["id"]:
        raise ValueError("claim['id'] 必须是非空字符串")
    os.makedirs(_claims_path(root), exist_ok=True)
    p = _claim_file_path(root, claim["id"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(claim, f, ensure_ascii=False, indent=2)
    if update_aggregate:
        _update_claims_aggregate(root)
    return p


def write_claims(root, claims):
    """批量写入 claim 文件并重建汇总文件。"""
    d = _claims_path(root)
    os.makedirs(d, exist_ok=True)
    for claim in claims:
        write_claim(root, claim, update_aggregate=False)
    _update_claims_aggregate(root)


def _update_claims_aggregate(root):
    """把所有单个 claim 文件汇总成 claims.json。"""
    with open(_aggregate_path(root), "w", encoding="utf-8") as f:
        json.dump(read_claims(root), f, ensure_ascii=False, indent=2)


def parse_entries(md_text):
    """解析 '## 标题 | 角色 | 时间段' 结构的 Markdown，返回条目列表。
    每个条目: {title, role, period, bullets[], responsibility_levels[]}"""
    entries = []
    cur = None
    for line in md_text.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            parts = [p.strip() for p in line[3:].split("|")]
            cur = {
                "title": parts[0] if parts else "",
                "role": parts[1] if len(parts) > 1 else "",
                "period": parts[2] if len(parts) > 2 else "",
                "bullets": [],
                "responsibility_levels": [],
            }
            entries.append(cur)
        elif line.startswith("- ") and cur is not None:
            raw = line[2:].strip()
            level, _ = extract_responsibility_level(raw)
            cur["bullets"].append(raw)
            cur["responsibility_levels"].append(level or "")
    return entries


def parse_bullet_list(md_text):
    """解析 '- key: value' 或 '- 文本' 列表。"""
    items = []
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def extract_jd_keywords(jd_text):
    """从 JD 文本提取关键词：词表命中 + 英文/数字术语。去重保序。"""
    found = []
    for w in TECH_VOCAB + ABILITY_VOCAB:
        if w.lower() in jd_text.lower() and w not in found:
            found.append(w)
    # 补充：连续英文/数字术语（词表未覆盖的）
    for m in re.findall(r"[A-Za-z][A-Za-z0-9+#.\-/]{1,20}", jd_text):
        if m not in found and m.lower() not in ("the", "and", "for", "with", "you"):
            found.append(m)
    return found


def split_jd_requirements(jd_text):
    """拆分 JD 为 required / preferred 两类条目。
    含「优先/加分/熟悉...更佳/preferred/plus」的行归入 preferred，其余要求行归入 required。"""
    required, preferred = [], []
    pref_pat = re.compile(r"优先|加分|更佳|preferred|plus|nice to have", re.I)
    for raw in re.split(r"[\n；;]", jd_text):
        line = raw.strip().lstrip("-•*0123456789.、）)").strip()
        if len(line) < 4:
            continue
        if pref_pat.search(line):
            preferred.append(line)
        elif re.search(r"要求|负责|任职|熟悉|精通|具备|经验|能力|学历|优先|职责", line):
            required.append(line)
    return required, preferred


def years_of_experience(period):
    """从 '2020.01-2023.05' / '2020.01-至今' 计算年限（粗略，保留 1 位小数）。"""
    p = period.strip()
    m = re.match(r"(\d{4})[./年-]?(\d{1,2})?", p)
    if not m:
        return 0.0
    y1, mo1 = int(m.group(1)), int(m.group(2) or 1)
    if re.search(r"至今|现在|present|now", p, re.I):
        y2, mo2 = date.today().year, date.today().month
    else:
        m2 = re.search(r"(\d{4})[./年-]?(\d{1,2})?", p[m.end():])
        if not m2:
            return 0.0
        y2, mo2 = int(m2.group(1)), int(m2.group(2) or 12)
    return round(max(0.0, (y2 - y1) + (mo2 - mo1) / 12.0), 1)


def dump_yaml(data, path):
    """写出 facts.yaml。内容为 JSON 格式（JSON 是 YAML 1.2 子集，
    下游可用 json.load 读取，也可用任意 YAML 解析器读取）。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_facts(root):
    p = os.path.join(root, DIR_AUTO, "facts.yaml")
    if not os.path.exists(p):
        raise SystemExit("[错误] facts.yaml 不存在，请先完成知识库录入（facts_parser 生成）。")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def out_path(root, subdir, filename):
    d = os.path.join(root, DIR_OUTPUT, subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, filename)


def today_str():
    return date.today().strftime("%Y%m%d")


def stamp():
    """产物文件名时间戳（YYYYMMDD-HHMM），避免同日重复生成互相覆盖。"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d-%H%M")
