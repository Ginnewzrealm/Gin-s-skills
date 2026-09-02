# collector 委托浏览器生命周期给 opencli-chrome-launcher 实现计划

> **面向 AI 代理的工作者：** 本计划作用于 `~/.agents/skills/collector`，非 Git 仓库，无法使用 git commit。每完成一个任务请在回复中记录变更文件与验证结果。

**目标：** 让 collector 在调用 OpenCLI 之前，优先使用 `opencli-chrome-launcher` 确保 Chrome 浏览器就绪；launcher 不存在时降级使用 collector 自带的 `browser_manager.py`。

**架构：** 新增 `scripts/chrome_launcher_adapter.py` 统一封装 launcher 查找、use/init/cleanup 调用与内部 fallback；`main.py` 的 `run_opencli_cmd` 改为通过 adapter 准备浏览器；`SKILL.md` 更新依赖说明。

**技术栈：** Python 标准库、subprocess、JSON。

---

## 文件职责

| 文件 | 职责 |
|---|---|
| `scripts/chrome_launcher_adapter.py` | 新建：查找 opencli-chrome-launcher、调用 use/init/cleanup、找不到时 fallback 到内部 browser_manager |
| `main.py` | 修改：`run_opencli_cmd` 使用 adapter 替代直接调用内部 browser_manager |
| `SKILL.md` | 修改：浏览器管理由 opencli-chrome-launcher 负责，内部 browser_manager 作为 fallback |
| `tests/test_chrome_launcher_adapter.py` | 新建：adapter 路径查找与 launcher 调用测试 |
| `tests/test_main.py` | 修改：原 `run_browser_manager` 相关测试改为 mock adapter 的 `ensure_browser_ready` / `cleanup_browser` |

---

## 任务 1：实现 chrome_launcher_adapter.py

**文件：**
- 创建：`scripts/chrome_launcher_adapter.py`
- 测试：`tests/test_chrome_launcher_adapter.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_chrome_launcher_adapter.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_chrome_launcher_adapter.py"""
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts import chrome_launcher_adapter as adapter


def test_find_launcher_from_env(tmp_path):
    fake = tmp_path / "opencli-chrome-launcher" / "scripts" / "opencli_chrome_launcher.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("# fake", encoding="utf-8")
    with patch.dict(os.environ, {"OPENCLI_CHROME_LAUNCHER_DIR": str(tmp_path / "opencli-chrome-launcher")}):
        found = adapter.find_opencli_chrome_launcher_script()
    assert found == str(fake)


def test_find_launcher_returns_none_when_missing(tmp_path):
    with patch.dict(os.environ, {"OPENCLI_CHROME_LAUNCHER_DIR": str(tmp_path / "not-exist")}):
        found = adapter.find_opencli_chrome_launcher_script()
    assert found is None


def test_run_launcher_returns_success_json(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            stdout = json.dumps({"status": "success", "module": "opencli-chrome-launcher"})
            stderr = ""
            returncode = 0
        return R()

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    res = adapter.run_launcher("use", launcher_script=str(fake))
    assert res["status"] == "success"


def test_run_launcher_parses_failed_output(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            stdout = "not json"
            stderr = "boom"
            returncode = 1
        return R()

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    res = adapter.run_launcher("use", launcher_script=str(fake))
    assert res["status"] == "failed"
    assert res["errors"][0]["code"] == "LAUNCHER_OUTPUT_ERROR"


def test_ensure_browser_ready_uses_launcher_when_available(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: str(fake))

    responses = [
        {"status": "success", "module": "opencli-chrome-launcher"},
    ]

    def fake_run_launcher(mode, session=None, launcher_script=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "run_launcher", fake_run_launcher)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True
    assert source == "opencli-chrome-launcher"


def test_ensure_browser_ready_init_when_no_binding(monkeypatch, tmp_path):
    fake = tmp_path / "opencli_chrome_launcher.py"
    fake.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: str(fake))

    responses = [
        {"status": "failed", "errors": [{"code": "NO_BINDING_CONFIG"}]},
        {"status": "success", "module": "opencli-chrome-launcher"},  # init
        {"status": "success", "module": "opencli-chrome-launcher"},  # use again
    ]

    def fake_run_launcher(mode, session=None, launcher_script=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "run_launcher", fake_run_launcher)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True


def test_ensure_browser_ready_falls_back_to_internal(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter, "find_opencli_chrome_launcher_script", lambda: None)

    responses = [
        {"status": "success"},  # init
        {"status": "success"},  # use
    ]

    def fake_internal(mode, session=None):
        return responses.pop(0)

    monkeypatch.setattr(adapter, "_run_internal_browser_manager", fake_internal)
    ok, res, source = adapter.ensure_browser_ready("collector")
    assert ok is True
    assert source == "internal-browser-manager"


def test_cleanup_browser_uses_source(monkeypatch, tmp_path):
    cleanup_called = []

    def fake_launcher_cleanup(mode, session=None, launcher_script=None):
        cleanup_called.append(("launcher", mode, session))
        return {"status": "success"}

    monkeypatch.setattr(adapter, "run_launcher", fake_launcher_cleanup)
    adapter.cleanup_browser("collector", source="opencli-chrome-launcher")
    assert cleanup_called == [("launcher", "cleanup", "collector")]


def test_cleanup_browser_falls_back_internal(monkeypatch):
    cleanup_called = []

    def fake_internal(mode, session=None):
        cleanup_called.append(("internal", mode, session))
        return {"status": "success"}

    monkeypatch.setattr(adapter, "_run_internal_browser_manager", fake_internal)
    adapter.cleanup_browser("collector", source="internal-browser-manager")
    assert cleanup_called == [("internal", "cleanup", "collector")]
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd ~/.agents/skills/collector
python3 -m pytest tests/test_chrome_launcher_adapter.py -v
```

