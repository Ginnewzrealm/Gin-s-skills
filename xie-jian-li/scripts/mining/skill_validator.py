#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_validator.py — 综合校验技能熟练度证据。

证据来源三处：
1. behavioral_evidence/*.md（STAR 行为证据碎片）
2. skill_details.md（技能深挖五维块）
3. skills.md 中已声明的熟练度（用于发现「自报过高」的情况）
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


class SkillValidator:
    """读取多处证据，判定某技能可声明的熟练度。"""

    def __init__(self, root):
        self.root = root
        self.evidence_dir = os.path.join(root, common.DIR_RAW, "behavioral_evidence")

    def _load_behavioral_evidence(self):
        """加载所有 be_*.md 中的 domain 和 description 字段。"""
        items = []
        if not os.path.isdir(self.evidence_dir):
            return items
        for name in os.listdir(self.evidence_dir):
            if not name.startswith("be_") or not name.endswith(".md"):
                continue
            path = os.path.join(self.evidence_dir, name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            m = re.search(r"domain:\s*(\w+)", text)
            domain = m.group(1) if m else "unknown"
            m = re.search(r"description:\s*(.+)", text)
            desc = m.group(1).strip() if m else ""
            items.append({"file": name, "domain": domain, "description": desc})
        return items

    def _load_skill_details(self):
        """加载 skill_details.md 中的技能名。"""
        items = []
        text = common.read_raw(self.root, "skill_details")
        for e in common.parse_entries(text):
            items.append({"name": e["title"], "file": "skill_details.md"})
        return items

    def _declared_level(self, skill_name):
        """从 skills.md 解析该技能的已声明熟练度。"""
        text = common.read_raw(self.root, "skills")
        pattern = re.compile(
            r"[-\*]\s*" + re.escape(skill_name) + r"\s*（\s*(熟练|掌握|了解|证据：强|证据：中)\s*）",
            re.I,
        )
        m = pattern.search(text)
        if not m:
            return None
        level = m.group(1)
        if level in ("强", "中"):
            level = "证据：%s" % level
        return level

    def evidence_for_skill(self, skill_name):
        """返回匹配 skill_name 的证据列表（去重）。"""
        name = skill_name.lower()
        results = []
        seen = set()
        for item in self._load_behavioral_evidence() + self._load_skill_details():
            key = "%s:%s" % (item.get("file"), item.get("description", item.get("name", "")))
            if key in seen:
                continue
            text = item.get("description", item.get("name", "")).lower()
            if name in text:
                results.append(item)
                seen.add(key)
        return results

    def proficiency_for_skill(self, skill_name):
        """根据证据数量返回建议熟练度。"""
        count = len(self.evidence_for_skill(skill_name))
        if count >= 3:
            return "熟练", count
        if count == 2:
            return "掌握", count
        if count == 1:
            return "了解", count
        return None, count

    def validate(self, skill_name):
        """完整校验：返回建议熟练度、证据数、已声明档位、是否自报过高。"""
        suggested, count = self.proficiency_for_skill(skill_name)
        declared = self._declared_level(skill_name)

        overclaim = False
        if declared and declared == "熟练" and (not suggested or count < 3):
            overclaim = True
        if declared and declared == "掌握" and (not suggested or count < 2):
            overclaim = True

        return {
            "skill": skill_name,
            "declared": declared,
            "suggested": suggested or "证据不足",
            "count": count,
            "overclaim": overclaim,
        }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    ap.add_argument("--skill", required=True)
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    v = SkillValidator(root)
    r = v.validate(args.skill)
    print("技能：%s" % r["skill"])
    print("已声明：%s" % (r["declared"] or "未声明"))
    print("证据数：%d" % r["count"])
    print("建议熟练度：%s" % r["suggested"])
    if r["overclaim"]:
        print("[警告] 已声明档位高于证据支撑，建议降级或继续挖掘")


if __name__ == "__main__":
    main()
