#!/usr/bin/env python3
"""
OpenCLI Chrome Launcher

负责 OpenCLI 浏览器环境的全生命周期管理：
- check: 只读诊断
- init:  检测并绑定 Chrome profile 与 OpenCLI profile
- use:   确保浏览器在目标 profile 且扩展已连接
- cleanup: 释放 browser session 并清理残留窗口

本脚本由 SKILL.md 规范，供其他需要 OpenCLI 的技能在调用前执行。
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CONFIG_DIR = os.path.join(SKILL_DIR, "config")
WORKSPACE_DIR = os.path.join(SKILL_DIR, "workspace")
LOCK_FILE_PATH = os.path.join(WORKSPACE_DIR, ".opencli_chrome_launcher.lock")
CONFIG_PATH = os.path.join(CONFIG_DIR, "binding.json")


def _default_config() -> Dict[str, Any]:
    return {
        "initialized": False,
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
            "session_name": "opencli-chrome-launcher",
        },
    }


def load_config() -> Dict[str, Any]:
    """读取配置，文件不存在时返回默认结构。"""
    if not os.path.exists(CONFIG_PATH):
        return _default_config()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 合并默认值，防止旧配置缺少字段
        default = _default_config()
        for key, value in default.items():
            if isinstance(value, dict):
                data.setdefault(key, {})
                for sub_key, sub_value in value.items():
                    data[key].setdefault(sub_key, sub_value)
            else:
                data.setdefault(key, value)
        return data
    except Exception as e:
        print(f"[OpenCLIChromeLauncher] 读取配置失败: {e}，使用默认配置")
        return _default_config()


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到 config/binding.json。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class OpenCLIChromeLauncher:
    """OpenCLI 浏览器生命周期管理器。"""

    def __init__(self):
        self.config = load_config()
        self.browser_opened_by_skill = False

    # ---------- 公共入口 ----------

    def run(self, mode: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        if mode == "check":
            return self._run_check()
        elif mode == "init":
            return self._run_init()
        elif mode == "use":
            return self._run_use(session_name)
        elif mode == "cleanup":
            return self._run_cleanup(session_name)
        else:
            return self._error("UNKNOWN_MODE", f"不支持的 mode: {mode}")

    # ---------- 锁管理 ----------

    def _acquire_lock(self, timeout: int = 30) -> bool:
        """获取浏览器管理锁，防止多 Agent 并发操作 Chrome。"""
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        start = time.time()
        while os.path.exists(LOCK_FILE_PATH):
            if time.time() - start > timeout:
                return False
            time.sleep(0.5)
        try:
            with open(LOCK_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 创建锁文件失败: {e}")
            return False

    def _release_lock(self) -> None:
        """释放浏览器管理锁。"""
        try:
            if os.path.exists(LOCK_FILE_PATH):
                os.remove(LOCK_FILE_PATH)
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 释放锁文件失败: {e}")

    # ---------- check 模式 ----------

    def _run_check(self) -> Dict[str, Any]:
        """只读诊断，不改任何状态。"""
        version = self._get_opencli_version()
        doctor_ok = self._run_doctor()
        chrome_available = self._is_chrome_available()
        chrome_running = self._is_chrome_running()
        chrome_profiles = self._get_chrome_profiles()
        opencli_profiles = self._list_profiles()
        connected_id = self.get_connected_opencli_profile()
        current_chrome_profile_dir = self._get_current_chrome_profile_dir()
        binding_exists = os.path.exists(CONFIG_PATH)

        return {
            "status": "success",
            "module": "opencli-chrome-launcher",
            "message": "✅ check 完成",
            "data": {
                "opencli_installed": version is not None,
                "opencli_version": version,
                "doctor_passed": doctor_ok,
                "chrome_available": chrome_available,
                "chrome_running": chrome_running,
                "current_chrome_profile_dir": current_chrome_profile_dir,
                "connected_opencli_profile": connected_id,
                "chrome_profiles": chrome_profiles,
                "opencli_profiles": opencli_profiles,
                "binding_exists": binding_exists,
                "binding": self.config.get("browser_profile") if binding_exists else None,
            },
            "errors": [],
        }

    # ---------- init 模式 ----------

    def _run_init(self) -> Dict[str, Any]:
        """首次初始化：检测环境、匹配 profile、写入 binding.json。"""
        self.config = load_config()

        version = self._get_opencli_version()
        if not version:
            return self._error(
                "OPENCLI_NOT_FOUND",
                "opencli 未安装。",
                reason="系统找不到 opencli 命令。",
                action="请运行 npm install -g @jackwener/opencli。",
                impact="无法使用 OpenCLI。",
            )

        doctor_ok = self._run_doctor()
        if not doctor_ok:
            return self._error(
                "OPENCLI_DOCTOR_FAILED",
                "OpenCLI 浏览器桥接失败。",
                reason="Chrome 扩展未安装或调试端口未开启。",
                action="请安装 OpenCLI Chrome 扩展并启动 Chrome，或点击扩展图标激活连接。",
                impact="无法建立浏览器会话。",
            )

        if not self._is_chrome_available():
            return self._error(
                "CHROME_NOT_FOUND",
                "未检测到 Chrome 浏览器。",
                reason="macOS 上未找到 /Applications/Google Chrome.app。",
                action="请安装 Google Chrome 后重试。",
                impact="无法自动打开浏览器。",
            )

        chrome_profiles = self._get_chrome_profiles()
        opencli_profiles = self._list_profiles()
        if not opencli_profiles:
            return self._error(
                "OPENCLI_NO_PROFILE",
                "OpenCLI 未连接任何 Chrome profile。",
                reason="opencli profile list 返回空列表。",
                action="请启动 Chrome 并确保 OpenCLI 扩展已连接。",
                impact="无法建立浏览器会话。",
            )

        current_chrome_profile_dir = self._get_current_chrome_profile_dir()
        matched_profiles = self._match_profiles(
            opencli_profiles, chrome_profiles, current_chrome_profile_dir
        )
        selected = self._select_profile(matched_profiles, chrome_profiles)
        if not selected:
            return self._error(
                "BROWSER_PROFILE_NEEDED",
                "存在多个 Chrome profile，需要明确选择。",
                reason="无法自动推断哪个 profile 安装了 OpenCLI 扩展。",
                action="请在配置中指定 browser_profile.opencli_profile_id 和 chrome_profile_id。",
                impact="无法建立浏览器会话。",
            )

        self.config["browser_profile"]["opencli_profile_id"] = selected["opencli_id"]
        self.config["browser_profile"]["chrome_profile_id"] = selected.get("chrome_id")
        self.config["browser_profile"]["chrome_profile_name"] = selected.get(
            "chrome_name", "Unknown"
        )

        profile_id = selected["opencli_id"]
        chrome_profile_id = selected.get("chrome_id")
        if profile_id:
            self._switch_profile(profile_id)

        doctor_ok = self._run_doctor()
        if not doctor_ok:
            return self._error(
                "OPENCLI_DOCTOR_FAILED",
                "切换 profile 后 OpenCLI 桥接失败。",
                reason="profile 切换后扩展连接断开。",
                action="请检查 Chrome 中 OpenCLI 扩展图标状态，或尝试其他 profile。",
                impact="无法继续。",
            )

        self.config["initialized"] = True
        self.config["initialized_at"] = datetime.now(timezone.utc).isoformat()
        save_config(self.config)

        chrome_name = self.config["browser_profile"].get("chrome_profile_name", "")
        return {
            "status": "success",
            "module": "opencli-chrome-launcher",
            "message": f"✅ 初始化完成。OpenCLI {version}，Chrome profile '{chrome_name}'（{profile_id}）已连接。",
            "data": {
                "initialized": True,
                "opencli_version": version,
                "profile_id": profile_id,
                "chrome_profile_id": chrome_profile_id,
                "chrome_profile_name": chrome_name,
            },
            "errors": [],
        }

    def _select_profile(
        self,
        matched_profiles: List[Dict[str, Any]],
        chrome_profiles: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """
        选择目标 profile。
        优先级：
        1. 单 profile → 自动使用
        2. 多 profile → 优先选择 email/名称包含 openclaw/opencli 的
        3. 否则选择 default 标记的
        4. 否则选择第一个
        """
        if len(matched_profiles) == 1:
            return matched_profiles[0]

        for p in matched_profiles:
            chrome_id = (p.get("chrome_id") or "").lower()
            chrome_name = (p.get("chrome_name") or "").lower()
            opencli_name = (p.get("opencli_name") or "").lower()
            if "openclaw" in chrome_id or "openclaw" in chrome_name or "openclaw" in opencli_name:
                return p
            if "opencli" in chrome_id or "opencli" in chrome_name or "opencli" in opencli_name:
                return p

        for p in matched_profiles:
            if p.get("opencli_name") == "default":
                return p

        return matched_profiles[0] if matched_profiles else None

    # ---------- use 模式 ----------

    def _run_use(self, session_name: Optional[str]) -> Dict[str, Any]:
        """每次使用前的浏览器就绪流程。"""
        self.config = load_config()
        session = session_name or self.config["browser"].get(
            "session_name", "opencli-chrome-launcher"
        )

        if not self._acquire_lock():
            return self._error(
                "BROWSER_LOCKED",
                "另一个任务正在管理 Chrome 浏览器。",
                reason="锁文件已存在，可能另一个 Agent 正在操作浏览器。",
                action="请等待其他任务完成后再试。",
                impact="本次无法建立浏览器会话。",
            )

        try:
            if not self._get_opencli_version():
                return self._error(
                    "OPENCLI_NOT_FOUND",
                    "opencli 未安装。",
                    reason="系统找不到 opencli 命令。",
                    action="请运行 npm install -g @jackwener/opencli。",
                    impact="无法使用 OpenCLI。",
                )

            if not os.path.exists(CONFIG_PATH):
                return self._error(
                    "NO_BINDING_CONFIG",
                    "缺少 binding 配置。",
                    reason="config/binding.json 不存在。",
                    action="请先运行 init 模式完成初始化。",
                    impact="无法建立浏览器会话。",
                )

            profile_id = self.config["browser_profile"].get("opencli_profile_id")
            chrome_profile_id = self.config["browser_profile"].get("chrome_profile_id")

            if not profile_id:
                profiles = self._list_profiles()
                if profiles:
                    profile_id = profiles[0]["id"]
                    self.config["browser_profile"]["opencli_profile_id"] = profile_id
                    save_config(self.config)
                else:
                    return self._error(
                        "BROWSER_PROFILE_MISSING",
                        "未配置 OpenCLI profile。",
                        reason="配置中缺少 browser_profile.opencli_profile_id。",
                        action="请重新运行初始化，或手动配置 profile ID。",
                        impact="无法建立浏览器会话。",
                    )

            if not chrome_profile_id:
                chrome_profile_id = "Profile 1"
                self.config["browser_profile"]["chrome_profile_id"] = chrome_profile_id
                save_config(self.config)

            print("[OpenCLIChromeLauncher] 前置清理：关闭已有 OpenCLI Browser 残留标签...")
            self.cleanup_leaked_windows()

            ready_result = self.ensure_browser_with_profile(
                opencli_profile_id=profile_id,
                chrome_profile_dir=chrome_profile_id,
                max_retry=self.config["browser"].get("connection_retry_max", 15),
                retry_interval=self.config["browser"].get("connection_retry_interval", 2.0),
            )

            if not ready_result.get("success"):
                code = ready_result.get("code", "EXTENSION_NOT_INSTALLED")
                message_map = {
                    "CHROME_LAUNCH_FAILED": ("无法启动 Chrome。", "Chrome 启动命令执行失败。"),
                    "CHROME_LAUNCH_TIMEOUT": ("Chrome 启动后未检测到进程。", "浏览器可能仍在加载或启动命令无效。"),
                    "PROFILE_SWITCH_FAILED": ("切换 OpenCLI profile 失败。", "opencli profile use 执行失败。"),
                    "EXTENSION_NOT_INSTALLED": (
                        "OpenCLI 扩展未在目标 Chrome profile 中连接。",
                        "Chrome 已确保运行在目标 profile，但扩展仍未连接。",
                    ),
                    "CHROME_QUIT_FAILED": ("无法退出当前 Chrome。", "osascript / pkill 执行失败。"),
                    "CHROME_EXIT_TIMEOUT": ("等待 Chrome 退出超时。", "Chrome 未在预期时间内完全关闭。"),
                }
                short, reason = message_map.get(
                    code, ("浏览器就绪失败。", ready_result.get("reason", "未知原因"))
                )
                return self._error(
                    code,
                    short,
                    reason=reason,
                    action="请检查 Chrome 和 OpenCLI 扩展状态，或重新运行初始化。",
                    impact="无法使用 OpenCLI。",
                )

            return {
                "status": "success",
                "module": "opencli-chrome-launcher",
                "browser_opened_by_skill": self.browser_opened_by_skill,
                "profile_id": profile_id,
                "chrome_profile_id": chrome_profile_id,
                "session_name": session,
                "message": f"✅ 浏览器已就绪（profile: {profile_id}, session: {session}）。",
                "data": {},
                "errors": [],
            }
        finally:
            self._release_lock()

    # ---------- cleanup 模式 ----------

    def _run_cleanup(self, session_name: Optional[str]) -> Dict[str, Any]:
        """清理本次 session。"""
        self.config = load_config()
        session = session_name or self.config["browser"].get(
            "session_name", "opencli-chrome-launcher"
        )

        if not self.config["browser"].get("auto_close_browser", True):
            return {
                "status": "success",
                "module": "opencli-chrome-launcher",
                "message": "auto_close_browser 为 false，跳过清理。",
                "data": {},
                "errors": [],
            }

        results = []
        errors = []

        try:
            result = subprocess.run(
                ["opencli", "browser", session, "close"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                results.append(f"已释放 browser session: {session}")
            else:
                msg = f"释放 browser session 失败: {result.stderr.strip() or '未知错误'}"
                results.append(msg)
                errors.append({"code": "CLEANUP_WARNING", "message": msg})
        except Exception as e:
            msg = f"释放 browser session 异常: {e}"
            results.append(msg)
            errors.append({"code": "CLEANUP_EXCEPTION", "message": msg})

        try:
            cleanup_result = self.cleanup_leaked_windows()
            results.append(f"残留窗口清理: {cleanup_result}")
        except Exception as e:
            msg = f"残留窗口清理异常: {e}"
            results.append(msg)
            errors.append({"code": "CLEANUP_EXCEPTION", "message": msg})

        return {
            "status": "warning" if errors else "success",
            "module": "opencli-chrome-launcher",
            "message": (
                "✅ 浏览器清理完成。" if not errors else "⚠️ 浏览器清理部分失败。"
            ) + "；".join(results),
            "data": {},
            "errors": errors,
        }

    # ---------- 核心浏览器生命周期方法 ----------

    def ensure_browser_with_profile(
        self,
        opencli_profile_id: str,
        chrome_profile_dir: str,
        max_retry: int = 15,
        retry_interval: float = 2.0,
    ) -> Dict[str, Any]:
        """
        确保 Chrome 运行在目标 profile，且 OpenCLI 扩展已连接。
        """
        connected_id = self.get_connected_opencli_profile()
        if connected_id == opencli_profile_id and self._run_doctor():
            print(
                f"[OpenCLIChromeLauncher] 目标 profile {opencli_profile_id} 已连接，跳过浏览器操作"
            )
            return {"success": True}

        chrome_running = self._is_chrome_running()

        if chrome_running:
            if connected_id is None:
                print(
                    "[OpenCLIChromeLauncher] Chrome 在运行但无 OpenCLI profile 连接，准备重启到目标 profile"
                )
            else:
                print(
                    f"[OpenCLIChromeLauncher] Chrome 在运行但当前 profile {connected_id} 不是目标 {opencli_profile_id}，准备重启 Chrome"
                )

            if not self.quit_chrome():
                return {"success": False, "code": "CHROME_QUIT_FAILED", "reason": "退出 Chrome 失败"}

            if not self.wait_for_chrome_exit(max_attempts=60, interval=0.5):
                return {
                    "success": False,
                    "code": "CHROME_EXIT_TIMEOUT",
                    "reason": "等待 Chrome 退出超时",
                }

        print(f"[OpenCLIChromeLauncher] 用 profile {chrome_profile_dir} 启动 Chrome")
        if not self.launch_chrome(profile_dir=chrome_profile_dir):
            return {"success": False, "code": "CHROME_LAUNCH_FAILED", "reason": "启动 Chrome 失败"}

        if not self._wait_for_chrome(max_wait=15):
            return {
                "success": False,
                "code": "CHROME_LAUNCH_TIMEOUT",
                "reason": "Chrome 启动后未检测到进程",
            }

        print(f"[OpenCLIChromeLauncher] 切换 OpenCLI profile: {opencli_profile_id}")
        if not self._switch_profile(opencli_profile_id):
            return {
                "success": False,
                "code": "PROFILE_SWITCH_FAILED",
                "reason": "opencli profile use 执行失败",
            }

        print("[OpenCLIChromeLauncher] 等待 extension 连接...")
        for i in range(max_retry):
            connected_id = self.get_connected_opencli_profile()
            if connected_id == opencli_profile_id and self._run_doctor():
                print(f"[OpenCLIChromeLauncher] extension 已连接 ({opencli_profile_id})")
                self.browser_opened_by_skill = True
                return {"success": True}
            print(f"[OpenCLIChromeLauncher] 等待 extension 连接... ({i + 1}/{max_retry})")
            time.sleep(retry_interval)

        return {
            "success": False,
            "code": "EXTENSION_NOT_INSTALLED",
            "reason": "扩展连接超时，可能目标 Chrome profile 未安装或未激活 OpenCLI 扩展",
        }

    def get_connected_opencli_profile(self) -> Optional[str]:
        """获取当前已连接的 OpenCLI profile ID。"""
        try:
            result = subprocess.run(
                ["opencli", "profile", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None
            output = result.stdout
            if "Connected Browser Bridge profiles" not in output:
                return None

            for line in output.splitlines():
                line = line.strip()
                if "— connected" in line or "-- connected" in line:
                    parts = line.split()
                    if parts:
                        return parts[0].rstrip(":")
            return None
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 获取已连接 profile 失败: {e}")
            return None

    def launch_chrome(self, profile_dir: Optional[str] = None) -> bool:
        """启动 Chrome。macOS 直接调用二进制，避免 open -a 忽略 --profile-directory 的问题。"""
        system = platform.system()
        try:
            if system == "Darwin":
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if profile_dir:
                    subprocess.Popen(
                        [chrome_path, f"--profile-directory={profile_dir}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                else:
                    subprocess.Popen(
                        [chrome_path, "--new-window"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                return True

            elif system == "Linux":
                chrome_cmd = ["google-chrome", "--new-window"]
                if profile_dir:
                    chrome_cmd.insert(1, f"--profile-directory={profile_dir}")
                subprocess.Popen(
                    chrome_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True

            elif system == "Windows":
                chrome_cmd = ["start", "chrome", "--new-window"]
                if profile_dir:
                    chrome_cmd.insert(2, f"--profile-directory={profile_dir}")
                subprocess.Popen(
                    chrome_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True

            else:
                print(f"[OpenCLIChromeLauncher] 不支持的平台: {system}")
                return False

        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 启动 Chrome 失败: {e}")
            return False

    def quit_chrome(self) -> bool:
        """退出 Chrome。先优雅退出，再 killall 兜底。"""
        system = platform.system()
        try:
            if system == "Darwin":
                script = '''
                tell application "Google Chrome"
                    if running then quit
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=False, timeout=10)
                time.sleep(2)

                if self._is_chrome_running():
                    print("[OpenCLIChromeLauncher] osascript 未生效，使用 killall 强制退出 Chrome")
                    subprocess.run(
                        ["killall", "-x", "-9", "Google Chrome"],
                        capture_output=True,
                        timeout=15,
                    )
                    time.sleep(2)
                    if self._is_chrome_running():
                        subprocess.run(
                            ["killall", "-x", "-9", "Google Chrome"],
                            capture_output=True,
                            timeout=15,
                        )
                        time.sleep(1)

            elif system == "Linux":
                subprocess.run(["killall", "-9", "chrome"], check=False, timeout=10)
            elif system == "Windows":
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], check=False, timeout=10)

            return True
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 退出 Chrome 失败: {e}")
            return False

    def wait_for_chrome_exit(self, max_attempts: int = 60, interval: float = 0.5) -> bool:
        """等待 Chrome 进程完全退出。"""
        for i in range(max_attempts):
            if not self._is_chrome_running():
                return True
            if i % 4 == 0:
                print(f"[OpenCLIChromeLauncher] 等待 Chrome 退出... ({i + 1}/{max_attempts})")
            time.sleep(interval)
        return False

    def cleanup_leaked_windows(self) -> str:
        """
        清理 OpenCLI 残留的 "OpenCLI Browser" 标签和空白窗口（macOS）。
        两阶段：
        1. 关闭所有标题包含 "OpenCLI Browser" 的标签
        2. 关闭只剩 about:blank / chrome://newtab 的空窗口
        """
        if platform.system() != "Darwin":
            return "非 macOS 平台，跳过"

        script = '''
        tell application "Google Chrome"
            set closedTabs to 0
            set closedWindows to 0

            -- 第一阶段：关闭所有标题包含 "OpenCLI Browser" 的标签
            repeat with w from (count windows) to 1 by -1
                set win to window w
                set allTabs to tabs of win
                repeat with t from (count allTabs) to 1 by -1
                    try
                        set tabTitle to title of tab t of win
                        if tabTitle contains "OpenCLI Browser" then
                            close tab t of win
                            set closedTabs to closedTabs + 1
                        end if
                    on error
                        -- 忽略无法读取的标签
                    end try
                end repeat
            end repeat

            -- 第二阶段：关闭只剩 about:blank / chrome://newtab 的空窗口
            repeat with w from (count windows) to 1 by -1
                set win to window w
                set allTabs to tabs of win
                if (count allTabs) = 0 then
                    close win
                    set closedWindows to closedWindows + 1
                else
                    set isLeakedWindow to true
                    repeat with t in allTabs
                        try
                            set tabURL to URL of t
                            set tabTitle to title of t
                            if not (tabURL starts with "about:blank" or tabURL starts with "chrome://newtab") then
                                set isLeakedWindow to false
                                exit repeat
                            end if
                        on error
                            -- 忽略无法读取的标签
                        end try
                    end repeat
                    if isLeakedWindow then
                        repeat with t from (count allTabs) to 1 by -1
                            try
                                close tab t of win
                                set closedTabs to closedTabs + 1
                            end try
                        end repeat
                        if (count tabs of win) = 0 then
                            close win
                            set closedWindows to closedWindows + 1
                        end if
                    end if
                end if
            end repeat

            return "closedTabs:" & closedTabs & ",closedWindows:" & closedWindows
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() or "无残留窗口"
        except Exception as e:
            return f"清理失败: {e}"

    # ---------- 底层命令 ----------

    def _get_opencli_version(self) -> Optional[str]:
        """获取 opencli 版本。"""
        if shutil.which("opencli") is None:
            return None
        try:
            result = subprocess.run(
                ["opencli", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _run_doctor(self) -> bool:
        """执行 opencli doctor，返回是否通过。"""
        status = self._bridge_status()
        return status.get("ok", False)

    def _bridge_status(self) -> Dict[str, Any]:
        """获取 OpenCLI 桥接状态。"""
        if not shutil.which("opencli"):
            return {"ok": False, "error": "opencli not installed"}

        try:
            result = subprocess.run(
                ["opencli", "doctor"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            has_fail = "[FAIL]" in output or "Connectivity: failed" in output
            has_missing_extension = "[MISSING] Extension" in output

            if result.returncode != 0 or has_fail or has_missing_extension:
                error = "OpenCLI bridge not ready"
                if "Extension" in output and (
                    "not connected" in output or "MISSING" in output
                ):
                    error = "OpenCLI extension not connected"
                elif "Connectivity" in output:
                    error = "OpenCLI connectivity failed"
                return {"ok": False, "error": error, "output": output}

            return {"ok": True, "output": output}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _is_chrome_available(self) -> bool:
        """检查 Chrome 是否安装。"""
        if platform.system() == "Darwin":
            return os.path.exists("/Applications/Google Chrome.app")
        return (
            shutil.which("google-chrome") is not None
            or shutil.which("chromium") is not None
        )

    def _is_chrome_running(self) -> bool:
        """检查 Chrome 进程是否运行。"""
        system = platform.system()
        try:
            if system == "Darwin":
                result = subprocess.run(
                    ["pgrep", "-x", "Google Chrome"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif system == "Linux":
                result = subprocess.run(
                    ["pgrep", "-x", "chrome"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif system == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "chrome.exe" in result.stdout
            else:
                return False

            return result.returncode == 0 and result.stdout.strip() != ""
        except Exception:
            return False

    def _wait_for_chrome(self, max_wait: int = 15) -> bool:
        """等待 Chrome 进程出现。"""
        for i in range(max_wait):
            if self._is_chrome_running():
                return True
            time.sleep(1)
        return False

    def _list_profiles(self) -> List[Dict[str, str]]:
        """获取 OpenCLI profile 列表。"""
        try:
            result = subprocess.run(
                ["opencli", "profile", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return self._parse_profile_list(result.stdout)
        except Exception:
            return []

    def _parse_profile_list(self, output: str) -> List[Dict[str, str]]:
        """解析 opencli profile list 输出。"""
        profiles = []
        in_connected = False
        in_disconnected = False

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("Connected Browser Bridge profiles"):
                in_connected = True
                in_disconnected = False
                continue
            if line.startswith("Disconnected saved profiles"):
                in_connected = False
                in_disconnected = True
                continue

            parts = line.split()
            if not parts:
                continue

            profile_id = parts[0].rstrip(":")
            name = ""
            is_connected = in_connected or (
                "connected" in line.lower() and "not connected" not in line.lower()
            )

            for part in parts[1:]:
                lower = part.lower()
                if lower in ("connected", "not", "—", "--", "default"):
                    continue
                if lower.startswith("v") and len(lower) > 1 and lower[1].isdigit():
                    continue
                name = part
                break

            profiles.append({
                "id": profile_id,
                "name": name,
                "connected": is_connected,
            })

        return profiles

    def _switch_profile(self, profile_id: str) -> bool:
        """切换默认 profile。"""
        try:
            result = subprocess.run(
                ["opencli", "profile", "use", profile_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_chrome_profiles(self) -> List[Dict[str, str]]:
        """读取 Chrome Local State 获取本地 profile 列表。"""
        system = platform.system()
        if system == "Darwin":
            local_state_path = os.path.expanduser(
                "~/Library/Application Support/Google/Chrome/Local State"
            )
        elif system == "Linux":
            local_state_path = os.path.expanduser("~/.config/google-chrome/Local State")
        elif system == "Windows":
            local_state_path = os.path.expanduser(
                "~/AppData/Local/Google/Chrome/User Data/Local State"
            )
        else:
            return []

        if not os.path.exists(local_state_path):
            return []

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            profiles = []
            for profile_id, info in info_cache.items():
                profiles.append({
                    "id": profile_id,
                    "name": info.get("name", profile_id),
                    "email": info.get("email", ""),
                    "gaia_name": info.get("gaia_name", ""),
                })
            return profiles
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 读取 Chrome Local State 失败: {e}")
            return []

    def _get_current_chrome_profile_dir(self) -> Optional[str]:
        """从当前运行的 Chrome 主进程命令行中解析 --profile-directory。"""
        system = platform.system()
        try:
            if system == "Darwin":
                result = subprocess.run(
                    ["ps", "-eo", "pid,command"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" in line and "--type=" not in line:
                        return self._parse_profile_directory_from_command(line)
            elif system == "Linux":
                result = subprocess.run(
                    ["ps", "-eo", "pid,command"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "google-chrome" in line.lower() and "--type=" not in line:
                        return self._parse_profile_directory_from_command(line)
            elif system == "Windows":
                result = subprocess.run(
                    ["wmic", "process", "where", "name='chrome.exe'", "get", "CommandLine"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "chrome.exe" in line.lower() and "--type=" not in line:
                        return self._parse_profile_directory_from_command(line)
        except Exception as e:
            print(f"[OpenCLIChromeLauncher] 解析当前 Chrome profile 失败: {e}")
        return None

    def _parse_profile_directory_from_command(self, command_line: str) -> Optional[str]:
        """从命令行字符串中解析 --profile-directory 的值，支持带空格的目录名。"""
        parts = command_line.split()
        for i, part in enumerate(parts):
            if part.startswith("--profile-directory="):
                value = part.split("=", 1)[1].strip('"')
                j = i + 1
                while j < len(parts) and not parts[j].startswith("--"):
                    value += " " + parts[j].strip('"')
                    j += 1
                return value.strip()
        return None

    def _match_profiles(
        self,
        opencli_profiles: List[Dict[str, Any]],
        chrome_profiles: List[Dict[str, str]],
        current_chrome_profile_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """将 OpenCLI profile 与 Chrome profile 进行匹配。"""
        matched = []
        used_chrome_ids = set()

        if current_chrome_profile_dir:
            for oc in opencli_profiles:
                if oc.get("connected"):
                    match = None
                    for cp in chrome_profiles:
                        if cp.get("id") == current_chrome_profile_dir:
                            match = cp
                            used_chrome_ids.add(cp.get("id"))
                            break
                    matched.append({
                        "opencli_id": oc.get("id", ""),
                        "opencli_name": oc.get("name", ""),
                        "opencli_connected": True,
                        "chrome_id": match.get("id") if match else current_chrome_profile_dir,
                        "chrome_name": match.get("name") if match else current_chrome_profile_dir,
                        "chrome_email": match.get("email") if match else "",
                    })
                    break

        for oc in opencli_profiles:
            oc_id = oc.get("id", "")
            if any(m["opencli_id"] == oc_id for m in matched):
                continue

            oc_name = oc.get("name", "").lower()
            match = None

            for cp in chrome_profiles:
                cp_id = cp.get("id", "")
                if cp_id in used_chrome_ids:
                    continue
                cp_name = cp.get("name", "").lower()
                if oc_name and (oc_name == cp_id.lower() or oc_name == cp_name):
                    match = cp
                    used_chrome_ids.add(cp_id)
                    break

            if not match and chrome_profiles:
                for cp in chrome_profiles:
                    if cp.get("id") not in used_chrome_ids:
                        match = cp
                        used_chrome_ids.add(cp.get("id"))
                        break

            matched.append({
                "opencli_id": oc_id,
                "opencli_name": oc.get("name", ""),
                "opencli_connected": oc.get("connected", False),
                "chrome_id": match.get("id") if match else None,
                "chrome_name": match.get("name") if match else "Unknown",
                "chrome_email": match.get("email") if match else "",
            })

        return matched

    # ---------- 辅助方法 ----------

    def _error(
        self,
        code: str,
        short: str,
        reason: str = "",
        action: str = "",
        impact: str = "",
    ) -> Dict[str, Any]:
        """构造统一错误返回。"""
        message = f"❌ {short}"
        if reason:
            message += f"\n原因：{reason}"
        if action:
            message += f"\n操作：{action}"
        if impact:
            message += f"\n影响：{impact}"

        return {
            "status": "failed",
            "module": "opencli-chrome-launcher",
            "message": message,
            "data": {},
            "errors": [{"code": code, "message": short}],
        }


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    session = sys.argv[2] if len(sys.argv) > 2 else None

    launcher = OpenCLIChromeLauncher()
    result = launcher.run(mode, session)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