预期：全部 FAIL（文件不存在）

- [ ] **步骤 3：实现 adapter**

创建 `scripts/chrome_launcher_adapter.py`：

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd ~/.agents/skills/collector
python3 -m pytest tests/test_chrome_launcher_adapter.py -v
```

预期：8 个 PASS

- [ ] **步骤 5：记录变更**

新增文件：
- `scripts/chrome_launcher_adapter.py`
- `tests/test_chrome_launcher_adapter.py`

---

## 任务 2：修改 main.py 使用 adapter

**文件：**
- 修改：`main.py:18-86`（OpenCLI 浏览器生命周期管理区域）
- 修改：`main.py:56-86`（`run_opencli_cmd`）

- [ ] **步骤 1：编写失败测试**

在 `tests/test_main.py` 中新增/替换 `TestBrowserManagerIntegration`：

```python
class TestBrowserLauncherAdapterIntegration:
    """OpenCLI 浏览器 launcher adapter 集成测试"""

    def test_run_opencli_cmd_prepares_browser_and_cleans(self, monkeypatch):
        calls = []

        def fake_ensure(session=None):
            calls.append(("ensure", session))
            return True, {"status": "success"}, "opencli-chrome-launcher"

        def fake_cleanup(session=None, source=None):
            calls.append(("cleanup", session, source))
            return {"status": "success"}

        def fake_subprocess_run(cmd, **kwargs):
            calls.append(("subprocess", cmd))
            class FakeResult:
                returncode = 0
                stdout = b"fake content"
                stderr = b""
            return FakeResult()

        from scripts import chrome_launcher_adapter
        monkeypatch.setattr(chrome_launcher_adapter, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(chrome_launcher_adapter, "cleanup_browser", fake_cleanup)
        monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

        result = main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                      "https://x.com/u/status/123")

        assert result.returncode == 0
        assert calls == [
            ("ensure", "collector"),
            ("subprocess", ["opencli", "twitter", "thread", "123"]),
            ("cleanup", "collector", "opencli-chrome-launcher"),
        ]

    def test_run_opencli_cmd_exits_when_browser_not_ready(self, monkeypatch):
        def fake_ensure(session=None):
            return False, {"status": "failed", "message": "opencli 未安装"}, "opencli-chrome-launcher"

        def fake_cleanup(session=None, source=None):
            return {"status": "success"}

        from scripts import chrome_launcher_adapter
        monkeypatch.setattr(chrome_launcher_adapter, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(chrome_launcher_adapter, "cleanup_browser", fake_cleanup)

        with pytest.raises(SystemExit) as exc_info:
            main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                  "https://x.com/u/status/123", allow_fallback=False)
        assert exc_info.value.code == 1

    def test_run_opencli_cmd_fallback_returns_none(self, monkeypatch):
        def fake_ensure(session=None):
            return False, {"status": "failed", "message": "opencli 未安装"}, "opencli-chrome-launcher"

        def fake_cleanup(session=None, source=None):
            return {"status": "success"}

        from scripts import chrome_launcher_adapter
        monkeypatch.setattr(chrome_launcher_adapter, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(chrome_launcher_adapter, "cleanup_browser", fake_cleanup)

        result = main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                      "https://x.com/u/status/123", allow_fallback=True)
        assert result is None
