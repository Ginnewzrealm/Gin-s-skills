#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/migrate_glute_leg.py — 把旧结构的臀髋部/腿部合并为臀腿部。

用法：
    python3 scripts/migrate_glute_leg.py <知识库根路径> [--dry-run]

行为：
1. 检查 <知识库根路径>/01-训练动作库/ 下是否存在 臀髋部/ 和/或 腿部/ 文件夹
2. 创建 臀腿部/ 文件夹
3. 把旧文件夹中的 .md 动作文档移动到 臀腿部/
4. 合并 动作索引.md 中 ## 臀髋部 与 ## 腿部 为 ## 臀腿部，器械二级标题归并
5. 输出迁移报告；默认不删除旧文件夹（用户确认后可手动删除）

安全：运行前必须备份知识库；首次运行会要求用户输入 "确认迁移" 四字。
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

SOURCE_PARTS = ["臀髋部", "腿部"]
TARGET_PART = "臀腿部"
LIBRARY_DIR = "01-训练动作库"
INDEX_FILE = "动作索引.md"


def confirm_migration(yes=False):
    """要求用户显式确认。"""
    if yes:
        return
    prompt = "⚠️  迁移会移动动作文档并改写动作索引.md。请先备份知识库。\n输入「确认迁移」继续："
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消迁移。", file=sys.stderr)
        sys.exit(2)
    if answer != "确认迁移":
        print("确认失败，已取消迁移。", file=sys.stderr)
        sys.exit(2)


def merge_folders(kb_root, dry_run=False):
    """合并臀髋部/腿部文件夹到臀腿部。"""
    lib_root = Path(kb_root) / LIBRARY_DIR
    target_dir = lib_root / TARGET_PART

    moved_files = []
    conflicts = []

    for source_name in SOURCE_PARTS:
        source_dir = lib_root / source_name
        if not source_dir.exists():
            print(f"未发现旧文件夹：{source_dir}")
            continue

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for md_file in sorted(source_dir.rglob("*.md")):
            dest = target_dir / md_file.name
            if dest.exists():
                conflicts.append((str(md_file.relative_to(lib_root)), str(dest.relative_to(lib_root))))
                continue
            if not dry_run:
                shutil.move(str(md_file), str(dest))
            moved_files.append(str(md_file.relative_to(lib_root)))

    return moved_files, conflicts


