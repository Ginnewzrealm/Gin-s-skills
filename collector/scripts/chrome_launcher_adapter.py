#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chrome_launcher_adapter.py — collector 的 OpenCLI 浏览器启动适配器。

优先调用 opencli-chrome-launcher 管理 Chrome 生命周期；找不到时降级到
collector 自带的 browser_manager.py。
"""
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))


def _launcher_candidates():
    """返回可能的 opencli-chrome-launcher 安装路径。"""
    env = os.environ.get("OPENCLI_CHROME_LAUNCHER_DIR")
    home = os.path.expanduser("~")
    return [
        env,
        os.path.join(home, ".agents", "skills", "opencli-chrome-launcher"),
        os.path.join(home, ".claude", "skills", "opencli-chrome-launcher"),
        os.path.join(_SKILL_DIR, "..", "opencli-chrome-launcher"),
    ]


def find_opencli_chrome_launcher_script() -> Optional[str]:
    """查找 launcher 脚本路径；找不到返回 None。"""
    for base in _launcher_candidates():
        if not base:
            continue
        path = os.path.join(os.path.abspath(base), "scripts", "opencli_chrome_launcher.py")
        if os.path.isfile(path):
            return path
    return None


def run_launcher(mode: str, session_name: Optional[str] = None,
                 launcher_script: Optional[str] = None) -> Dict[str, Any]:
    """调用 opencli-chrome-launcher 指定模式，返回解析后的 JSON。"""
    script = launcher_script or find_opencli_chrome_launcher_script()
    if not script:
        return {
            "status": "failed",
            "module": "chrome-launcher-adapter",
            "message": "未找到 opencli-chrome-launcher",
            "data": {},
            "errors": [{"code": "LAUNCHER_NOT_FOUND",
                        "message": "opencli-chrome-launcher 未安装"}],
        }

    cmd = [sys.executable, script, mode]
    if session_name:
        cmd.append(session_name)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "module": "chrome-launcher-adapter",
            "message": "launcher %s 输出解析失败" % mode,
            "data": {"stdout": result.stdout, "stderr": result.stderr},
            "errors": [{"code": "LAUNCHER_OUTPUT_ERROR",
                        "message": result.stderr or result.stdout}],
        }


def _run_internal_browser_manager(mode: str, session_name: Optional[str] = None) -> Dict[str, Any]:
    """降级调用 collector 自带的 browser_manager.py。"""
    script = os.path.join(_SCRIPT_DIR, "browser_manager.py")
    cmd = [sys.executable, script, mode]
    if session_name:
        cmd.append(session_name)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "module": "browser-manager",
            "message": "browser_manager %s 输出解析失败" % mode,
            "data": {"stdout": result.stdout, "stderr": result.stderr},
            "errors": [{"code": "BROWSER_MANAGER_ERROR",
                        "message": result.stderr or result.stdout}],
        }


def ensure_browser_ready(session_name: Optional[str] = None) -> Tuple[bool, Dict[str, Any], str]:
    """确保浏览器就绪。返回 (是否成功, 结果字典, 来源)。"""
    script = find_opencli_chrome_launcher_script()
    if script:
        res = run_launcher("use", session_name, launcher_script=script)
        if res.get("status") == "success":
            return True, res, "opencli-chrome-launcher"

        errors = res.get("errors", [])
        if any(e.get("code") == "NO_BINDING_CONFIG" for e in errors):
            init_res = run_launcher("init", session_name, launcher_script=script)
            if init_res.get("status") != "success":
                return False, init_res, "opencli-chrome-launcher"
            res = run_launcher("use", session_name, launcher_script=script)
            if res.get("status") == "success":
                return True, res, "opencli-chrome-launcher"

        return False, res, "opencli-chrome-launcher"

    # 降级到内部 browser_manager
    res = _run_internal_browser_manager("init", session_name)
    if res.get("status") != "success":
        return False, res, "internal-browser-manager"
    res = _run_internal_browser_manager("use", session_name)
    if res.get("status") == "success":
        return True, res, "internal-browser-manager"
    return False, res, "internal-browser-manager"


def cleanup_browser(session_name: Optional[str] = None, source: Optional[str] = None) -> Dict[str, Any]:
    """根据来源执行对应的 cleanup。"""
    if source == "opencli-chrome-launcher":
        return run_launcher("cleanup", session_name)
    return _run_internal_browser_manager("cleanup", session_name)
