#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence_store.py — STAR 行为证据碎片写入与索引维护。"""
import os
import re
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


class EvidenceStore:
    """管理 kb_path/原始事实/behavioral_evidence/ 目录。"""

    DIR_NAME = "behavioral_evidence"

    def __init__(self, root):
        self.root = root
        self.dir_path = os.path.join(root, common.DIR_RAW, self.DIR_NAME)
        os.makedirs(self.dir_path, exist_ok=True)

    def _next_seq(self, domain):
        """按域名找下一个序号，如 be_work_experience_001。"""
        pattern = re.compile(r"^be_%s_(\d{3})\.md$" % re.escape(domain))
        max_n = 0
        for name in os.listdir(self.dir_path):
            m = pattern.match(name)
            if m:
                max_n = max(max_n, int(m.group(1)))
        return max_n + 1

    def save(self, domain, description, source, star, confidence="confirmed", verbatim=""):
        """
        star: dict with keys: Background, Task, Action, Result, Key Insight, Boundary
        """
        seq = self._next_seq(domain)
        name = "be_%s_%03d" % (domain, seq)
        path = os.path.join(self.dir_path, "%s.md" % name)

        lines = [
            "---",
            "name: %s" % name,
            "description: %s" % description,
            "type: evidence",
            "domain: %s" % domain,
            "source: %s" % source,
            "confidence: %s" % confidence,
            "created: %s" % datetime.now().strftime("%Y-%m-%d"),
            "---",
            "",
            "## 背景（Background）",
            star.get("Background", ""),
            "",
            "## 任务（Task）",
            star.get("Task", ""),
            "",
            "## 行动（Action）",
        ]
        for a in star.get("Action", []):
            lines.append("- %s" % a)
        lines.extend([
            "",
            "## 结果（Result）",
            star.get("Result", ""),
            "",
            "## 关键判断（Key Insight）",
            star.get("Key Insight", ""),
            "",
            "## 边界条件（Boundary）",
            star.get("Boundary", ""),
            "",
            "## 原话（Verbatim）",
            "> %s" % verbatim if verbatim else "> （无）",
            "",
        ])

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self._update_map(name, domain, description, confidence)
        return name

    def _update_map(self, name, domain, description, confidence):
        map_path = os.path.join(self.dir_path, "map.md")
        content = ""
        if os.path.exists(map_path):
            with open(map_path, encoding="utf-8") as f:
                content = f.read()

        header = "# 行为证据地图\n\n> 自动维护，禁止手动编辑。\n"
        if not content.startswith("# 行为证据地图"):
            content = header

        section_marker = "## %s" % domain
        entry_line = "- [%s](%s.md) — %s [%s]" % (description, name, description, confidence)

        if section_marker not in content:
            content += "\n%s\n%s\n" % (section_marker, entry_line)
        else:
            # 在对应 section 末尾追加
            parts = content.split(section_marker)
            section_body = parts[1]
            next_section_idx = section_body.find("\n## ")
            if next_section_idx == -1:
                content = content + entry_line + "\n"
            else:
                insert_pos = len(parts[0]) + len(section_marker) + next_section_idx
                content = content[:insert_pos] + entry_line + "\n" + content[insert_pos:]

        with open(map_path, "w", encoding="utf-8") as f:
            f.write(content)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    store = EvidenceStore(root)
    name = store.save(
        domain="work_experience",
        description="测试商户分层",
        source="美团-测试",
        star={
            "Background": "增长停滞",
            "Task": "提升月活商户",
            "Action": ["重新分层", "配客户经理"],
            "Result": "80万→110万",
            "Key Insight": "活跃度比GMV重要",
            "Boundary": "头部必须人工",
        },
        confidence="confirmed",
        verbatim="测试原话",
    )
    print("[完成] 写入 %s" % name)


if __name__ == "__main__":
    main()
