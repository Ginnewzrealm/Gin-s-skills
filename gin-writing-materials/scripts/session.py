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
        "seed": topic,
        "stage": "project_located",
        "rounds": 0,
        "methods_used": [],
        "domain": None,
        "fragments": [],
        "key_variables": [],
        "sections_covered": [],
        "status": "active",
        "main_qud": "",
        "current_qud": "",
        "return_to": "",
        "p_x_r": {"P": "", "X": "", "R": ""},
        "last_question": {},
        "branches": [],
        "closure": {
            "knowledge": "open",
            "public_material": "unknown",
            "confirmed": False,
            "unresolved": [],
        },
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
    if direction and direction not in s["sections_covered"]:
        s["sections_covered"].append(direction)
    save(material_root, topic, s)


def set_domain(material_root, topic, domain):
    s = load_or_create(material_root, topic)
    s["domain"] = domain
    save(material_root, topic, s)


def set_seed(material_root, topic, seed):
    s = load_or_create(material_root, topic)
    s["seed"] = seed
    save(material_root, topic, s)


def set_qud(material_root, topic, main_qud=None, current_qud=None, return_to=None, p_x_r=None):
    s = load_or_create(material_root, topic)
    if main_qud is not None:
        s["main_qud"] = main_qud
    if current_qud is not None:
        s["current_qud"] = current_qud
    if return_to is not None:
        s["return_to"] = return_to
    if p_x_r is not None:
        s["p_x_r"] = {**s.get("p_x_r", {}), **p_x_r}
    save(material_root, topic, s)


def set_question_plan(material_root, topic, object, gap, action, dimension, purpose):
    s = load_or_create(material_root, topic)
    s["last_question"] = {
        "object": object,
        "gap": gap,
        "action": action,
        "dimension": dimension,
        "purpose": purpose,
    }
    save(material_root, topic, s)


def add_branch(material_root, topic, branch_id, summary, reason="", status="queued"):
    s = load_or_create(material_root, topic)
    branches = [b for b in s.get("branches", []) if b.get("id") != branch_id]
    branches.append({"id": branch_id, "summary": summary, "reason": reason, "status": status})
    s["branches"] = branches
    save(material_root, topic, s)


def set_closure(material_root, topic, knowledge=None, public_material=None, confirmed=None, unresolved=None):
    s = load_or_create(material_root, topic)
    closure = s.get("closure", {})
    if knowledge is not None:
        closure["knowledge"] = knowledge
    if public_material is not None:
        closure["public_material"] = public_material
    if confirmed is not None:
        closure["confirmed"] = confirmed
    if unresolved is not None:
        closure["unresolved"] = list(unresolved)
    s["closure"] = closure
    save(material_root, topic, s)


def set_stage(material_root, topic, stage):
    s = load_or_create(material_root, topic)
    s["stage"] = stage
    save(material_root, topic, s)


def mark_completed(material_root, topic):
    s = load_or_create(material_root, topic)
    s["status"] = "completed"
    save(material_root, topic, s)
