#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成主题定义文件 00-主题定义.md。"""

import argparse
import os

import common


TEMPLATE_PATH = os.path.join(common.SKILL_DIR, "references", "topic-definition-template.md")


def _bullet_list(items):
    if items:
        return "\n".join(f"- {item}" for item in items)
    return "- （待补充）"


def save(
    material_root,
    topic,
    key_question="",
    scope=None,
    success_criteria=None,
    constraints=None,
    hypotheses=None,
):
    """根据主题定义模板生成 00-主题定义.md。

    scope 应为字典，可包含：读者、文体、篇幅目标、在范围内、不在范围内。
    """
    scope = scope or {}
    success_criteria = success_criteria or []
    constraints = constraints or []
    hypotheses = hypotheses or []

    path = common.topic_definition_path(material_root, topic)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    scope_text = "\n".join([
        f"- **读者**：{scope.get('读者', '（待补充）')}",
        f"- **文体**：{scope.get('文体', '（待补充）')}",
        f"- **篇幅目标**：{scope.get('篇幅目标', '（待补充）')}",
        f"- **在范围内**：{scope.get('在范围内', '（待补充）')}",
        f"- **不在范围内**：{scope.get('不在范围内', '（待补充）')}",
    ])

    content = template.format(
        主题=topic,
        key_question=key_question or "（待补充）",
        scope=scope_text,
        success_criteria=_bullet_list(success_criteria),
        constraints=_bullet_list(constraints),
        hypotheses=_bullet_list(hypotheses),
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    ap = argparse.ArgumentParser(description="生成主题定义文件")
    ap.add_argument("--material-root", required=True, help="素材库根目录")
    ap.add_argument("--topic", required=True, help="主题名")
    ap.add_argument("--key-question", default="", help="真实问题")
    ap.add_argument("--reader", default="", help="读者")
    ap.add_argument("--style", default="", help="文体")
    ap.add_argument("--length", default="", help="篇幅目标")
    ap.add_argument("--in-scope", default="", help="在范围内")
    ap.add_argument("--out-scope", default="", help="不在范围内")
    ap.add_argument("--success-criteria", nargs="*", default=[], help="成功标准")
    ap.add_argument("--constraints", nargs="*", default=[], help="约束")
    ap.add_argument("--hypotheses", nargs="*", default=[], help="初始假设")
    args = ap.parse_args()

    scope = {
        "读者": args.reader,
        "文体": args.style,
        "篇幅目标": args.length,
        "在范围内": args.in_scope,
        "不在范围内": args.out_scope,
    }

    path = save(
        material_root=args.material_root,
        topic=args.topic,
        key_question=args.key_question,
        scope=scope,
        success_criteria=args.success_criteria,
        constraints=args.constraints,
        hypotheses=args.hypotheses,
    )
    print(path)


if __name__ == "__main__":
    main()
