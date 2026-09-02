# collector 更新日志

> 维护规范：每一次功能升级和优化，都必须在此记录**日期、版本号、更新内容**，逐条追加，不覆盖历史。

## 2026-09-02 — v1.6.0
- 新增：`scripts/chrome_launcher_adapter.py` OpenCLI 浏览器生命周期适配器，优先调用 `opencli-chrome-launcher` 管理 Chrome；未安装时自动降级到 `scripts/browser_manager.py`
- 优化：`main.py` 的 `run_opencli_cmd()` 改由 `chrome_launcher_adapter` 准备浏览器，launcher 不可用时走内部 fallback 并保留 `allow_fallback` 行为
- 优化：X/Twitter 等 OpenCLI 采集前，先尝试 `opencli-chrome-launcher use`；若返回 `NO_BINDING_CONFIG` 则自动 `init` 后再 `use`，无需用户手动启动 Chrome
- 更新：`tests/test_chrome_launcher_adapter.py` 新增 adapter 路径查找、launcher 调用、fallback 与 cleanup 测试（9 个）
- 更新：`tests/test_main.py` 浏览器管理相关测试改为 mock `main.ensure_browser_ready` / `main.cleanup_browser`，与直接导入绑定保持一致
- 文档：`SKILL.md` 更新依赖检查、X/Twitter 说明与 OpenCLI 浏览器自动管理章节，文件结构增加 `chrome_launcher_adapter.py`，版本更新为 v1.6.0

## 2026-08-20 — v1.5.0
- 新增：`scripts/browser_manager.py` OpenCLI 浏览器生命周期管理器，统一处理 Chrome 启动、profile 切换、扩展连接、并发锁、残留窗口清理
- 新增：`scripts/config_manager.py` 与 `config/config.json`，保存 `browser_profile` / `browser` / `env_check` 配置
- 优化：X/Twitter 采集前自动调用 `browser_manager init` / `use` / `cleanup`，用户无需手动启动 Chrome 远程调试端口
- 优化：`main.py` 新增 `run_opencli_cmd()` 统一入口，所有 OpenCLI 命令先走浏览器就绪检查，失败时按 `allow_fallback` 决定是否降级
- 优化：移除 `main.py` 中已废弃的 `check_opencli_available()`，改由 `browser_manager.py` 解析 `opencli doctor` 输出
- 新增：cleanup 智能退出 Chrome——仅当 Chrome 由本技能启动且只剩残留窗口时才调用 `quit_chrome()`，避免误关用户正常窗口
- 优化：强化 `cleanup_leaked_windows()`，不仅关闭全空白窗口，还会主动关闭所有标题为 "OpenCLI Browser" 的标签，解决标签分组堆积问题
- 优化：在 `browser_manager use` 前增加前置清理，运行 OpenCLI 命令前先清理已有的 OpenCLI Browser 残留标签
- 优化：SKILL.md description 正面清晰化边界，强调「单条 URL/文件路径 → 原样保存到本地」，避免与选题资料调研类技能混淆

## 2026-08-15 — v1.4.0
- 优化：X/Twitter OpenCLI 调用默认附加 `--window background --keep-tab false`，减少浏览器窗口弹出与标签组堆积
- 优化：在 SKILL.md 中增加 OpenCLI Browser 窗口管理与内存占用说明
- 修复：`check_env.py` 与 `install.sh` 中 wexin-reader MCP 路径修正为 `wexin-read-mcp/server.py`（移除错误的 `src/`）
- 修复：`scripts/fetch_url.sh` 中 `archive.today` 命中 CAPTCHA 后直接 `exit 75` 导致 Google Cache / agent-fetch  fallback 无法执行的问题，改为继续后续降级
- 完善：`main.py` 的 `get_output_dir()` 在首次运行时自动提示确认输出目录（交互环境）或使用默认值并写入 `output_dir.config`（非交互环境）
- 修复：补全 `requirements.txt`，新增 `ebooklib`（EPUB 提取）和 `pyyaml`（微信 MCP scraper 解析）
- **修复：X/Twitter 单条推文 URL（`/status/`）被错误识别为用户主页，导致重复采集同一用户最新推文。新增 `x_twitter_status` 类型，调用 `opencli twitter thread <tweet-id>` 精确采集单条推文**
- 部署：技能物理目录迁移到 `~/.agents/skills/collector/`，并通过软链接 `~/.claude/skills/collector` 让 Claude Code 继续识别

## 2026-08-01 — v1.3.1
- 修订：输出目录确认改为仅在首次初始化时确认一次（新增 N2a 判断 output_dir.config 是否已存在），后续运行直接读取配置，不再向用户确认

## 2026-08-01 — v1.3.0
- 新增：输出目录初始化时向用户确认（N2b），确认后写入 output_dir.config（N2c）
- 强化：触发反馈为强制性第一动作，先于一切环境检查
- 新增：changelog/ 版本管理机制（本文件）
- 修复：test_main.py 断言跟上 X/Twitter 三子类型（pytest 10/10）
- 修复：播客凭据 tokens.json 路径解耦（GETNOTE_TOKENS_FILE > config/tokens.json > 旧路径兼容）
- 补齐：proxy.config 模板、LICENSE（MIT）
- SOP：微信采集补显式异常边（T2 → 统一报错退出）

## 2026-07-19 — v1.2.1
- OpenCLI 硬依赖（不降级）、触发确认加入内容源类型、文件名冲突追加序号、通用依赖前置全检、按需检查播客API和海外代理、X/Twitter 失败时显示诊断引导
