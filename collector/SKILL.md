---
name: collector
description: |
  当用户给出**具体的 URL 链接或本地文件路径**，并表达「保存到本地 / 下载 / 存下来 / 归档 / 备份 / 采集 / 抓下来 / 收起来 / 存库」等意图时，使用本技能。

  本技能执行的是**单条内容抓取**：把指定的网页、推文、视频页、播客、PDF、EPUB、Office 文档、图片、音频或压缩包原样转换为 Markdown 文件，保存到 `$COLLECTOR_DIR` 目录。

  典型输入形式：
  - 一个网页链接：`https://www.ft.com/content/abc123`
  - 一条推文链接：`https://x.com/username/status/123456`
  - 一个本地文件路径：`~/Downloads/report.pdf`

  典型触发语句：「采集这条推文 https://...」「把这个 PDF 存到库里」「下载这个视频」「归档这篇文章」「收一下这个网页」。

  关键判定：用户意图是**把单条内容原样保存到本地文件**，而不是搜索多源信息、整理调研资料、生成报告或改写原文。

  本技能核心原则：100% 全文采集、原文原样保存、不加工不摘要。
---

# 采集器 — 多源内容采集

自动从多种来源获取内容，**原样保存**（不做任何摘要、分析或格式转换）到 `$COLLECTOR_DIR` 指定目录。

> **核心原则：原文保存 + 全文采集** — 采集器只做采集与保存，不加工、不重写、不分析、不截断。输出为 Markdown 格式，元数据以内嵌列表记录，正文必须保留原始内容完整原文，不得省略、摘要或选择性保存。

## 触发反馈（N1 — 强制性第一动作）

技能被触发时，**立即**向用户显示采集类型确认消息。**这是强制性第一动作，先于一切初始化与环境检查，不可跳过**——确保用户第一时间知道采集器正在发挥作用。

消息格式：
```
✅ 采集器已触发，正在处理【{内容源类型}】...
```
内容源类型包括：网页、微信公众号文章、播客转写、X/Twitter文章、推文搜索、YouTube视频、EPUB电子书、PDF文档、Office文档、图片OCR、音频元数据、ZIP压缩包。

> 此处的内容源类型为触发瞬间的**预判**；权威识别在 Step 1（N4）完成。

## 初始化（N2）

采集任务执行前，按以下逻辑执行：

1. **读取配置** — 输出目录优先级：环境变量 `COLLECTOR_DIR` > `output_dir.config` > 默认 `~/CollectorOutput`；代理配置读取 `proxy.config`（默认 `http://127.0.0.1:6696`），用于海外网站采集
2. **判断是否已初始化（N2a）** — 若 `output_dir.config` 已存在（或 `COLLECTOR_DIR` 环境变量已设置）：**直接使用该目录，不再向用户确认**，进入依赖检查
3. **首次初始化确认（N2b，仅一次）** — 仅当 `output_dir.config` 不存在（技能安装后的首次运行）时：向用户展示生效的输出目录，请用户确认或修改
4. **记录到技能（N2c）** — 将确认的输出目录写入 `output_dir.config`。**确认只发生这一次，后续所有运行直接读取配置，不再询问**

## 依赖检查（N3 — 通用依赖前置全检）

**以下依赖在任何采集任务执行前必须全部通过检查，任一缺失则报错退出，不执行任何采集任务：**

| 检查项 | 检查内容 | 失败处理 |
|--------|---------|---------|
| COLLECTOR_DIR 可写性 | 目录存在且可写入 | ❌ COLLECTOR_DIR 不可写，请检查权限 |
| OpenCLI 可用性 | 检测 opencli 命令是否在 PATH 中；首次使用 OpenCLI 时由 `opencli-chrome-launcher` 自动初始化浏览器 profile | ❌ opencli 未安装，请按官方文档安装；若已安装但扩展未连接，按错误提示激活扩展 |
| wexin-reader MCP | 实际调用一次 read_weixin_article 验证 MCP 可用 | ❌ 微信公众号MCP不可用，请检查配置并重启 OpenClaw |

浏览器生命周期优先由 `opencli-chrome-launcher` 技能管理。若该技能未安装，collector 会自动降级使用自带的 `scripts/browser_manager.py`。

