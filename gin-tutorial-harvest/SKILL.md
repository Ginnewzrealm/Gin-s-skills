---
name: gin-tutorial-harvest
description: |
  输入主题 + source-scan 的 sources.json（或直接给 URL 清单），按通道优先级把教程文章/教材采集为本地 Markdown 资料库，
  输出 coverage-manifest.json 验收报告，可直接流转给下游原子技能（选题裁决/找答案）。
  当用户说"把这些资料采下来"、"采集这些教程"、"扒这些页面"、"建 XX 主题资料库"时触发。
  也适用于上游编排器（写教程技能组）的 Stage 0 采集层。
  不适用于：发现资料源（走 gin-tutorial-source-scan）、单条网页收藏（走 collector）、找用户真问题（走 gin-question）。
---

# gin-tutorial-harvest：教程资料采集层

输入主题 + sources.json → 输出本地 Markdown 资料库（按层分目录）+ coverage-manifest.json。
核心原则：**每条 URL 的通道由脚本调度、每条内容由脚本验收、每次失败按降级阶梯处理——判断全部可追溯。**

## 何时使用 / 不适用

- 已有 sources.json（或用户直接给 URL 清单）要落盘成资料库 → 本技能
- 只有一个主题词还没找源 → 先 gin-tutorial-source-scan
- 单条链接随手存 → collector；发现层输出前的人工圈定 → 不是本技能的事（本技能自动采全部收录源）

## 输入 / 输出 / 验收（契约）

| 项 | 内容 |
|---|---|
| 输入 topic | 必填，主题词（写入 manifest） |
| 输入 output_dir | 必填，资料库落盘路径 |
| 输入 sources.json | 必填，source-scan 的产出；直接给 URL 清单时先转成同 schema |
| 输入 target_draft_words | 选填，默认 8000（验收达标线 = 3×） |
| 输出 ① | `<output_dir>/L1/…L6/` 下的 Markdown 正文（后处理过） |
| 输出 ② | `<output_dir>/coverage-manifest.json`：逐条 url/层/字数/通道/重试/覆盖问题 + 验收结论 + 观察哨清单 |
| 验收 A | 素材总字数 ≥ 3 × target_draft_words，不达标 → 自动回到 source-scan 补搜再采一轮，报告里写明 |
| 验收 B | 每个 TOP 高频问题 ≥2 份独立来源（coverage 从 source-scan 带入，缺口如实报不硬凑） |
| 验收 C | 每条正文 ≥500 内容单位（中文字+英文词），不足判失败走降级阶梯 |

## 工作流程

```
1. 前置准备   读 sources.json；确定 output_dir / target_draft_words(默认8000)；逐条跑 channel 定通道
2. 逐条采集   按通道执行采集命令（见下）
3. 逐条验收   validate 字数；不合格 → 同通道重试 1 次 → 仍败走降级阶梯 → 仍败记 failed
4. 失败替补   failed 源用 sources.json 同 action 类型的其他源替补，替补关系记入 manifest
5. 后处理     postprocess 剥站内锚点链接噪音（--site-host 用 URL 的域名）
6. 落盘       按 layer 存 <output_dir>/<L?>/<安全文件名>.md（文件名禁 \ / : * ? " < > | 和标点空格）
7. 收口报告   manifest 汇总；验收不达标 → 回 source-scan 补搜（可继续采集，无人工闸门）
8. 输出      向用户报告：成功 N / 失败 N（含原因与替补）/ 观察哨（unknown 级源清单）/ 验收结论
```

## 通道调度（每条 URL 必跑脚本，禁止凭 URL 肉眼猜通道）

```bash
python3 scripts/harvest.py channel --url "..." --action "单页采集" [--no-firecrawl-key]
```

| 返回通道 | 执行方式 |
|---|---|
| firecrawl-scrape | `npx -y firecrawl-cli scrape <url> --only-main-content -o <file>` — **必须带 --only-main-content**，否则抓到导航栏噪音（占文件 3/4 体积） |
| firecrawl-download | 整站扒取：`firecrawl download <url> <dir>`（需 API key；无 key 时脚本会自动降级为 scrape 并提示） |
| opencli | opencli-browser 真实浏览器通道（知乎/B站专栏/登录墙） |
| collector | collector 技能（PDF/公众号/视频页） |
| skip-book | 不采集（豆瓣/当当是找书线索，书目记入 note 即可） |

调度优先级：**域名黑名单 > action 标注 > 扩展名 > 默认**。知乎即使 action 标错也走 opencli。

## 降级阶梯（失败处理，红阶段实测教训）

```
采集失败（validate 不通过 / CLI 报错 / 空正文）
  → 同通道重试 1 次
  → 仍败：换下一通道
       firecrawl 撞 502/503 → opencli 本机浏览器
         ⚠️ 502/503 多半是源站封采集代理的出口 IP（9/5 实测：健身吧 firecrawl 两次 502，
            本机 curl 直连 200）——本机浏览器常能通，不许直接放弃
       firecrawl 撞验证码 → opencli
  → 三通道皆败才记 failed，同层同 action 替补
```

- **404 ≠ 重试能救**：先 `curl -sI <url>` 直连确认 + WebSearch 查证源是否下线；确认源失效 → 直接判 failed 走替补，不浪费重试
- 替补必须在 manifest 里记录：`"替补自": "<原 url>"`——审计链：拒绝/失败/替补都是判断，要可追溯

## 后处理规则

```bash
python3 scripts/harvest.py postprocess --file <path> --site-host <URL 域名>
```

- 空锚点 `[](url "直接链接")`（Docusaurus 标题挂件）→ 整段移除
- 站内链接 `[text](同站 url)` → 剥 URL **保留显示文本**（阅读流不断）
- 外部引用链接 → **原样保留**（下游找答案/溯源要顺着引用链走）
- 无 site-host 时只剥空锚点，不乱删

## 语言政策

教材级源（官方/学术/经典）**不限语言**——英文 WHO/arXiv 源同样有效素材。验收字数口径 =
中文字数 + 英文词数（脚本已内置，禁止按纯中文字数误杀英文权威源）。

## 观察哨

source-scan 定级为 `unknown` 的源**照常采集**（高价值 UGC 常在 unknown 里），但在 manifest
的 `观察哨` 字段列出其 URL，供下游人工/选题裁决环节重点复核。

## 常见错误（红阶段基线观察）

| 错误（基线实际行为） | 纠正 |
|---|---|
| 健身吧 502 直接放弃+替补，没换通道 | 502/503 先试 opencli 本机浏览器（代理 IP 被封 ≠ 页面不存在） |
| 靠"文件 11KB+ 排除错误页"的体积启发式 | 必须跑 `validate` 数内容单位，≥500 才算采到 |
| 通道凭 URL 肉眼判断 | 每条必跑 `channel` 脚本，黑名单/标注/扩展名有明确优先级 |
| 失败源静默替换 | 替补关系记入 manifest（`替补自`），失败原因逐条写明 |
| 采完就完事，无汇总无验收 | 必须出 coverage-manifest.json 并报告验收结论；不达标回 source-scan 补搜 |

## 依赖

- `npx -y firecrawl-cli`（免 key 可 scrape；download 需 key，配于 ~/.config/gin-tutorial/config.yaml）
- opencli-browser 技能（知乎/B站专栏/登录墙降级通道）
- collector 技能（PDF/公众号/视频页）
- 上游：gin-tutorial-source-scan 的 sources.json