def parse_index_sections(index_text):
    """把索引文本拆成 (前置内容, {部位: 部位文本}) 字典。"""
    # 匹配 ## 部位 到下一个 ## 或文件末尾
    pattern = re.compile(r"^(##\s+)(.+?)\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)

    sections = {}
    preamble = index_text
    for match in pattern.finditer(index_text):
        heading_prefix = match.group(1)
        heading = match.group(2).strip()
        body = match.group(3)
        sections[heading] = heading_prefix + heading + "\n" + body
        # 简单移除已匹配部分，剩余为前置内容
        preamble = preamble.replace(match.group(0), "", 1)

    return preamble, sections


def merge_equipment_sections(body1, body2):
    """合并两个部位正文内部的器械二级标题，保留原有顺序，去重。"""
    # 用 ### 器械 切分
    sub_pattern = re.compile(r"^(###\s+)(.+?)\n(.*?)(?=^###\s|\Z)", re.MULTILINE | re.DOTALL)

    order = []
    sub_sections = {}

    for body in (body1, body2):
        for match in sub_pattern.finditer(body):
            heading = match.group(2).strip()
            content = match.group(3)
            if heading not in sub_sections:
                order.append(heading)
                sub_sections[heading] = content
            else:
                # 合并内容：保留非占位内容，拼接真实动作行
                existing = sub_sections[heading]
                merged_content = existing.rstrip() + "\n" + content
                # 移除连续多个「（暂无）」占位，只保留一个
                merged_content = re.sub(r"(?:^|\n)\s*（暂无）\s*(?=\n)", "\n", merged_content)
                sub_sections[heading] = merged_content

    merged = ""
    for heading in order:
        content = sub_sections[heading].strip()
        # 如果该二级标题下没有真实动作行，补回「（暂无）」
        if not content or all(line.strip() == "（暂无）" for line in content.splitlines() if line.strip()):
            content = "（暂无）"
        merged += f"### {heading}\n{content}\n"

    return merged


def merge_index(kb_root, dry_run=False):
    """合并动作索引.md 中的臀髋部与腿部为臀腿部。"""
    index_path = Path(kb_root) / LIBRARY_DIR / INDEX_FILE
    if not index_path.exists():
        print(f"警告：未找到索引文件 {index_path}", file=sys.stderr)
        return False

    index_text = index_path.read_text(encoding="utf-8")
    preamble, sections = parse_index_sections(index_text)

    # 如果已经只有臀腿部，无需处理
    if TARGET_PART in sections and not any(s in sections for s in SOURCE_PARTS):
        print("索引已经是新结构（只有臀腿部），跳过索引合并。")
        return True

    # 收集源部位正文
    source_bodies = []
    for source_name in SOURCE_PARTS:
        if source_name in sections:
            source_bodies.append(sections[source_name])
            del sections[source_name]

    if source_bodies:
        merged_body = merge_equipment_sections(*source_bodies)
        # 更新索引行中的相对路径：./臀髋部/xxx.md / ./腿部/xxx.md → ./臀腿部/xxx.md
        for old_part in SOURCE_PARTS:
            merged_body = merged_body.replace(f"./{old_part}/", f"./{TARGET_PART}/")
        # 构造新的臀腿部一级标题
        sections[TARGET_PART] = f"## {TARGET_PART}\n{merged_body}"

    # 重新组装：前置 + 按原有一级标题顺序（胸部、背部、肩臂部、臀腿部、核心/腹部...）
    # 由于 Python 3.7+ dict 保持插入顺序，但 sections 此时顺序可能被打乱。
    # 这里采用简单策略：把臀腿部放在肩臂部之后、核心/腹部之前；其余保持原序。
    desired_order = ["胸部", "背部", "肩臂部", TARGET_PART, "核心/腹部", "全身/功能性", "有氧", "拉伸/筋膜", "热身"]

    new_text = preamble
    for heading in desired_order:
        if heading in sections:
            new_text += sections[heading]

    # 如果有计划之外的一级标题，追加在后面
    for heading, body in sections.items():
        if heading not in desired_order:
            new_text += body

    if not dry_run:
        backup_path = index_path.with_suffix(".md.bak")
        shutil.copy2(str(index_path), str(backup_path))
        index_path.write_text(new_text, encoding="utf-8")
        print(f"已备份原索引到：{backup_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description="合并臀髋部与腿部为臀腿部")
    parser.add_argument("kb_root", help="知识库根路径")
    parser.add_argument("--dry-run", action="store_true", help="只输出迁移报告，不实际移动文件")
    parser.add_argument("--yes", action="store_true", help="跳过交互确认（仅用于脚本/测试）")
    args = parser.parse_args()

    kb_root = Path(args.kb_root)
    lib_root = kb_root / LIBRARY_DIR
    if not lib_root.exists():
        print(f"错误：未找到动作库目录 {lib_root}", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        confirm_migration(yes=args.yes)

    moved, conflicts = merge_folders(kb_root, dry_run=args.dry_run)
    index_ok = merge_index(kb_root, dry_run=args.dry_run)

    print("\n=== 迁移报告 ===")
    print(f"模式：{'只读演练' if args.dry_run else '实际执行'}")
    print(f"动作文档移动：{len(moved)} 个")
    for f in moved:
        print(f"  → {f}")
    print(f"同名冲突（未移动）：{len(conflicts)} 个")
    for src, dst in conflicts:
        print(f"  ⚠️  {src} 与 {dst} 同名，请手动处理")
    print(f"索引合并：{'完成' if index_ok else '未执行/失败'}")

    if conflicts:
        print("\n存在同名冲突，请解决后重新运行或手动处理。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