**检查通过后显示**：`✅ 采集器环境检查通过，已就绪`

## 按需依赖检查（N6）

以下依赖在实际用到时才检查，不阻塞其他类型的采集：

| 内容类型 | 检查项 | 失败处理 |
|---------|--------|---------|
| **播客** | `GETNOTE_API_KEY` + `GETNOTE_CLIENT_ID` 环境变量 | ❌ Get笔记API凭据未配置，请设置环境变量 |
| **海外网站**（非 `.cn` 域名） | 海外代理端口 `127.0.0.1:6696` 可连通性 | ❌ 海外代理端口不可用，采集海外网站会失败 |
| 其他类型 | 无额外依赖 | 直接通过 |

## 支持的内容源

### 1. 网页链接（含付费墙绕过）
任意公开网页。自动检测并绕过 NYT、WSJ、FT、Economist、Bloomberg、Medium 等 **300+ 付费网站**。绕过策略：r.jina.ai → Googlebot UA → Referer 伪装 → AMP → archive.today → Google Cache → agent-fetch（兜底）。

### 2. 微信公众号文章
通过 MCP 服务器（wexin-reader）自动抓取文章内容。

### 3. 播客 / 音频平台
小宇宙、喜马拉雅、B站 — 通过 Get笔记 API 获取完整转写文本。

### 4. X/Twitter 帖子 / 文章
**通过 OpenCLI 自动采集**（用真实 Chrome 登录态读取，突破反爬）。
> 采集器会在调用 OpenCLI 前自动完成浏览器生命周期管理：优先调用 `opencli-chrome-launcher` 确保 Chrome 就绪；launcher 未安装时降级使用 `scripts/browser_manager.py`。采集完成后释放 session 并清理残留窗口。用户无需手动启动 Chrome 远程调试端口。
>
> 若 OpenCLI 扩展未安装或未连接，会返回明确错误码并提示激活扩展。X/Twitter 有强反爬机制，暂不支持 WebSearch/WebFetch 降级。

### 5. YouTube 视频
保存视频链接引用（字幕提取需额外工具）。**降级输出**：完成反馈中必须提示用户字幕未采集。

### 6. 本地文件
- **EPUB** — ebooklib 提取全文
- **PDF / TXT / MD** — markitdown 转换
- **Word / PPT / Excel** — markitdown 转换
- **图片** (JPEG/PNG) — OCR
- **音频** (MP3/WAV) — markitdown 提取元数据/文本（**降级输出**：不支持语音转文字，需额外配置 Whisper 等工具，需向用户明示）
- **ZIP** — 解压并列出内容

### 7. 搜索关键词
> ⚠️ **暂不支持** — 搜索关键词不属于采集器职责，请通过 WebSearch 获取结果后保存到文件再采集。

## 工作流程

### Step 1: 识别内容源类型（N4 — 权威识别）

自动判断输入，无需手动指定。

| 特征 | 类型 |
|------|------|
| `mp.weixin.qq.com` | 微信公众号 |
| `youtube.com` / `youtu.be` | YouTube |
| `xiaoyuzhoufm.com` / `ximalaya.com` / `bilibili.com` | 播客 |
| `x.com` / `twitter.com` 含 `/i/article/` | X/Twitter 文章 |
| `x.com` / `twitter.com` 含 `/status/` | X/Twitter 单条推文 |
| `x.com` / `twitter.com` 含 `/search?q=` | X/Twitter 搜索 |
| `x.com` / `twitter.com` 其他路径 | X/Twitter 用户推文 |
| 其他 `https://` | 网页（含付费墙） |
| `.epub` | EPUB 电子书 |
| `.pdf` / `.txt` / `.md` | 文档 |
| `.docx` / `.pptx` / `.xlsx` | Office 文档 |
| `.jpg` / `.png` 等 | 图片（OCR） |
| `.mp3` / `.wav` | 音频 |
| `.zip` | ZIP 压缩包 |
| 纯文本关键词 | 不支持（搜索功能） |

### Step 2: 获取内容

根据类型调用对应工具：

