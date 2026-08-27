#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tacit 碎片 CRUD 与校验。"""

import os
import re

import common


REQUIRED_FIELDS = ["用户原始表达", "AI 追问", "原话", "场景", "解读", "关联锚点", "来源"]


def _next_seq(material_root, topic, date_str=None):
    date_str = date_str or common.today_str()
    d = common.fragment_dir(material_root, topic)
    os.makedirs(d, exist_ok=True)
    existing = [f for f in os.listdir(d) if f.endswith(".md")]
    nums = []
    for f in existing:
        m = re.match(rf"^{re.escape(date_str)}-(\d{{3}})\.md$", f)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def create(
    material_root,
    topic,
    domain,
    method,
    direction,
    confidence,
    quote,
    scene,
    interpretation,
    anchor,
    source,
    question="",
    raw_expression="",
):
    date_str = common.today_str()
    seq = _next_seq(material_root, topic, date_str)
    filename = f"{date_str}-{seq:03d}.md"
    d = common.fragment_dir(material_root, topic)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, filename)
    interp_lines = "\n".join(f"  - {x}" for x in interpretation)
    content = f"""---
topic: {topic}
domain: {domain}
method: {method}
direction: {direction}
confidence: {confidence}
created: {common.today_str()}
anchor: {anchor}
---

## 用户原始表达
{raw_expression}

## AI 追问
{question}

## 原话
{quote}

## 场景
{scene}

## 解读
{interp_lines}

## 关联锚点
{anchor}

## 来源
{source}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def list_fragments(material_root, topic):
    d = common.fragment_dir(material_root, topic)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".md"))


def validate(path):
    """检查碎片是否包含 5 个必填字段。"""
    errors = []
    if not os.path.exists(path):
        return [f"文件不存在：{path}"]
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for field in REQUIRED_FIELDS:
        if f"## {field}" not in content:
            errors.append(f"缺少字段：{field}")
    return errors


def read(path):
    """读取碎片文件，返回 frontmatter 字典 + body 文本。"""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, parts[2].strip()
