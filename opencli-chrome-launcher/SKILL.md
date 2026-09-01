---
name: opencli-chrome-launcher
description: |
  当用户需要确保 Chrome 浏览器已准备好供 OpenCLI 使用，或提到 "打开 Chrome 给 OpenCLI"、"清理 OpenCLI Browser 标签"、"检查 OpenCLI 浏览器状态" 时触发。
  本技能负责 OpenCLI 浏览器环境的全生命周期：check（只读诊断）、init（初始化绑定）、use（使用前确保浏览器就绪）、cleanup（清理残留标签）。
  不执行任何 OpenCLI 业务采集，只提供"浏览器已就绪"的运行时环境。
version: "v1.2.0"
---

# opencli-chrome-launcher v1.2.0

本技能让 Agent 在使用 OpenCLI 之前，自动完成 Chrome 启动、账号切换、扩展连接检查以及残留标签清理。

## 触发场景

- 用户说："打开 Chrome 给 OpenCLI 用"
- 用户说："清理 OpenCLI Browser 标签"
- 用户说："检查 OpenCLI 浏览器状态"
- 其他需要 OpenCLI 的技能在内部调用本技能

## 核心原则

1. **只管理浏览器生命周期**：不执行 OpenCLI 站点适配器、不采集数据。
2. **强制重启切换 profile**：Chrome 在错误账号时，会关闭当前所有 Chrome 窗口并重启到目标 profile。
3. **清理不阻塞业务**：cleanup 失败只返回 warning，不卡死主流程。
4. **谁调用谁负责**：调用方技能负责在业务完成后调用 cleanup。

## 模式

### check 模式

```bash
python scripts/opencli_chrome_launcher.py check
```

只读诊断，返回当前 opencli、Chrome、profile、窗口状态，不改动任何配置。

### init 模式

```bash
python scripts/opencli_chrome_launcher.py init
```

首次初始化：
1. 检查 opencli 是否安装
2. 检查 `opencli doctor` 是否通过
3. 检查 Chrome 是否安装
4. 读取 Chrome `Local State` 获取本地 profile 列表
5. 获取 `opencli profile list` 的 OpenCLI profile 列表
6. 按规则自动匹配并选择目标 profile
7. 写入 `config/binding.json`
8. 再次 `opencli doctor` 确认

### use 模式

```bash
python scripts/opencli_chrome_launcher.py use [session_name]
```

每次使用前的浏览器就绪流程：
1. 读取 `config/binding.json`
2. 获取文件锁，防止并发操作 Chrome
3. 前置 cleanup：关闭历史残留的 "OpenCLI Browser" 标签
4. `ensure_browser_with_profile()` 确保 Chrome 在目标 profile 且扩展已连接
5. 返回就绪状态

### cleanup 模式

```bash
python scripts/opencli_chrome_launcher.py cleanup [session_name]
```

业务完成后清理：
1. `opencli browser <session> close` 释放 session lease
2. 两阶段 aggressive cleanup：
   - 关闭所有标题含 "OpenCLI Browser" 的标签
   - 关闭只剩 `about:blank` / `chrome://newtab` 的空窗口

## 输出格式

所有模式返回统一 JSON：

```json
{
  "status": "success|partial|failed|needs_user_input",
  "module": "opencli-chrome-launcher",
  "message": "给用户看的摘要",
  "data": {},
  "errors": [{"code": "...", "message": "..."}]
}
```

## 错误码

| 错误码 | 含义 | 处理 |
|---|---|---|
| `OPENCLI_NOT_FOUND` | opencli 未安装 | failed，提示安装 |
| `OPENCLI_DOCTOR_FAILED` | OpenCLI 浏览器桥接失败 | failed，提示激活扩展 |
| `CHROME_NOT_FOUND` | 未检测到 Chrome | failed |
| `NO_BINDING_CONFIG` | 缺少 binding.json | failed，提示先 init |
| `BROWSER_PROFILE_MISSING` | 配置中缺少 OpenCLI profile ID | failed |
| `BROWSER_PROFILE_NEEDED` | 多个 profile 需用户选择 | needs_user_input |
| `CHROME_PROFILE_MISMATCH` | 切换后仍不匹配 | failed |
| `CHROME_LAUNCH_FAILED` | 无法启动 Chrome | failed |
| `CHROME_LAUNCH_TIMEOUT` | Chrome 启动后未检测到进程 | failed |
| `CHROME_QUIT_FAILED` | 无法退出当前 Chrome | failed |
| `CHROME_EXIT_TIMEOUT` | 等待 Chrome 退出超时 | failed |
| `PROFILE_SWITCH_FAILED` | 切换 OpenCLI profile 失败 | failed |
| `EXTENSION_NOT_INSTALLED` | 扩展未安装/未激活 | failed |
| `BROWSER_LOCKED` | 另一个任务正在管理 Chrome | failed |
| `CLEANUP_WARNING` | 清理失败 | warning，不阻塞 |
| `CLEANUP_EXCEPTION` | 清理过程异常 | warning，不阻塞 |
| `UNKNOWN_MODE` | 不支持的 mode | failed |

## 配置

`config/binding.json` 由 init 生成：

```json
{
  "initialized": true,
  "browser_profile": {
    "chrome_profile_id": "Profile 1",
    "chrome_profile_name": "Mira",
    "opencli_profile_id": "g3a5ehu6"
  },
  "browser": {
    "auto_open_browser": true,
    "auto_close_browser": true,
    "connection_retry_interval": 2,
    "connection_retry_max": 15,
    "session_name": "opencli-chrome-launcher"
  },
  "initialized_at": "2026-09-01T12:00:00+08:00"
}
```

## 边界声明

- Chrome 专用给 Agent 使用；profile 不匹配时会强制退出并重启 Chrome，关闭当前所有 Chrome 窗口。
- 不直接调用任何站点适配器。
- macOS 优先，Linux/Windows 保留基础支持。
- cleanup 失败不阻塞业务结果。
