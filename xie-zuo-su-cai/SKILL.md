---
name: xie-zuo-su-cai
description: |
  写作素材整理技能。当用户有模糊文章主题、想挖掘可用素材时使用。
  触发词：整理素材、挖素材、聊聊 X、想写 X、准备写。
  输出：在素材库根目录下创建 {日期}-{中文主题名}/ 项目文件夹，
  内含主题定义、需求澄清记录、会话状态、素材碎片和最终素材文档，
  可作为后续任何写作技能的输入素材。本技能只负责整理素材，不自动调用写作技能。
  必要时读取 references/methods.md、references/topic-definition-template.md、
  references/material-template.md。
---

# xie-zuo-su-cai（写作素材）

> "有材料才写得好。" 本技能只挖素材，不写文章。

## 触发反馈

每次触发先说：

```text
📝 写作素材技能已激活，正在准备挖掘素材...
```

## 落盘纪律（强制）

本技能的核心产出不是对话，而是**可复用的本地素材资产**。以下规则不可违反：

- **禁止只在 Agent 上下文里记忆用户说的话。**
- **禁止等聊完再统一保存。**
- **禁止以"用户没确认"为由跳过保存。** 用户愿意回答，就是愿意记录。
- 用户每轮回答后，只要包含故事、数字、观点、灵感、感受、修正中的任意一种，**必须立即调用 `scripts/save_turn.py` 保存到本地**。
- 每个主题项目必须包含：
  - `00-主题定义.md`
  - `00-需求澄清.md`
  - `01-会话状态.json`
  - `02-素材碎片/`

## 触发词

- "整理素材"
- "挖素材"
- "聊聊 X"
- "想写 X"
- "准备写 X"

## 动作路由

| 用户表达 | 动作 |
|---------|------|
| 触发词 + 主题 | `mine`：开始/继续挖掘 |
| "看看素材库" / "我的素材" | `review`：回顾碎片 |
| "这条不对" / "更新这条" | `correct`：修改碎片 |
| "重新生成素材文档" | `build`：生成最终文档 |

## 安装与一次性初始化

本技能需要一次性初始化。安装后或升级后，由用户运行：

```bash
python3 ~/.agents/skills/xie-zuo-su-cai/scripts/init.py \
  --material-root ~/Documents/写作素材库 \
  [--input-materials <文件或目录路径> ...]
```

`init.py` 会完成以下一次性工作，并把结果保存到技能可读取的位置：

1. **保存用户配置**
   - 写入 `~/.config/xie-zuo-su-cai/config.yaml`
   - 核心字段：`material_root`（素材库根目录）
2. **检查运行依赖**
   - Python 版本 >= 3.9
   - `pypinyin` 已安装
3. **检查素材库存储路径**
   - 验证 `material_root` 可写
   - 创建目录结构：`成品/`
   - 旧版 `.xie-zuo-su-cai/` 数据不会被自动迁移，检测到时会提示用户
4. **记录用户输入素材（可选）**
   - 若用户提供了文件/目录路径，验证其存在并记录到配置中

> **备份到当前 Agent 的 tools 目录（可选但推荐）**
>
> 初始化完成后，Agent 应把用户配置额外备份一份到当前 Agent 自己的 tools 目录，
> 防止技能目录被更新/覆盖后丢失用户配置：
> ```
> {agent-tools-dir}/xie-zuo-su-cai/config.yaml
> ```
> 调用 `init.py` 时通过 `--tools-backup-dir` 传入该路径。
> 不同 Agent 平台常见位置示例：
> - Claude Code / Superpowers：`~/.agents/tools/`
> - OpenClaw：`~/.openclaw/tools/`
> - Codex：`~/.codex/tools/`
>
> 日常使用读取配置时，若主配置丢失，会优先查找该 tools 目录下的备份。

> 初始化信息（配置、路径、依赖状态）保存在 `~/.config/xie-zuo-su-cai/config.yaml` 和（可选）`$XIE_ZUO_SU_CAI_TOOLS_DIR/xie-zuo-su-cai/config.yaml` 中，后续使用直接读取，不再重复初始化。

## 启动检查（每次触发）

每次触发 `mine` / `build` / `review` / `correct` 前，只做轻量读取和校验：

1. **读取已保存的配置**
   - 从 `~/.config/xie-zuo-su-cai/config.yaml` 读取 `material_root`
   - 若配置不存在，提示用户先运行 `scripts/init.py`
2. **校验素材库路径**
   - 确认 `material_root` 目录存在且可写
3. **读取用户输入素材（可选）**
   - 若配置或本次对话中提供了素材路径，验证其存在

> 启动检查失败时停止后续流程，向用户报告具体问题（通常是配置丢失或路径不可写）。

## 主流程（mine）

1. 接收初始主题
2. **定位/创建项目文件夹**：根据主题名查找已有 `{material_root}/{日期}-{中文主题名}/` 文件夹；若无则按当前日期新建
3. **主题定义**：调用 `scripts/topic_def.py` 生成 `00-主题定义.md`，用多选题确认读者/文体/判断方向
4. 拉取锚点素材（最近 2 周 3-5 篇成品），放入 `成品/` 目录
5. 选择挖掘域（writing/topic/product/aesthetic/audience），写入 `01-会话状态.json`
6. 对话循环（8/16/24 轮硬上限）
   - 选方法：读取 `references/methods.md`，从 A-G 中选一种且不连续重复
   - 提问（附 AI 猜测）
   - 等待回答
   - 追问（最多 2 次）
   - Teachback 复述
   - 用户确认/纠正
   - **记录对话：调用 `scripts/save_turn.py` 把本轮 AI 问题和用户原始表达追加到 `00-需求澄清.md`，并更新 `01-会话状态.json`**
   - **记录素材：用户确认有价值后，再次调用 `scripts/save_turn.py`（带上 `--confidence` 和 `--direction`）生成 `02-素材碎片/{日期}-{序号}.md`**
   - 显示完整性评分（调用 `scripts/validate.py` 中的逻辑）
7. 达到收尾条件后调用 `scripts/build_doc.py` 整合素材文档 `03-素材文档.md`
8. 输出素材文档路径，技能结束。是否基于该素材调用其他写作技能，由用户自行决定。

## 完整性评分

每轮显示：

```text
📊 素材挖掘进度
- 已确认素材：X/5
- 章节覆盖：X/2
- 主题清晰度：X/5
```

## 结束边界

素材文档生成后，本技能任务完成。Agent 应只输出素材文档路径，例如：

```text
✅ 素材文档已生成：{路径}

素材整理完成。你可以基于这些素材使用任何写作技能继续创作。
```

**本技能不自动调用任何写作技能**（包括 `human-writing`、`khazix-writer`、`wechat-article-core` 等）。是否进入写作阶段，由用户主动决定。

## 边界

- ❌ 不写大纲
- ❌ 不写文章
- ❌ 不搜网络资料
- ❌ 不把多条素材提炼成一条规则
