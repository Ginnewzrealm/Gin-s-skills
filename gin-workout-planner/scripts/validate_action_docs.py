#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/validate_action_docs.py — 校验动作文档 frontmatter。"""

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "动作类型",
    "器械状态",
    "计重方式",
    "训练阶段",
    "目标部位",
    "最后练习",
    "累计训练次数",
    "估算1RM",
]

VALID_ENUMS = {
    "动作类型": {"主项", "复合动作", "孤立动作"},
    "器械状态": {"激活", "冷冻"},
    "计重方式": {"总重", "单侧×2", "单臂×1"},
    "训练阶段": {"学习期", "渐进期", "精细优化期"},
}

WORDLIST_SECTION_RE = re.compile(
    r"###\s+目标部位标签词表.*?\n(?P<table>(?:\|[^\n]*\|\n?)+)",
    re.DOTALL,
)
WORDLIST_ROW_RE = re.compile(
    r"\|\s*(?P<body_part>[^|]+?)\s*\|\s*(?P<tags>[^|]+?)\s*\|",
)


def load_wordlist(rules_md_text):
    """从 rules.md 文本解析目标部位词表。"""
    wordlist = {}
    section_match = WORDLIST_SECTION_RE.search(rules_md_text)
    if not section_match:
        return wordlist

    table_text = section_match.group("table")
    for match in WORDLIST_ROW_RE.finditer(table_text):
        body_part = match.group("body_part").strip()
        tags_text = match.group("tags").strip()
        # 跳过表头行和分隔行
        if not body_part or body_part == "部位" or set(body_part) <= {"-", "|"}:
            continue
        if set(tags_text) <= {"-", "|"}:
            continue
        tags = [t.strip() for t in tags_text.split("、") if t.strip()]
        if tags:
            wordlist[body_part] = set(tags)
    return wordlist


def _parse_inline_list(value):
    """解析行内列表 [a, b] 或 []。"""
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(","):
            item = item.strip().strip('"\'')
            if item:
                items.append(item)
        return items
    return None


def parse_simple_yaml(yaml_text):
    """解析简化版 YAML frontmatter（仅支持标量字符串和字符串列表）。"""
    result = {}
    current_key = None
    current_list = None

    for raw_line in yaml_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        # 列表项
        list_match = re.match(r"^\s*-\s+(?P<value>.+)$", line)
        if list_match and current_key is not None and current_list is not None:
            current_list.append(list_match.group("value").strip().strip('"\''))
            continue

        # 键值对
        kv_match = re.match(r"^(?P<key>[^#:]+?)\s*:\s*(?P<value>.*)$", line)
        if not kv_match:
            continue

        key = kv_match.group("key").strip()
        value = kv_match.group("value").strip()

        # 关闭上一个列表
        if current_key is not None and current_list is not None:
            result[current_key] = current_list
            current_key = None
            current_list = None

        inline_list = _parse_inline_list(value)
        if inline_list is not None:
            result[key] = inline_list
        elif value == "":
            # 多行列表的开始
            current_key = key
            current_list = []
        else:
            # 标量值，去除引号
            result[key] = value.strip('"\'')

    # 文件末尾如果还在列表中
    if current_key is not None and current_list is not None:
        result[current_key] = current_list

    return result


def parse_frontmatter(content):
    """解析 Markdown 文件的 YAML frontmatter。"""
    if not content.startswith("---"):
        return None, "文件缺少 YAML frontmatter"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, "YAML frontmatter 格式不完整"

    yaml_text = parts[1].strip()
    try:
        frontmatter = parse_simple_yaml(yaml_text)
    except Exception as e:
        return None, f"frontmatter 解析失败: {e}"

    if not isinstance(frontmatter, dict):
        return None, "frontmatter 不是有效的键值对象"

    return frontmatter, None


def extract_h1(content):
    """提取第一个 Markdown H1 标题（去掉 # 和括号内容）。"""
    for line in content.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            # 去掉括号内容，如 "（与文件名一字不差）"
            title = re.split(r"[（(]", title)[0].strip()
            return title
    return None


