#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xie-zuo-su-cai 技能静态审计脚本。"""

import ast
import os
import sys
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_imports(path):
    """解析 Python 文件中的顶层 import/from ... import。"""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
    return imports


def list_functions(path):
    """列出模块中定义的顶层函数。"""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    return [
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def main():
    scripts_dir = os.path.join(SKILL_DIR, "scripts")
    scripts = sorted(f for f in os.listdir(scripts_dir) if f.endswith(".py"))

    print("# xie-zuo-su-cai 技能静态审计报告\n")

    # 1. 文件清单与入口
    print("## 1. 脚本文件清单\n")
    for s in scripts:
        path = os.path.join(scripts_dir, s)
        size = os.path.getsize(path)
        with open(path, encoding="utf-8") as f:
            has_main = 'if __name__ == "__main__":' in f.read()
        entry = "✅ CLI 入口" if has_main else "➖ 库模块"
        print(f"- `{s}` ({size} bytes) — {entry}")
    print()

    # 2. import 依赖图
    print("## 2. 模块依赖图\n")
    deps = {}
    for s in scripts:
        path = os.path.join(scripts_dir, s)
        module_name = s[:-3]
        imports = parse_imports(path)
        # 只关心同目录模块
        local_deps = [m for m in imports if m in {x[:-3] for x in scripts}]
        deps[module_name] = local_deps

    for mod, local_deps in deps.items():
        if local_deps:
            print(f"- `{mod}` → {', '.join(f'`{d}`' for d in local_deps)}")
        else:
            print(f"- `{mod}` → （无本地依赖）")
    print()

    # 3. 循环依赖检测
    print("## 3. 循环依赖检测\n")
    cycles = []
    visited = set()

    def dfs(node, path):
        if node in path:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:])
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for dep in deps.get(node, []):
            dfs(dep, path[:])

    for mod in deps:
        dfs(mod, [])

    if cycles:
        for c in cycles:
            print(f"- 🔴 发现循环依赖：{' → '.join(f'`{m}`' for m in c)} → `{c[0]}`")
    else:
        print("- ✅ 未发现循环依赖")
    print()

    # 4. 函数级未使用检测（粗略：其他脚本是否引用）
    print("## 4. 函数引用情况（粗略）\n")
    funcs = {s[:-3]: list_functions(os.path.join(scripts_dir, s)) for s in scripts}
    all_text = ""
    for s in scripts:
        with open(os.path.join(scripts_dir, s), encoding="utf-8") as f:
            all_text += f"\n{f.read()}"
    for mod, names in funcs.items():
        for name in names:
            used = all_text.count(f"{name}(") > 1 or all_text.count(f"{module_name}.{name}(") > 0
            marker = "✅" if used else "⚠️ 可能未使用"
            print(f"- `{mod}.{name}()` {marker}")
    print()

    # 5. references 与 SKILL.md 的引用关系
    print("## 5. References 与入口文件覆盖\n")
    refs_dir = os.path.join(SKILL_DIR, "references")
    refs = sorted(os.listdir(refs_dir)) if os.path.isdir(refs_dir) else []
    skill_md_path = os.path.join(SKILL_DIR, "SKILL.md")
    with open(skill_md_path, encoding="utf-8") as f:
        skill_content = f.read()
    for r in refs:
        ref_path = os.path.join(refs_dir, r)
        if os.path.isfile(ref_path):
            mentioned = r in skill_content
            marker = "✅ SKILL.md 已引用" if mentioned else "⚠️ SKILL.md 未引用"
            print(f"- `{r}` — {marker}")
    print()

    # 6. 输入输出依赖
    print("## 6. 核心数据流\n")
    print("""
用户输入（主题/回答）
  → init.py（初始化素材库根目录）
  → session.py（维护会话状态 JSON）
  → fragment.py（生成碎片 Markdown）
  → validate.py（统计 confirmed/章节覆盖）
  → build_doc.py（输出 `{日期}-{主题拼音}-素材.md`）
  → human-writing（读取素材文档路径）
""")


if __name__ == "__main__":
    main()
