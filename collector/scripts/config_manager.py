#!/usr/bin/env python3
"""
配置管理模块。

读写 collector 技能目录下的 config/config.json
"""

import json
import os
from typing import Any, Dict

# 配置路径：基于脚本所在目录的相对路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "config"))
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "initialized": False,
    "opencli": {
        "installed": False,
        "version": None,
        "doctor_passed": False,
    },
    "browser_profile": {
        "chrome_profile_id": None,
        "chrome_profile_name": None,
        "opencli_profile_id": None,
    },
    "browser": {
        "auto_open_browser": True,
        "auto_close_browser": True,
        "connection_retry_interval": 2,
        "connection_retry_max": 15,
        "session_name": "collector",
    },
    "env_check": {
        "initialized_at": None,
        "checks": {
            "opencli_installed": False,
            "chrome_available": False,
            "profile_selected": False,
            "doctor_passed": False,
        }
    },
}


def load_config() -> Dict[str, Any]:
    """读取配置文件，不存在则返回默认配置。"""
    if not os.path.exists(CONFIG_PATH):
        return _copy_config(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 合并默认值，防止升级后缺少字段
        merged = _copy_config(DEFAULT_CONFIG)
        _deep_merge(merged, config)
        return merged
    except Exception as e:
        print(f"[ConfigManager] 读取配置失败: {e}，使用默认配置")
        return _copy_config(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> None:
    """保存配置文件。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ConfigManager] 保存配置失败: {e}")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """递归合并两个字典。"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _copy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """深拷贝配置。"""
    return json.loads(json.dumps(config))


def main():
    """简单的 CLI 测试入口。"""
    config = load_config()
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
