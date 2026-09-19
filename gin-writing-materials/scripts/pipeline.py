#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""串联主题定义读取、素材校验和成品文档生成。"""

import argparse

import build_doc
import session
import topic_def
import validate


def run(material_root, topic, judgment="（待补充）", reader_question="（待补充）", force=False):
    definition = topic_def.read(material_root, topic)
    result = validate.validate_session(material_root, topic)
    closed_small_idea = result["knowledge_closed"] and result["confirmed_count"] >= 1 and not result["errors"]
    if not result["ok"] and not closed_small_idea and not force:
        reasons = result["errors"] or [
            f"confirmed 素材至少 {validate.MIN_CONFIRMED} 个，章节至少覆盖 {validate.MIN_SECTIONS} 个"
        ]
        raise ValueError("素材完整性校验失败：" + "；".join(reasons))
    path = build_doc.build(
        material_root=material_root,
        topic=topic,
        key_question=definition["key_question"],
        scope=definition["scope"],
        success_criteria=definition["success_criteria"],
        constraints=definition["constraints"],
        hypotheses=definition["hypotheses"],
        judgment=judgment,
        reader_question=reader_question,
        force=force,
    )
    session.set_stage(material_root, topic, "completed")
    session.mark_completed(material_root, topic)
    return path


def main():
    parser = argparse.ArgumentParser(description="运行写作素材生成管线")
    parser.add_argument("--material-root", required=True, help="素材库根目录")
    parser.add_argument("--topic", required=True, help="主题名")
    parser.add_argument("--judgment", default="（待补充）", help="作者当前判断")
    parser.add_argument("--reader-question", default="（待补充）", help="读者追问")
    parser.add_argument("--force", action="store_true", help="忽略完整性和碎片校验失败")
    args = parser.parse_args()
    path = run(args.material_root, args.topic, args.judgment, args.reader_question, args.force)
    print(f"素材文档已生成：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
