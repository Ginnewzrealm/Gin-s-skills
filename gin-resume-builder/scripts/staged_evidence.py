#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""staged_evidence.py — 待确认证据暂存区管理。

Agent 先把整理好的 STAR 写入 `原始事实/待确认/`，等用户确认后再迁移到
`behavioral_evidence/`。这样用户可以随时打开预览文件检查实际文字。
"""
import json
import os
import re
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from mining.evidence_store import EvidenceStore


class StagedEvidenceStore:
    """管理 `原始事实/待确认/` 目录。"""

    DIR_NAME = common.DIR_STAGED

    def __init__(self, root):
        self.root = root
        self.dir_path = os.path.join(root, common.DIR_RAW, self.DIR_NAME)
        os.makedirs(self.dir_path, exist_ok=True)

    def _next_seq(self, domain):
        pattern = re.compile(r"^st_%s_(\d{3})\.md$" % re.escape(domain))
        max_n = 0
        for name in os.listdir(self.dir_path):
            m = pattern.match(name)
            if m:
                max_n = max(max_n, int(m.group(1)))
        return max_n + 1

    def stage(self, domain, source, description, background, task, actions,
              result, insight, boundary, confidence="preview", verbatim=""):
        """写入预览 Markdown + JSON 侧载，返回 staged_id。"""
        seq = self._next_seq(domain)
        sid = "st_%s_%03d" % (domain, seq)
        md_path = os.path.join(self.dir_path, "%s.md" % sid)
        json_path = os.path.join(self.dir_path, "%s.json" % sid)

        star = {
            "Background": background,
            "Task": task,
            "Action": list(actions),
            "Result": result,
            "Key Insight": insight,
            "Boundary": boundary,
        }

        md_lines = [
            "---",
            "staged_id: %s" % sid,
            "description: %s" % description,
            "type: staged",
            "domain: %s" % domain,
            "source: %s" % source,
            "confidence: %s" % confidence,
            "created: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
            "---",
            "",
            "## 背景（Background）",
            background,
            "",
            "## 任务（Task）",
            task,
            "",
            "## 行动（Action）",
        ]
        for a in star["Action"]:
            md_lines.append("- %s" % a)
        md_lines.extend([
            "",
            "## 结果（Result）",
            result,
            "",
            "## 关键判断（Key Insight）",
            insight,
            "",
            "## 边界条件（Boundary）",
            boundary,
            "",
            "## 原话（Verbatim）",
            "> %s" % verbatim if verbatim else "> （无）",
            "",
            "> 状态：待确认。回复 OK 后 Agent 将把它写入 `原始事实/behavioral_evidence/`。",
        ])

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        payload = {
            "staged_id": sid,
            "domain": domain,
            "description": description,
            "source": source,
            "confidence": confidence,
            "verbatim": verbatim,
            "star": star,
            "created": datetime.now().isoformat(),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return sid

    def list_staged(self):
        """返回所有待确认条目列表（元组：staged_id, description, created）。"""
        items = []
        for name in sorted(os.listdir(self.dir_path)):
            if not name.endswith(".json"):
                continue
            json_path = os.path.join(self.dir_path, name)
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            items.append((data["staged_id"], data["description"], data.get("created", "")))
        return items

    def confirm(self, staged_id):
        """把指定预览迁移到 behavioral_evidence/，并删除预览文件。"""
        json_path = os.path.join(self.dir_path, "%s.json" % staged_id)
        md_path = os.path.join(self.dir_path, "%s.md" % staged_id)
        if not os.path.exists(json_path):
            raise FileNotFoundError("待确认证据不存在：%s" % staged_id)

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        store = EvidenceStore(self.root)
        name = store.save(
            domain=data["domain"],
            description=data["description"],
            source=data["source"],
            star=data["star"],
            confidence="confirmed",
            verbatim=data.get("verbatim", ""),
        )

        os.remove(json_path)
        os.remove(md_path)
        return name

    def reject(self, staged_id):
        """用户拒绝，删除预览文件。"""
        for ext in (".md", ".json"):
            path = os.path.join(self.dir_path, "%s%s" % (staged_id, ext))
            if os.path.exists(path):
                os.remove(path)
