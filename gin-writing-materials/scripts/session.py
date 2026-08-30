#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会话状态管理。"""

import json
import os

import common


def load_or_create(material_root, topic):
    path = common.session_path(material_root, topic)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    default = {
        "topic": topic,
        "stage": "project_located",
        "rounds": 0,
        "methods_used": [],
        "domain": None,
        "fragments": [],
        "key_variables": [],
        "sections_covered": [],
        "status": "active",
    }
    save(material_root, topic, default)
    return default


def save(material_root, topic, data):
    path = common.session_path(material_root, topic)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def increment_round(material_root, topic):
    s = load_or_create(material_root, topic)
    s["rounds"] += 1
    save(material_root, topic, s)


def record_method(material_root, topic, method):
    s = load_or_create(material_root, topic)
    if method not in s["methods_used"]:
        s["methods_used"].append(method)
    save(material_root, topic, s)


def record_fragment(material_root, topic, fragment_id, direction, confidence):
    s = load_or_create(material_root, topic)
    if fragment_id not in s["fragments"]:
        s["fragments"].append(fragment_id)
    if direction not in s["sections_covered"]:
        s["sections_covered"].append(direction)
    save(material_root, topic, s)


def set_domain(material_root, topic, domain):
    s = load_or_create(material_root, topic)
    s["domain"] = domain
    save(material_root, topic, s)


def set_stage(material_root, topic, stage):
    s = load_or_create(material_root, topic)
    s["stage"] = stage
    save(material_root, topic, s)


def mark_completed(material_root, topic):
    s = load_or_create(material_root, topic)
    s["status"] = "completed"
    save(material_root, topic, s)