```

同时删除或注释原 `TestBrowserManagerIntegration` 和 `TestBrowserManagerCleanup`（它们测试的是内部 browser_manager，现在由 adapter fallback 路径覆盖）。

- [ ] **步骤 2：运行测试验证失败**

```bash
python3 -m pytest tests/test_main.py::TestBrowserLauncherAdapterIntegration -v
```

预期：FAIL，因为 main.py 还未导入 adapter 函数。

- [ ] **步骤 3：修改 main.py**

1. 在 `main.py` 顶部 OpenCLI 区域替换为 adapter 导入：

```python
# ---------- OpenCLI 浏览器生命周期管理 ----------

from scripts.chrome_launcher_adapter import ensure_browser_ready, cleanup_browser


def run_opencli_cmd(cmd, input_arg, allow_fallback=False):
    """
    在浏览器就绪后执行 OpenCLI 命令，并在 finally 中清理。

    浏览器就绪优先由 opencli-chrome-launcher 负责；launcher 未安装时
    降级使用 collector 自带的 browser_manager.py。
    """
    ok, result, source = ensure_browser_ready(session_name="collector")
    if not ok:
        if allow_fallback:
            cleanup_browser(session_name="collector", source=source)
            return None
        print(f"❌ {result.get('message', '浏览器就绪失败')}", file=sys.stderr)
        sys.exit(1)

    try:
        print("   通过 OpenCLI 获取内容...")
        return subprocess.run(cmd, capture_output=True, timeout=60)
    finally:
        cleanup_browser(session_name="collector", source=source)
```

2. 删除或注释旧的 `run_browser_manager` 和 `ensure_browser_manager_initialized` 函数。为减少破坏性，可保留但标记为 deprecated，不再被 `run_opencli_cmd` 使用。

- [ ] **步骤 4：运行测试验证通过**

```bash
python3 -m pytest tests/test_main.py -v
```

预期：所有测试 PASS（包括原有非 browser 测试）

- [ ] **步骤 5：记录变更**

修改文件：
- `main.py`：OpenCLI 浏览器管理改由 adapter 负责
- `tests/test_main.py`：测试目标改为 adapter

---

## 任务 3：更新 SKILL.md

**文件：**
- 修改：`SKILL.md:48-56`（依赖检查部分）
- 修改：`SKILL.md:294-296`（OpenCLI 浏览器自动管理部分）

- [ ] **步骤 1：更新依赖检查说明**

把依赖检查表格中的 OpenCLI 可用性说明改为：

```markdown
| OpenCLI 可用性 | 检测 opencli 命令是否在 PATH 中；首次使用 OpenCLI 时自动初始化浏览器 profile | ❌ opencli 未安装，请按官方文档安装；若已安装但扩展未连接，按错误提示激活扩展 |
```

在表格后新增一段：

```markdown
浏览器生命周期优先由 `opencli-chrome-launcher` 技能管理。若该技能未安装，collector 会自动降级使用自带的 `scripts/browser_manager.py`。
```

- [ ] **步骤 2：更新 OpenCLI 浏览器自动管理章节**

把 `## OpenCLI 浏览器自动管理` 下的描述更新为：