| 内容源 | 工具/命令 |
|--------|---------|
| X/Twitter 单条推文 | `opencli twitter thread "<tweet-id>" --window background --keep-tab false` |
| X/Twitter 文章 | `opencli twitter article "<URL>" --window background --keep-tab false` |
| X/Twitter 用户推文 | `opencli twitter tweets "<用户名>" --window background --keep-tab false` |
| X/Twitter 搜索 | `opencli twitter search "<关键词>" --window background --keep-tab false` |
| 网页/付费墙 | `bash scripts/fetch_url.sh <URL>` |
| 播客 | `python3 scripts/get_podcast_transcript.py <URL>` |
| 微信公众号 | MCP 工具 `read_weixin_article` |
| EPUB | `python3 main.py <文件路径>` |
| 其他本地文件 | `python3 main.py <文件路径>` |

### Step 3: 保存到目标目录

通过 `main.py` 保存到 `$COLLECTOR_DIR`，目录结构：
```
$COLLECTOR_DIR/
├── webpage/     ← 普通网页
├── weixin/      ← 微信公众号
├── youtube/     ← YouTube 引用
├── podcast/     ← 播客转写
├── x_twitter/   ← X/Twitter（推文/文章）
├── epub/        ← EPUB 电子书
├── document/    ← PDF/TXT/MD
├── office/      ← Word/PPT/Excel
├── image/       ← 图片 OCR
├── audio/       ← 音频
├── zip/         ← 压缩包
└── search/      ← 搜索结果（暂不支持）
```

每个文件格式（Markdown）：
```markdown
# <原标题>

- **来源**: <原始 URL 或文件路径>
- **来源类型**: <webpage/weixin/x_twitter/...>
- **采集时间**: 2026-05-15 12:00:00

---

<采集的内容全文 — 原样保存，不作任何改动>
```

**文件名冲突处理**：重名时追加序号 `_1`, `_2`...（而非覆盖）。

## 完整示例

### 示例 1：X/Twitter 文章（必须用 OpenCLI）
**用户**：`采集这篇推文 https://x.com/username/status/123456789`

自动执行：
```
1. opencli twitter article "https://x.com/username/status/123456789"
   → 用真实 Chrome 登录态获取文章全文
2. 保存到 $COLLECTOR_DIR/x_twitter/<标题>.md
```

**X/Twitter 其他命令参考**：
```bash
# 获取用户最近推文
opencli twitter tweets "<用户名>" --limit 10

# 搜索推文
opencli twitter search "<关键词>"

# 查看当前登录账号
opencli twitter whoami

# 检查连接状态
opencli doctor
```

### 示例 2：网页付费文章
**用户**：`采集这篇 FT 文章 https://www.ft.com/content/abc123`

自动执行：
```
1. bash scripts/fetch_url.sh "https://www.ft.com/content/abc123"
   → Googlebot UA 绕过付费墙，获取全文
2. python3 main.py "https://www.ft.com/content/abc123"
   → 保存到 $COLLECTOR_DIR/webpage/
```

### 示例 3：EPUB 电子书
**用户**：`采集这本电子书 /Users/me/Books/sapiens.epub`

自动执行：
```
1. python3 main.py /Users/me/Books/sapiens.epub
   → ebooklib 提取全文（~15 万字）
2. 保存到 $COLLECTOR_DIR/epub/sapiens.md
```

## 错误处理

### X/Twitter 采集失败

```
❌ OpenCLI 采集失败
可能原因：
1. OpenCLI 扩展未安装或未激活 → 打开 Chrome 点击 OpenCLI 扩展图标
2. Chrome 中 Twitter/X 未登录 → 确认登录状态
3. 文章不存在或权限不足 → 检查 URL 是否正确
4. 多个 Agent 同时操作 Chrome → 稍后再试
```

若浏览器就绪失败（如扩展未连接、profile 切换失败），X/Twitter 路径会**直接报错退出**，因为不存在可行的公开降级方案。

### 微信公众号采集失败
```
❌ 微信文章抓取失败
可能原因：
1. wexin-reader MCP 未配置或未启动 → 检查 OpenClaw config.json 并重启
2. url-md 未安装 → 见 wexin-read-mcp 说明安装
3. 文章链接失效或需验证 → 检查 URL 是否可正常访问
```

