#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化用户配置与素材库目录，并检查运行依赖。"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def _print_block(title):
    print(f"\n{'=' * 40}")
    print(f" {title}")
    print(f"{'=' * 40}")


def check_python_version(min_major=3, min_minor=9):
    """检查 Python 版本。"""
    ok = sys.version_info >= (min_major, min_minor)
    if ok:
        print(f"[完成] Python 版本：{sys.version.split()[0]}（满足 >= {min_major}.{min_minor}）")
    else:
        print(f"⚠️ Python 版本过低：{sys.version.split()[0]}，需要 >= {min_major}.{min_minor}")
    return ok


def check_pypinyin():
    """检查 pypinyin 是否已安装。"""
    try:
        import pypinyin  # noqa: F401
        print("[完成] pypinyin 已安装")
        return True
    except ImportError:
        print("⚠️ 未安装 pypinyin。请运行：pip install pypinyin>=0.55.0")
        return False


def check_material_root(material_root):
    """检查素材库根目录是否可写。"""
    material_root = os.path.abspath(os.path.expanduser(material_root))
    if os.path.exists(material_root):
        if not os.path.isdir(material_root):
            print(f"⚠️ {material_root} 不是目录")
            return False
        if not os.access(material_root, os.W_OK):
            print(f"⚠️ 目录 {material_root} 不可写")
            return False
    else:
        # 尝试创建以验证父目录可写
        try:
            os.makedirs(material_root, exist_ok=True)
        except OSError as e:
            print(f"⚠️ 无法创建目录 {material_root}：{e}")
            return False
    print(f"[完成] 素材库路径可写：{material_root}")
    return True


def check_input_materials(paths):
    """检查用户提供的输入素材文件/目录是否存在。"""
    if not paths:
        return True
    ok = True
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.exists(p):
            print(f"[完成] 输入素材存在：{p}")
        else:
            print(f"⚠️ 输入素材不存在：{p}")
            ok = False
    return ok


def check_env(material_root=None, input_materials=None):
    """运行所有环境检查。返回 (ok, warnings)。"""
    _print_block("初始化检查")
    results = {
        "python": check_python_version(),
        "pypinyin": check_pypinyin(),
    }
    warnings = {}
    if material_root:
        results["material_root"] = check_material_root(material_root)
    if input_materials:
        results["input_materials"] = check_input_materials(input_materials)

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n⚠️ 检查未通过项：{', '.join(failed)}")
        return False, warnings
    if warnings:
        print(f"\n⚠️ 警告（非阻塞）：{'; '.join(warnings.values())}")
    print("\n[完成] 所有必要检查通过")
    return True, warnings


def run_init(material_root, cfg_path=None, input_materials=None, tools_backup_dir=None):
    material_root = os.path.abspath(os.path.expanduser(material_root))

    # 先检查环境与依赖
    ok, _ = check_env(material_root=material_root, input_materials=input_materials)
    if not ok:
        print("\n请修复上述问题后再试。")
        return None

    default_cfg = common.load_config(common.DEFAULT_CONFIG_PATH)
    default_cfg["material_root"] = material_root
    content_lines = [f"{k}: {v}\n" for k, v in default_cfg.items()]

    # 主配置路径
    cfg_path = cfg_path or common.user_config_path()
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.writelines(content_lines)

    # 备份配置路径：Agent 传入自己的 tools 目录
    backup_path = common.tools_config_path(tools_backup_dir)
    if backup_path:
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.writelines(content_lines)
        print(f"[完成] 备份配置文件：{backup_path}")

    anchor = os.path.join(material_root, default_cfg["anchor_dir"])
    os.makedirs(anchor, exist_ok=True)

    legacy_dir = os.path.join(material_root, ".xie-zuo-su-cai")
    if os.path.exists(legacy_dir):
        print(f"\n[提示] 检测到旧版数据目录：{legacy_dir}")
        print("旧数据不会被自动迁移。如需迁移，请手动将碎片/会话/主题定义移动到新的项目文件夹中。")

    print(f"\n[完成] 素材库已初始化：{material_root}")
    print(f"[完成] 主配置文件：{cfg_path}")
    return cfg_path


def main():
    ap = argparse.ArgumentParser(description="初始化写作素材库")
    ap.add_argument("--material-root", required=True, help="素材库根目录")
    ap.add_argument(
        "--input-materials",
        nargs="*",
        help="用户提供的输入素材文件或目录路径",
    )
    ap.add_argument(
        "--tools-backup-dir",
        help="Agent 自己的 tools 目录，用于备份用户配置",
    )
    args = ap.parse_args()
    cfg = run_init(
        args.material_root,
        input_materials=args.input_materials,
        tools_backup_dir=args.tools_backup_dir,
    )
    if cfg is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
