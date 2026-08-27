#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""保存一轮对话到项目文件夹。

每轮用户回答后必须调用本脚本：
1. 更新 01-会话状态.json（轮数 +1）
2. 把 AI 追问和用户原始表达追加到 00-需求澄清.md
3. 如果提供了 confidence，再生成一个素材碎片
"""

import argparse
import os

import common
import fragment
import session


def save_turn(
    material_root,
    topic,
    question,
    answer,
    method=None,
    direction=None,
    confidence=None,
    anchor=None,
    source=None,
    interpretation=None,
):
    """保存一轮对话。

    Args:
        material_root: 素材库根目录
        topic: 主题名
        question: AI 的问题
        answer: 用户的完整回答（原始表达）
        method: 挖掘方法（可选）
        direction: 该轮对应的文章方向（可选）
        confidence: confirmed/fuzzy（可选，提供则生成碎片）
        anchor: 关联锚点（可选）
        source: 来源说明（可选）
        interpretation: 解读列表（可选）

    Returns:
        (conversation_log_path, fragment_path_or_None)
    """
    interpretation = interpretation or []

    # 确保会话状态存在
    session.load_or_create(material_root, topic)
    session.increment_round(material_root, topic)
    if method:
        session.record_method(material_root, topic, method)

    s = session.load_or_create(material_root, topic)
    round_num = s["rounds"]

    # 追加对话记录到 00-需求澄清.md
    log_path = common.conversation_log_path(material_root, topic)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    entry = f"""## 第 {round_num} 轮

**AI**：{question}

**用户**：{answer}

"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    # 如果提供了 confidence，生成素材碎片
    frag_path = None
    if confidence:
        quote = answer.strip().split("\n")[0][:200]
        interp = interpretation if interpretation else ["（待补充）"]
        frag_path = fragment.create(
            material_root=material_root,
            topic=topic,
            domain="writing",
            method=method or "",
            direction=direction or "",
            confidence=confidence,
            quote=quote,
            scene="（待补充）",
            interpretation=interp,
            anchor=anchor or "",
            source=source or f"第{round_num}轮",
            question=question,
            raw_expression=answer,
        )
        rel = os.path.relpath(
            frag_path,
            common.project_dir(material_root, topic),
        )
        session.record_fragment(material_root, topic, rel, direction or "", 0.8)

    return log_path, frag_path


def main():
    ap = argparse.ArgumentParser(description="保存一轮对话")
    ap.add_argument("--material-root", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--question", required=True, help="AI 的问题")
    ap.add_argument("--answer", required=True, help="用户的完整回答")
    ap.add_argument("--method", default=None)
    ap.add_argument("--direction", default=None)
    ap.add_argument("--confidence", default=None, choices=["confirmed", "fuzzy"])
    ap.add_argument("--anchor", default=None)
    ap.add_argument("--source", default=None)
    ap.add_argument("--interpretation", nargs="*", default=[])
    args = ap.parse_args()

    log_path, frag_path = save_turn(
        material_root=args.material_root,
        topic=args.topic,
        question=args.question,
        answer=args.answer,
        method=args.method,
        direction=args.direction,
        confidence=args.confidence,
        anchor=args.anchor,
        source=args.source,
        interpretation=args.interpretation,
    )
    print(f"已保存对话记录：{log_path}")
    if frag_path:
        print(f"已保存素材碎片：{frag_path}")


if __name__ == "__main__":
    main()
