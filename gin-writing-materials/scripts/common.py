#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gin-writing-materials 公共工具层：配置读取、路径解析、文本处理。"""

import os
import re
import unicodedata
from datetime import date

try:
    from pypinyin import lazy_pinyin
except Exception:  # pragma: no cover
    lazy_pinyin = None


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(SKILL_DIR, "config.yaml")

DEFAULT_ANCHOR_DIR = "成品"
XIE_ZUO_SU_CAI_DIR = ".gin-writing-materials"

TOPIC_DEF_FILE = "00-主题定义.md"
CONVERSATION_LOG_FILE = "00-需求澄清.md"
SESSION_FILE = "01-会话状态.json"
FRAGMENTS_DIR = "02-素材碎片"
MATERIAL_DOC_FILE = "03-素材文档.md"


def load_config(path=DEFAULT_CONFIG_PATH):
    """读取简单 YAML key: value 配置。"""
    cfg = {
        "material_root": "",
        "anchor_dir": DEFAULT_ANCHOR_DIR,
    }
    if not os.path.exists(path):
        return cfg
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def user_config_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".config", "gin-writing-materials", "config.yaml")


def tools_config_path(tools_dir=None):
    """返回备份配置路径。

    如果调用方（Agent）传入 tools_dir，则使用传入路径；
    否则返回 None，由调用方根据当前 Agent 平台自行决定。
    """
    if not tools_dir:
        return None
    return os.path.join(os.path.expanduser(tools_dir), "gin-writing-materials", "config.yaml")


def load_config_with_fallback(primary=None, tools_dir=None):
    """优先读主配置，缺失则读 tools 目录下的备份配置。"""
    primary = primary or user_config_path()
    if os.path.exists(primary):
        return load_config(primary)
    backup = tools_config_path(tools_dir)
    if backup and os.path.exists(backup):
        return load_config(backup)
    return load_config()


def resolve_material_root(cli_root=None, cfg_path=None, tools_dir=None):
    """解析素材库根路径：CLI 参数 > 用户主配置 > tools 备份配置 > 报错。"""
    if cli_root:
        return os.path.abspath(os.path.expanduser(cli_root))
    cfg = load_config_with_fallback(cfg_path or user_config_path(), tools_dir)
    root = cfg.get("material_root", "")
    if root:
        return os.path.abspath(os.path.expanduser(root))
    raise SystemExit("[错误] 未配置 material_root。请先运行 init。")


def ensure_dirs(material_root):
    """确保素材库隐藏目录存在（旧版兼容，不再主动使用）。"""
    base = os.path.join(material_root, XIE_ZUO_SU_CAI_DIR)
    for sub in ("fragments", "sessions", "topic-definitions"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    return base


def slugify(text):
    """把中文/混合文本转成 URL-safe kebab-case（优先转拼音）。"""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    if lazy_pinyin:
        # 先尝试整句转拼音，再拼接
        pinyin_parts = lazy_pinyin(text)
        text = " ".join(pinyin_parts)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text.lower().strip("-")


def today_str():
    return date.today().strftime("%Y%m%d")


def sanitize_topic_name(topic):
    """清洗中文主题名，替换文件系统非法字符。"""
    topic = unicodedata.normalize("NFKC", topic)
    topic = topic.strip()
    illegal = r'\\/|:*?"<> '
    for ch in illegal:
        topic = topic.replace(ch, "-")
    topic = re.sub(r"-+", "-", topic)
    return topic.strip("-")


def topic_to_folder_name(topic, date_str=None):
    """生成主题项目文件夹名：{日期}-{中文主题名}。"""
    date_str = date_str or today_str()
    return f"{date_str}-{sanitize_topic_name(topic)}"


def find_project_dir(material_root, topic):
    """根据主题名查找已存在的项目文件夹。返回唯一匹配或 None。"""
    if not os.path.isdir(material_root):
        return None
    target_clean = sanitize_topic_name(topic)
    target_slug = slugify(topic)
    matches = []
    for name in os.listdir(material_root):
        full = os.path.join(material_root, name)
        if not os.path.isdir(full):
            continue
        m = re.match(r"^\d{8}-(.+)$", name)
        if not m:
            continue
        existing_topic = m.group(1)
        if existing_topic == target_clean:
            return full
        if slugify(existing_topic) == target_slug:
            matches.append(full)
    if len(matches) == 1:
        return matches[0]
    return None


def project_dir(material_root, topic, date_str=None, create=True):
    """返回主题项目文件夹路径。优先复用已有文件夹，否则创建新文件夹。"""
    existing = find_project_dir(material_root, topic)
    if existing:
        return existing
    name = topic_to_folder_name(topic, date_str)
    path = os.path.join(material_root, name)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def topic_definition_path(material_root, topic):
    return os.path.join(project_dir(material_root, topic), TOPIC_DEF_FILE)


def conversation_log_path(material_root, topic):
    return os.path.join(project_dir(material_root, topic), CONVERSATION_LOG_FILE)


def session_path(material_root, topic):
    return os.path.join(project_dir(material_root, topic), SESSION_FILE)


def fragment_dir(material_root, topic):
    d = os.path.join(project_dir(material_root, topic), FRAGMENTS_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def material_doc_path(material_root, topic):
    return os.path.join(project_dir(material_root, topic), MATERIAL_DOC_FILE)


def anchor_dir_path(material_root, cfg=None):
    anchor = (cfg or load_config()).get("anchor_dir", DEFAULT_ANCHOR_DIR)
    return os.path.join(material_root, anchor)
