#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会话完整性与碎片校验。"""

import fragment
import session as session_mod


MIN_CONFIRMED = 5
MIN_SECTIONS = 2
SECTIONS = ["钩子", "核心论证", "案例支撑", "结尾升华"]


def validate_session(material_root, topic):
    """返回会话是否满足收尾条件。"""
    paths = fragment.list_fragments(material_root, topic)
    confirmed = 0
    fuzzy = 0
    sections = set()
    errors = []
    for p in paths:
        fm, _ = fragment.read(p)
        conf = fm.get("confidence", "")
        if conf == "confirmed":
            confirmed += 1
        elif conf == "fuzzy":
            fuzzy += 1
        direction = fm.get("direction", "")
        if direction in SECTIONS:
            sections.add(direction)
        field_errors = fragment.validate(p)
        if field_errors:
            errors.extend(field_errors)

    ok = not errors and confirmed >= MIN_CONFIRMED and len(sections) >= MIN_SECTIONS
    state = session_mod.load_or_create(material_root, topic)
    closure = state.get("closure", {})
    return {
        "ok": ok,
        "confirmed_count": confirmed,
        "fuzzy_count": fuzzy,
        "sections_covered": sorted(sections),
        "errors": errors,
        "knowledge_closed": closure.get("knowledge") == "closed" and bool(closure.get("confirmed")),
        "public_material_status": closure.get("public_material", "unknown"),
    }


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="校验写作素材会话")
    parser.add_argument("--material-root", required=True, help="素材库根目录")
    parser.add_argument("--topic", required=True, help="主题名")
    args = parser.parse_args()
    result = validate_session(args.material_root, args.topic)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


def completeness_score(material_root, topic):
    """返回红绿灯评分。"""
    paths = fragment.list_fragments(material_root, topic)
    confirmed = sum(
        1 for p in paths if fragment.read(p)[0].get("confidence") == "confirmed"
    )
    sections = set()
    for p in paths:
        d = fragment.read(p)[0].get("direction", "")
        if d in SECTIONS:
            sections.add(d)

    s = session_mod.load_or_create(material_root, topic)
    clarity = min(5, max(1, len(s.get("key_variables", [])) + 2))

    def light(current, threshold):
        if current >= threshold:
            return "🟢"
        elif current >= (threshold + 1) // 2:
            return "🟡"
        return "🔴"

    return {
        "素材": {"current": confirmed, "threshold": MIN_CONFIRMED, "light": light(confirmed, MIN_CONFIRMED)},
        "章节": {"current": len(sections), "threshold": MIN_SECTIONS, "light": light(len(sections), MIN_SECTIONS)},
        "主题清晰度": {"current": clarity, "threshold": 5, "light": light(clarity, 5)},
    }