### 付费墙绕过失败
级联策略全部失败后，`main.py` 自动使用 curl 直接抓取兜底；兜底仍失败则报错退出：
```
❌ 获取网页失败
可尝试：打开 https://archive.today/newest/<URL> 手动验证后重试
```

### 播客转写失败
```
❌ 获取转写失败
可能原因：API Key 未配置 / 平台限制 / 网络问题
```

## 环境变量

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `COLLECTOR_DIR` | 采集内容输出目录（建议指向 Obsidian vault） | `~/CollectorOutput` |
| `GETNOTE_API_KEY` | 播客转写 API Key（播客采集必须） | 无 |
| `GETNOTE_CLIENT_ID` | 播客转写 Client ID（播客采集必须） | 无 |
| `GETNOTE_TOKENS_FILE` | 播客凭据 tokens.json 路径（可选，默认 `config/tokens.json`） | 无 |

## 代理配置

只对采集器的网页抓取生效，不影响系统和 AI 平台。

- **海外网站**（非 `.cn` 域名）：使用 `http://127.0.0.1:6696`
- **国内网站**：直连（无需代理）

编辑 `<技能目录>/proxy.config`：
```
http://127.0.0.1:6696
```

> **注意**：X/Twitter 走 OpenCLI（Chrome 真实会话），不受代理配置影响。

## 注意事项

1. **全文采集**：所有文章/推文/网页必须保存完整原文，不得截断、摘要或选择性保存内容
2. **付费墙绕过仅用于个人学习研究**
3. **微信公众号需先配置 MCP 服务器**（OpenClaw config.json）
4. **COLLECTOR_DIR 可设为 Obsidian vault 路径**，采集内容直接进 Obsidian
5. 文件默认保存为 `.md`（Markdown）格式
6. **原文保存**：采集器不做任何内容加工、摘要、分析或格式转换，保留原始内容原貌
7. **X/Twitter 通过 OpenCLI 自动采集**：采集器会自动准备 Chrome 浏览器环境（启动、切换 profile、等待扩展连接），用户无需手动启动 Chrome 远程调试端口
8. **Chrome 专用给 Agent 使用**：profile 不匹配时，采集器会强制退出并重启 Chrome，关闭当前所有 Chrome 窗口
9. **降级输出必须明示**：YouTube 仅链接引用、音频仅元数据，完成反馈中必须告知用户

## OpenCLI 浏览器自动管理

collector 在调用 OpenCLI 之前，会通过 `scripts/chrome_launcher_adapter.py` 确保 Chrome 浏览器就绪：

1. 优先查找并使用 `opencli-chrome-launcher` 技能：
   - 调用 `use` 模式确保目标 profile 已连接
   - 若缺少 binding 配置，自动调用 `init` 模式完成初始化
   - 业务完成后调用 `cleanup` 模式释放 session 并清理残留标签
2. 若 `opencli-chrome-launcher` 未安装，则降级使用 collector 自带的 `scripts/browser_manager.py`
3. 用户无需手动启动 Chrome 远程调试端口

### 内部 fallback（browser_manager.py）

当 `opencli-chrome-launcher` 未安装时，adapter 会调用 `scripts/browser_manager.py`。

#### 首次使用（自动初始化）

首次调用任何 OpenCLI 平台（当前为 X/Twitter）时，`browser_manager.py init` 会自动：

1. 检测 `opencli` 是否安装
2. 检测 Chrome 是否安装
3. 读取 Chrome 本地 profile 列表
4. 获取 OpenCLI profile 列表
5. 自动匹配并选择目标 profile（单 profile 直接选；多 profile 按名称/email 含 `openclaw`/`opencli`、default 标记、第一个的顺序推断）
6. 保存绑定关系到 `config/config.json`
7. 再次 `opencli doctor` 确认扩展已连接

绑定后的配置保存在：

```json
{
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
    "session_name": "collector"
  }
}
```

#### 每次使用（自动就绪）

每次执行 OpenCLI 命令前，`browser_manager.py use` 会：

1. 获取文件锁 `workspace/.browser_manager.lock`，防止多 Agent 并发操作 Chrome
2. 检查当前已连接的 OpenCLI profile
3. 若目标 profile 已连接 → 直接成功
4. 若 Chrome 未运行 → 用目标 profile 启动
5. 若 Chrome 在运行但目标未连接 → 强制退出 Chrome → 用目标 profile 重启 → 等待扩展连接
6. 返回就绪状态

