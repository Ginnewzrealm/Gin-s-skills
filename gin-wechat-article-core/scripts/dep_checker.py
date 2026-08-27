"""依赖检查工具。

检查可选的 baoyu 技能与本地 WPS skill 是否已安装。
配置来源：gin-wechat-article-core/config.yaml 的 optional_dependencies 节。
"""
import os
from pathlib import Path
from typing import Optional

import yaml


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _expand_path(path: Optional[str]) -> Path:
    """展开 ~ 和环境变量。"""
    if path is None:
        return Path()
    return Path(os.path.expandvars(os.path.expanduser(path)))


def load_config(path: Path = CONFIG_PATH) -> dict:
    """加载 config.yaml，文件不存在时返回空字典。"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError(f"无法读取配置文件 {path}: {e}") from e


def check_local_skill(env_var: str, default: str) -> str:
    """检查本地 skill 目录是否存在。

    Returns:
        "installed" 或 "missing"
    """
    path = _expand_path(os.getenv(env_var, default))
    return "installed" if path.exists() else "missing"


def check_baoyu_skill(skill_name: str) -> str:
    """检查 baoyu skill 是否已安装到本地 skills 目录。

    baoyu 技能通过 npx skills add 安装后，通常位于
    ~/.agents/skills/<skill-name>/。
    """
    base = _expand_path(os.getenv("AGENTS_SKILLS_PATH", "~/.agents/skills"))
    path = base / skill_name
    return "installed" if path.exists() else "missing"


def check_all_optional_deps(config: Optional[dict] = None) -> dict:
    """检查所有可选依赖状态。

    从 config.yaml 的 optional_dependencies 节读取依赖定义，
    避免在代码中硬编码 skill 列表。
    """
    if config is None:
        config = load_config()

    deps_config = config.get("optional_dependencies", {})
    result = {}
    for name, cfg in deps_config.items():
        if not isinstance(cfg, dict):
            continue
        dep_type = cfg.get("type", "baoyu")
        if dep_type == "local":
            result[name] = check_local_skill(
                cfg.get("env", ""),
                cfg.get("default", ""),
            )
        else:
            # 默认按 baoyu skill 处理：id 为 jimliu/baoyu-skills@<skill-name>
            # 优先使用配置里的 skill_name，否则从 id 截取
            skill_name = cfg.get("skill_name") or name
            result[name] = check_baoyu_skill(skill_name)
    return result


def format_missing_reminder(deps: dict) -> str:
    """格式化缺失依赖的提醒文案。"""
    missing = [name for name, status in deps.items() if status == "missing"]
    if not missing:
        return ""
    lines = ["⚠️ 以下可选技能未安装，相关功能将不可用："]
    for name in missing:
        if name == "wps-skill":
            lines.append(
                f"- {name}：保存到本地 Word 文档功能不可用，"
                "将 fallback 为 Markdown 文件。"
            )
        else:
            lines.append(f"- {name}")
    lines.append("如需使用，请安装对应 skill。")
    return "\n".join(lines)