```markdown
## OpenCLI 浏览器自动管理

collector 在调用 OpenCLI 之前，会通过 `scripts/chrome_launcher_adapter.py` 确保 Chrome 浏览器就绪：

1. 优先查找并使用 `opencli-chrome-launcher` 技能：
   - 调用 `use` 模式确保目标 profile 已连接
   - 若缺少 binding 配置，自动调用 `init` 模式完成初始化
   - 业务完成后调用 `cleanup` 模式释放 session 并清理残留标签
2. 若 `opencli-chrome-launcher` 未安装，则降级使用 collector 自带的 `scripts/browser_manager.py`
3. 用户无需手动启动 Chrome 远程调试端口
```

- [ ] **步骤 3：记录变更**

修改文件：
- `SKILL.md`：浏览器管理职责说明更新

---

## 任务 4：回归测试与收尾

- [ ] **步骤 1：运行完整测试套件**

```bash
cd ~/.agents/skills/collector
python3 -m pytest tests/ -q
```

预期：全部通过

- [ ] **步骤 2：手动验证 launcher 调用路径（可选，需有 OpenCLI 环境）**

```bash
python3 -c "from scripts.chrome_launcher_adapter import find_opencli_chrome_launcher_script; print(find_opencli_chrome_launcher_script())"
```

预期输出类似：

```
/Users/fubo/.agents/skills/opencli-chrome-launcher/scripts/opencli_chrome_launcher.py
```

- [ ] **步骤 3：更新 changelog**

在 `changelog/CHANGELOG.md` 顶部追加：

```markdown
## 2026-09-02
- collector 在调用 OpenCLI 前优先使用 opencli-chrome-launcher 管理 Chrome 生命周期；未安装时降级使用自带 browser_manager
- 新增 scripts/chrome_launcher_adapter.py 统一封装 launcher 查找、use/init/cleanup 调用与 fallback
```

- [ ] **步骤 4：记录变更**

新增/修改文件：
- `scripts/chrome_launcher_adapter.py`
- `main.py`
- `SKILL.md`
- `tests/test_chrome_launcher_adapter.py`
- `tests/test_main.py`
- `changelog/CHANGELOG.md`

---

## 自检

**规格覆盖度：**
- 用户要求"一旦遇到浏览器没有打开，连接不正常的状态，要先调用 opencli-chrome-launcher" → 任务 1/2 的 adapter 在 `ensure_browser_ready` 中优先查找并调用 launcher
- 用户要求"launcher 不存在时也能工作" → 任务 1 的 fallback 到内部 browser_manager
- 用户要求" collector 本身要改动最小" → 任务 2 只改动 `run_opencli_cmd`，其余业务逻辑不变

**占位符扫描：** 所有步骤包含实际代码、命令、预期输出，无"待定"或"后续实现"。

**类型一致性：** `ensure_browser_ready` 返回 `(bool, dict, str)`，与 `cleanup_browser(source=...)` 中的 `source` 字符串保持一致；adapter 内部统一使用 `"opencli-chrome-launcher"` / `"internal-browser-manager"`。

---

## 执行交接

计划已完成并保存到 `~/.agents/skills/collector/docs/superpowers/plans/2026-09-02-collector-delegate-to-opencli-chrome-launcher.md`。

**两种执行方式：**

1. **子代理驱动（推荐）** — 每个任务调度一个新子代理
2. **内联执行** — 在当前会话中按任务顺序实现

选哪种方式？