#### 清理（自动释放）

每次 OpenCLI 命令执行前后，`browser_manager.py` 都会清理 OpenCLI 残留：

1. **前置清理**（`use` 阶段）：运行 OpenCLI 命令前，先关闭所有标题为 "OpenCLI Browser" 的标签，避免新命令创建更多分组
2. 执行 `opencli browser collector close` 释放 session lease
3. 再次关闭所有标题为 "OpenCLI Browser" 的标签
4. 关闭只剩 `about:blank` / `chrome://newtab` 的空窗口
5. **智能退出 Chrome**：
   - 如果 Chrome **由本技能启动**，且清理后只剩残留窗口 → 自动调用 `quit_chrome()` 完全退出 Chrome 进程
   - 如果存在用户正常窗口，或 Chrome 不是本技能启动的 → **保留 Chrome 进程**

> 注意：OpenCLI 扩展本身会创建 "OpenCLI Browser" 标签分组，目前官方没有 `--no-tab-group` 参数可以完全禁止。本技能通过前置 + 后置双重清理，在每次采集前后主动关闭这些标签，避免分组堆积。
### 手动调整 profile

如需更换 profile，直接编辑 `config/config.json` 中的 `browser_profile` 节点，或删除该文件让下次触发时重新初始化。

### 减少浏览器窗口与内存占用

采集器调用 OpenCLI 时，默认附加 `--window background --keep-tab false`：
- `--window background`：不在前台弹出新的 Chrome 窗口
- `--keep-tab false`：命令结束后立即释放 OpenCLI Browser 标签页，避免标签组堆积

如果希望所有 OpenCLI 命令都默认后台运行，可在 shell 配置中加入：
```bash
export OPENCLI_WINDOW=background
```

> 注意：OpenCLI Browser 标签组由 Browser Bridge 扩展创建；多个同名分组残留是已知现象，cleanup 步骤会自动清理。

## 测试

- Python 单元测试：`python3 -m pytest tests/test_main.py -q`
- fetch_url.sh 辅助函数测试（需安装 bats，`brew install bats-core`）：`bats tests/test_fetch_url.sh`

## 维护规范（版本管理）

**每一次功能升级和优化，都必须在 `changelog/CHANGELOG.md` 中记录：日期、版本号、更新内容。** 逐条追加，不覆盖历史记录。修改本技能时同步更新下方版本信息。

## 文件结构

```
collector/
├── SKILL.md                ← 技能定义（本文件）
├── main.py                 ← CLI 入口：采集 + 保存
├── config/
│   └── config.json         ← 浏览器 profile 与 OpenCLI 配置（运行时生成）
├── scripts/
│   ├── chrome_launcher_adapter.py  ← OpenCLI 浏览器生命周期适配器（优先 opencli-chrome-launcher，fallback browser_manager）
│   ├── browser_manager.py  ← 内部 OpenCLI 浏览器生命周期管理（fallback）
│   ├── config_manager.py   ← 配置读写
│   ├── fetch_url.sh        ← 网页抓取 + 付费墙绕过
│   └── get_podcast_transcript.py  ← 播客转写
├── wexin-read-mcp/         ← 微信公众号 MCP 服务器（依赖 url-md）
├── tests/                  ← pytest + bats 测试
├── changelog/
│   └── CHANGELOG.md        ← 更新日志（每次升级必须记录）
├── install.sh              ← 安装脚本
├── check_env.py            ← 环境检查
├── requirements.txt        ← Python 依赖
├── requirements-dev.txt    ← 开发/测试依赖
├── proxy.config            ← 海外代理配置
├── output_dir.config       ← 用户确认后的输出目录（初始化时写入，可选）
└── LICENSE                 ← MIT
```

**版本**：v1.6.0
**最后更新**：2026-09-02
**更新内容**：新增 OpenCLI 浏览器自动管理（browser_manager.py），X/Twitter 采集无需手动启动 Chrome；自动处理 profile 切换、扩展连接、并发锁与残留窗口清理；新增 config/config.json 保存浏览器配置。详见 changelog/CHANGELOG.md。
