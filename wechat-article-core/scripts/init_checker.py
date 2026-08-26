"""路径初始化检查。

负责：
- 读取 config.yaml
- 判断是否首次配置
- 与用户交互获取三个路径
- 验证路径可用性
- 自动创建缺失的输出/模板目录
- 写回 config.yaml
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


def _expand_path(path: str) -> Path:
    """展开 ~ 和环境变量。"""
    if path is None:
        return Path()
    return Path(os.path.expandvars(os.path.expanduser(path)))


def load_config(path: Path) -> dict:
    """加载 YAML 配置文件。

    文件不存在或解析失败时抛出 RuntimeError，便于主编排层给出友好提示。
    """
    if not path.exists():
        raise RuntimeError(f"配置文件不存在：{path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise RuntimeError(f"配置文件 YAML 解析失败 {path}: {e}") from e
    except OSError as e:
        raise RuntimeError(f"无法读取配置文件 {path}: {e}") from e


def save_config(config: dict, path: Path) -> None:
    """写回 YAML 配置文件。"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)


def needs_initial_config(config: dict) -> bool:
    """判断是否需要首次配置。

    paths.*.value 任一为空字符串或缺失即视为未配置。
    """
    paths = config.get("paths", {})
    for key in ("input_dir", "output_dir", "user_templates_dir"):
        value = paths.get(key, {}).get("value")
        if not value:
            return True
    return False


def resolve_paths_from_config(config: dict) -> Dict[str, Path]:
    """从 config 解析出三个实际路径。

    优先级：config.paths.*.value > 对应环境变量 > default
    """
    paths_config = config.get("paths", {})
    resolved = {}
    for key in ("input_dir", "output_dir", "user_templates_dir"):
        cfg = paths_config.get(key, {})
        value = cfg.get("value")
        if not value:
            value = os.getenv(cfg.get("env"), cfg.get("default", ""))
        resolved[key] = _expand_path(value)
    return resolved


def validate_paths(paths: Dict[str, Path]) -> Tuple[Dict[str, Optional[Path]], List[str]]:
    """验证三个路径的可用性。

    返回：
    - resolved: 可用路径；不可用的 key 对应 None
    - messages: 需要展示给用户的提醒消息列表
    """
    messages = []
    resolved = {}

    input_dir = paths.get("input_dir")
    if input_dir and input_dir.exists() and input_dir.is_dir():
        if os.access(input_dir, os.R_OK):
            resolved["input_dir"] = input_dir
        else:
            messages.append(f"⚠️ 输入目录 {input_dir} 无读取权限，将不使用本地素材。")
            resolved["input_dir"] = None
    else:
        messages.append("⚠️ 输入目录不存在，当前没有本地素材可用。")
        resolved["input_dir"] = None

    output_dir = paths.get("output_dir")
    if output_dir:
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                messages.append(f"📁 输出目录不存在，已自动创建：{output_dir}")
            except OSError as e:
                messages.append(f"⚠️ 输出目录 {output_dir} 创建失败（{e}），将 fallback 到当前目录。")
                resolved["output_dir"] = None
        if output_dir.exists():
            if os.access(output_dir, os.W_OK):
                resolved["output_dir"] = output_dir
            else:
                messages.append(f"⚠️ 输出目录 {output_dir} 无写入权限，将 fallback 到当前目录。")
                resolved["output_dir"] = None

    templates_dir = paths.get("user_templates_dir")
    if templates_dir:
        if not templates_dir.exists():
            try:
                templates_dir.mkdir(parents=True, exist_ok=True)
                messages.append(f"📁 风格模板目录不存在，已自动创建：{templates_dir}")
            except OSError as e:
                messages.append(f"⚠️ 风格模板目录 {templates_dir} 创建失败（{e}），使用内置默认模板。")
                resolved["user_templates_dir"] = None
        if templates_dir.exists():
            if os.access(templates_dir, os.R_OK):
                resolved["user_templates_dir"] = templates_dir
            else:
                messages.append(f"⚠️ 风格模板目录 {templates_dir} 无读取权限，使用内置默认模板。")
                resolved["user_templates_dir"] = None

    return resolved, messages


def format_initial_prompt(config: dict) -> str:
    """生成首次配置提示语。"""
    paths = config.get("paths", {})
    lines = ["📁 首次使用公众号长文写作技能，请配置三个工作目录："]
    for idx, (key, label) in enumerate([
        ("input_dir", "输入目录（放素材）"),
        ("output_dir", "输出目录（放成稿）"),
        ("user_templates_dir", "风格模板目录（自定义 YAML）"),
    ], 1):
        default = paths.get(key, {}).get("default", "")
        lines.append(f"{idx}. {label}：{default}")
    lines.append("")
    lines.append("你可以：")
    lines.append('- 直接回复"确认"使用默认值')
    lines.append('- 回复"输入=/xxx, 输出=/yyy, 模板=/zzz"指定自定义路径')
    return "\n".join(lines)


def parse_user_paths_reply(reply: str, config: dict) -> Dict[str, str]:
    """解析用户对路径配置的回复。"""
    defaults = {
        key: config.get("paths", {}).get(key, {}).get("default", "")
        for key in ("input_dir", "output_dir", "user_templates_dir")
    }
    reply = reply.strip()
    if reply in ("确认", "ok", "OK", "默认"):
        return defaults

    mapping = {"输入": "input_dir", "输出": "output_dir", "模板": "user_templates_dir"}
    result = dict(defaults)
    for part in reply.split(","):
        part = part.strip()
        if "=" in part:
            key_part, value = part.split("=", 1)
            key = mapping.get(key_part.strip())
            if key:
                result[key] = value.strip()
    return result


def update_config_values(config: dict, paths: Dict[str, str]) -> dict:
    """把用户确认的路径写回 config 字典。"""
    for key, value in paths.items():
        config.setdefault("paths", {}).setdefault(key, {})["value"] = value
    return config