def validate_doc(content, filename, wordlist, strict=True):
    """校验单个动作文档，返回错误列表（空表示通过）。"""
    errors = []
    name_without_ext = Path(filename).stem

    frontmatter, err = parse_frontmatter(content)
    if err:
        return [err]

    # 必填字段
    for field in REQUIRED_FIELDS:
        if field not in frontmatter:
            if field == "目标部位" and not strict:
                # 旧文档豁免：缺失目标部位仅跳过，不报错
                continue
            errors.append(f"frontmatter 缺少必填字段: {field}")

    if errors:
        # 缺少必填字段时，后续枚举值检查可能不准确，先返回
        return errors

    # 枚举值校验
    for field, valid_values in VALID_ENUMS.items():
        value = frontmatter.get(field)
        if value is not None and value not in valid_values:
            errors.append(
                f"{field} 取值不合法: {value!r}，应为 {sorted(valid_values)} 之一"
            )

    # 目标部位校验
    target_areas = frontmatter.get("目标部位")
    if target_areas is not None:
        if not isinstance(target_areas, list):
            errors.append("目标部位 必须是 YAML 列表")
        else:
            if len(target_areas) == 0 and strict:
                # 空列表只在省略时允许；严格模式下如果写了 [] 也是合法的
                pass
            if len(target_areas) > 2:
                errors.append("目标部位 标签数量必须为 1~2 个")

            all_tags = set()
            for tags in wordlist.values():
                all_tags.update(tags)

            for tag in target_areas:
                if tag not in all_tags:
                    errors.append(f"目标部位 标签不在受控词表中: {tag}")

    # H1 标题与文件名一致
    h1 = extract_h1(content)
    if h1 is None:
        errors.append("缺少 H1 动作名标题")
    elif h1 != name_without_ext:
        errors.append(f"H1 标题与文件名不一致: H1={h1!r}, 文件名={name_without_ext!r}")

    return errors


def validate_library(library_path, rules_path, strict=False):
    """扫描整个动作库并返回错误汇总。"""
    rules_text = Path(rules_path).read_text(encoding="utf-8")
    wordlist = load_wordlist(rules_text)

    if not wordlist:
        print("警告: 未能从 rules.md 解析出目标部位词表", file=sys.stderr)

    library = Path(library_path)
    docs = list(library.rglob("*.md"))

    total_errors = 0
    for doc_path in docs:
        content = doc_path.read_text(encoding="utf-8")
        errors = validate_doc(content, doc_path.name, wordlist, strict=strict)
        if errors:
            total_errors += len(errors)
            print(f"\n❌ {doc_path.relative_to(library)}")
            for err in errors:
                print(f"   - {err}")

    print(f"\n扫描完成: {len(docs)} 个文档, {total_errors} 个错误")
    return total_errors


def validate_single_file(file_path, rules_path, strict=True):
    """校验单个动作文档。"""
    rules_text = Path(rules_path).read_text(encoding="utf-8")
    wordlist = load_wordlist(rules_text)

    if not wordlist:
        print("警告: 未能从 rules.md 解析出目标部位词表", file=sys.stderr)

    doc_path = Path(file_path)
    content = doc_path.read_text(encoding="utf-8")
    errors = validate_doc(content, doc_path.name, wordlist, strict=strict)

    if errors:
        print(f"\n❌ {doc_path}")
        for err in errors:
            print(f"   - {err}")
        print(f"\n校验完成: 1 个文档, {len(errors)} 个错误")
        return len(errors)

    print(f"\n✅ {doc_path}: 通过")
    return 0


def main():
    parser = argparse.ArgumentParser(description="校验动作文档 frontmatter")
    parser.add_argument(
        "--library",
        default=None,
        help="动作库根目录 (默认: 01-训练动作库，与 --file 二选一)",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="单个动作文档路径 (与 --library 二选一)",
    )
    parser.add_argument(
        "--rules",
        default="references/rules.md",
        help="rules.md 路径 (默认: references/rules.md)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式: 旧文档也必须有 frontmatter 目标部位",
    )
    args = parser.parse_args()

    if args.library and args.file:
        print("错误: --library 和 --file 不能同时使用", file=sys.stderr)
        sys.exit(2)

    if args.file:
        total_errors = validate_single_file(args.file, args.rules, strict=args.strict)
    else:
        library = args.library or "01-训练动作库"
        total_errors = validate_library(library, args.rules, strict=args.strict)

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
