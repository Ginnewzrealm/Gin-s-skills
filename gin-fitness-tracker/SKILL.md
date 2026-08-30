---
name: gin-fitness-tracker
description: >
  健身数据追踪技能。用户说「健身追踪」、报告具体健康数据字段、查询健身数据、补录数据、同步讯记或配置时触发。
  触发后必须立即发送反馈"🏃 健身追踪技能已激活，正在连接数据..."，然后再执行任何操作。
  不用于制定训练计划、每周复盘分析、推荐健身房/补剂/动作或提供健身建议。
version: "v3.5.2"
---

# 健身追踪 v3.5.2

## 概述

健身追踪是三层健身架构中的**数据层**，负责每日健康数据的记录、查询与同步。

核心原则：
- 在正确的时刻问正确的问题
- 不覆盖用户主动录入的数据
- 所有写入必须复查验证
- **用户始终知道技能正在执行哪一步**

## ⚠️ Agent 硬规则（本 skill 内的写入唯一入口）

**本 skill 管辖范围内的一切数据写入，必须通过本 skill 完成。**

1. **禁止直接调用 `lark-cli sheets` 写入「每日记录」表或「用户配置」表。**
2. **所有写入必须经过 `write-verify` 子技能或 `scripts/record_fields_once.py` 脚本。**
3. **写入前必须读取表头，并通过 `scripts/build_header_map.py` 生成 `header_map.json`。**
4. **`scripts/prepare_write_request.py` 是构造 `+cells-set` range 的唯一入口，Agent 不得自己推断列字母或构造 range。**
5. **如果写入验证失败，本 skill 会自动换工具重试并自动重新读取表头重跑完整流程。Agent 不得在同一 turn 内用 `lark-cli` 逐格手动修复。**
6. **违反以上任意一条，视为 bypass 本 skill，必须停止并重新触发本 skill 执行。**

这些规则是 skill 内部约定。OpenClaw 系统层面的强制约束由系统侧的 `AGENTS.md` 负责，不在本 skill 文件范围内。

## 何时使用

本技能通过 `scripts/trigger_classifier.py` 判断用户消息是否触发。触发信号包括：

1. **显式 invocation**：消息中出现「健身追踪」四字
2. **数据录入**：消息包含具体健康数据字段及其值，例如：
   - 身体："晨起体重 68.5"、"体脂率 23.8"
   - 睡眠："昨晚 12 点睡的"
   - 饮食："今天吃了 1800 卡"
   - 训练："力量练了胸+三头"
3. **查询**："看看这周数据"、"今天填了什么"、"健身数据"
4. **补录**："补一下昨天"、"补数据 8 月 29 日"
5. **配置**："健身追踪配置"、"配置健身"
6. **同步**："同步讯记"
7. **Cron**：`cron:daily_poll`

**不触发场景**（命中否定触发词）：
- 周报/分析/复盘：`PDCA分析`、`健身周报`、`本周总结`、`代谢分析`
- 训练计划/日记：`今天练胸`、`帮我安排训练`、`训练打卡`、`总结今天的训练`
- 建议/推荐：`怎么健身`、`推荐蛋白粉`、`健身房推荐`
- 医疗/伤病：`膝盖疼`、`康复训练`

## 触发规则

### 触发优先级

1. **否定触发词优先**：消息含周报/计划/建议/训练日记/医疗等词 → **不触发**
2. **cron 触发**：`cron:daily_poll` → `daily_poll`
3. **显式配置/同步**：`健身追踪配置`/`配置健身` → `init`；`同步讯记` → `sync`
4. **字面触发**：`健身追踪` → 根据日期/时段/数据判断 `daily_poll` / `makeup` / `reply_entry`
5. **字段指纹**：消息含字段名/同义词 + 数值/时间/选项 → `reply_entry`
6. **查询意图**：含查询词 + 健身/数据/饮食语境 → `query`
7. **补数据**：`补数据`/`补一下` + 日期/字段 → `makeup`

### 触发分类脚本

所有触发判断统一走 `scripts/trigger_classifier.py`：

```bash
cat <<'JSON' | python3 scripts/trigger_classifier.py
{
  "message": "今早体重68.5，昨晚12点睡的",
  "context": {"cron": false}
}
JSON
```

输出：

```json
{
  "triggered": true,
  "mode": "reply_entry",
  "reason": "字段指纹匹配：晨起体重、入睡时间",
  "excluded_by": null
}
```

`mode` 取值：
- `daily_poll`：每日轮询
- `reply_entry`：回复录入
- `makeup`：补数据
- `query`：查询数据
- `init`：初始化配置
- `sync`：讯记同步

---

## ⚡ 更新日志规则

**每次对技能进行修改时，必须同步更新 `CHANGELOG.md`。**

更新要求：
1. 在 `CHANGELOG.md` 顶部添加新的更新记录
2. 更新 `SKILL.md` 顶部的 `version` 字段
3. 记录：日期、版本号、更新类型、涉及文件、主要内容

更新类型定义：
- `新增`：增加新功能或新模块
- `修复`：修复 bug 或问题
- `优化`：改进现有功能但不改变行为
- `重构`：改变实现方式但行为不变

---

## ⚡ 统一反馈规则

健身追踪技能要求**在任何操作之前、之中、之后都向用户发送状态反馈**。

### 触发反馈（必须在最前面）

技能被触发后，**第一句话必须是**：

```
🏃 健身追踪技能已激活，正在连接数据...
```

### 子模块状态反馈

进入每个子模块时，必须发送对应的状态反馈：

| 子模块 | 状态反馈 |
|--------|---------|
| `init` | `🔧 正在执行初始化：检查配置与数据连接...` |
| `query-data` | `📊 正在读取你的健身数据...` |
| `collect-data` | `📝 正在生成当前时段需要记录的内容...` |
| `write-verify` | `✍️ 正在写入并校验数据...` |
| `sync-xunji` | `🔄 正在同步讯记数据（不覆盖已录入内容）...` |

### 操作完成反馈

**只有在子模块返回 `success` 且写入操作已通过回读验证时，才发送完成反馈：**

```
✅ 数据记录完成，正在同步最新状态...
```

**发送前提（操作完成反馈必须在 write-verify 返回 success 且复查通过后发送）：**
- `write-verify` 返回 `status: "success"`
- 返回中包含写入证据（`revision`、`updated_cells_count`）
- 所有标记为 `fields_written` 的字段都经过回读验证，值与写入请求一致

**严禁在以下情况下发送 ✅ 完成反馈**：
- ❌ `write-verify` 返回 `failed` 或 `partial`
- ❌ 没有执行回读验证
- ❌ 回读值与写入值不一致
- ❌ lark-cli 调用失败或没有返回 `revision`/`updated_cells_count`

### 错误反馈

遇到错误时，使用统一错误格式（详见"统一错误处理"章节）。

当 `write-verify` 返回 `failed` 或 `partial` 时，协调器必须发送错误/部分成功反馈，而不是 ✅ 完成反馈。

即：write-verify 返回 failed 或 partial 时，禁止发送 "✅ 数据记录完成" 反馈。

触发反馈发送后，如果本次进入新子模块，紧接着输出该子模块的场景定位句 + micro-checklist。

---

## 群聊静默模式

当 `context.channel_type == "group"` 时，技能进入**群聊静默模式**：内部仍然完整执行所有 stage 和校验，但对用户的反馈做精简，避免在群里刷屏。

### 输入中的通道类型

子模块调用输入应包含：

```json
{
  "mode": "reply_entry",
  "date": "2026-08-30",
  "user_input": "今早体重68.5",
  "context": {
    "channel_type": "group" | "private"
  }
}
```

- `private`：正常展示 Progress Checklist 和每步状态反馈
- `group`：进入静默模式

### 静默模式反馈规则

| 信息类型 | group 模式 | private 模式 |
|---------|-----------|-------------|
| 触发反馈 | ✅ `🏃 健身追踪技能已激活，正在处理...` | ✅ `🏃 健身追踪技能已激活，正在连接数据...` |
| 子模块状态反馈 | ❌ 不展示 | ✅ 展示 |
| Progress Checklist 每一步 | ❌ 不展示 | ✅ 展示 |
| 写入失败 / 正在重试 | ✅ 展示 | ✅ 展示 |
| 硬闸门需要用户确认 | ✅ 展示并等待 | ✅ 展示并等待 |
| 完成摘要 | ✅ 最终一条消息 | ✅ 最终一条消息 |

### 静默模式示例

**群聊触发**：
```
🏃 健身追踪技能已激活，正在处理...
```

**群聊结束（成功）**：
```
✅ 已记录 2 个字段：晨起体重 68.5 kg、入睡时间 00:30
```

**群聊结束（有失败字段）**：
```
⚠️ 部分成功：晨起体重已记录；体脂率写入失败，原因：... 可回复「重来」重新执行
```

**重要**：静默模式只隐藏"进度展示"，不隐藏"异常"和"需要确认"的硬闸门。

---

## Progress Checklist 使用规则

本技能含 5 个子模块：`init`、`collect-data`、`query-data`、`sync-xunji`、`write-verify`。每次触发本技能时，先根据路由表选择目标子模块，然后**立即输出场景定位句 + 该子模块 micro-checklist**。

### 场景定位句

进入任意子模块时，先说一句：

```markdown
当前场景：gin-fitness-tracker — [子模块名]
```

例如：
- 初始化 → `当前场景：gin-fitness-tracker — init`
- 数据收集 → `当前场景：gin-fitness-tracker — collect-data`
- 数据查询 → `当前场景：gin-fitness-tracker — query-data`
- 讯记同步 → `当前场景：gin-fitness-tracker — sync-xunji`
- 写入验证 → `当前场景：gin-fitness-tracker — write-verify`

### micro-checklist 标签

| 标签 | 含义 |
|------|------|
| `[自动]` | AI / 脚本自动读取配置/表头/写入数据，无需用户实时输入 |
| `[需确认]` | 需要用户查看并确认，但非强制阻塞 |
| `[硬闸门]` | 用户不确认则不能继续下一步 |
| `[可回环]` | 用户可要求回退到前面步骤重做 |

### 展示时机

1. **流程开始时**：输出场景定位句 + 完整 micro-checklist，高亮当前步骤。
2. **进入硬闸门时**：再次展示 checklist，并追加 `当前阻塞：等待你确认 XXXX。`
3. **完成时**：将最后一步标记为 `[✓]`，输出关键结果（写入字段数、失败字段、未验证项）。
4. **子模块切换时**：输出新子模块的场景定位句 + micro-checklist，继承上游状态。
5. **会话中断恢复时**：读取当前日期行后，重新输出完整 checklist + 当前阻塞提示。

### 禁止

- 不要跳过 `write-verify` 返回的 `needs_user_input` 硬闸门
- 不要静默覆盖用户已有数据
- 不要在用户说"重来"或"回退"时不重置 checklist 状态
- 不要子模块直接向用户输出未经协调的长篇结果

---

## 路由规则

### 路由入口

所有触发判断统一调用 `scripts/trigger_classifier.py`：

```bash
cat <<'JSON' | python3 scripts/trigger_classifier.py
{
  "message": "用户原始消息",
  "context": {"cron": false}
}
JSON
```

协调器根据脚本的 `mode` 路由到对应子技能：

| `trigger_classifier.py` 输出 `mode` | 路由目标 | 子技能模式 |
|---------|---------|------|
| `daily_poll` | `collect-data` | 每日轮询 |
| `reply_entry` | `collect-data` | 回复录入 |
| `makeup` | `collect-data` | 补数据 |
| `query` | `query-data` | 查看数据 |
| `init` | `init` | 初始化配置 |
| `sync` | `sync-xunji` | 讯记同步 |
| `triggered: false` | — | 不触发，转交其他技能处理 |

### 路由示例

| 用户输入 | `mode` | 路由目标 |
|---------|--------|---------|
| "健身追踪" | `daily_poll` | `collect-data` |
| "健身追踪 昨天" | `makeup` | `collect-data` |
| "晨起体重68.5" | `reply_entry` | `collect-data` |
| "昨晚12点睡的" | `reply_entry` | `collect-data` |
| "看看这周数据" | `query` | `query-data` |
| "今天吃了多少" | `query` | `query-data` |
| "补一下昨天" | `makeup` | `collect-data` |
| "配置健身" | `init` | `init` |
| "同步讯记" | `sync` | `sync-xunji` |
| "PDCA分析" | `triggered: false` | 不触发（转 `gin-fitness-pdca`） |
| "今天练胸" | `triggered: false` | 不触发（转 `gin-workout-planner`） |

### 默认路由规则

- 用户仅说「健身追踪」四字 → `daily_poll`
- `trigger_classifier.py` 返回 `triggered: false` → **不得触发本技能**

### 路由优先级

由 `trigger_classifier.py` 内部决定，协调器直接服从脚本输出：

1. 否定触发词（不触发）
2. cron 定时
3. 显式配置/同步
4. 「健身追踪」字面触发
5. 字段指纹
6. 查询意图
7. 补数据意图

---

## 反馈协调器

`SKILL.md` 作为唯一的用户交互入口，承担**反馈协调器**职责：

```
用户触发技能
    ↓
发送触发反馈：🏃 健身追踪技能已激活，正在连接数据...
    ↓
根据路由表选择目标子模块
    ↓
调用子模块，子模块发送自身状态反馈
    ↓
子模块执行具体操作
    ↓
子模块返回结构化结果
    ↓
协调器汇总并发送最终反馈
```

**禁止子模块直接向用户输出未经协调的长篇结果。** 所有子模块的输出必须通过上述返回格式交给 `SKILL.md` 汇总。

### 查询数据展示规则

`query-data` 返回的 `data.records[]` 中每个记录包含：
- `filled_fields`：已填字段摘要
- `blank_fields` / `not_yet_due_fields`：空白字段（含三态归类）
- `raw_record`：表头行定义的**全部字段**原始值，空白字段用 `null` 表示

协调器根据用户意图选择展示方式：

| 用户意图 | 必须展示的内容 |
|---------|---------------|
| 简单询问"今天填了什么"、"看看今日数据"、"健身数据" | 可展示 `filled_fields` 摘要 + 三态归类 |
| 要求"检查"、"看一下"、"审计"、"核对"、"完整数据" | **必须展示完整 `raw_record`** |

**重要原则**：当用户需要判断数据异常、缺失或格式错误时，Agent 不得替用户过滤空白字段。完整原始记录是发现异常（如公式字段被静态值覆盖、值写入错误列）的唯一依据。

---

## 子模块调用规范

### 输入

子模块接收的输入由 `SKILL.md` 根据路由决定，通常包含：

```json
{
  "mode": "daily_poll" | "reply_entry" | "makeup" | "query" | "init" | "sync",
  "date": "2026-07-26",
  "user_input": "用户原始消息或回复",
  "context": {
    "channel_type": "group" | "private"
  }
}
```

`context.channel_type` 用于控制反馈粒度：
- `private`：展示完整 Progress Checklist 和每步状态反馈
- `group`：进入群聊静默模式，只展示触发反馈、异常、硬闸门和最终摘要

如果 `context.channel_type` 缺失，默认按 `private` 处理。

### 输出

所有子模块必须返回统一的 JSON 结构：

```json
{
  "status": "success" | "partial" | "failed" | "needs_user_input",
  "module": "init" | "query-data" | "collect-data" | "write-verify" | "sync-xunji",
  "message": "给用户看的自然语言摘要",
  "data": {},
  "errors": []
}
```

字段说明：
- `status`：执行状态
  - `success`：全部成功
  - `partial`：部分成功（有失败或跳过的字段）
  - `failed`：整体失败
  - `needs_user_input`：需要用户进一步回复才能继续
- `module`：当前子模块名称
- `message`：给用户的自然语言摘要，简洁专业
- `data`：模块返回的结构化数据
- `errors`：错误列表，每个错误包含 `code` 和 `message`

---

## 字段名白名单

**所有字段名必须以运行时读取的表头行为唯一白名单。**

- `collect-data` 生成问题时，字段名必须 100% 来自 `read_header` 返回的表头行。
- `write-verify` 写入前，必须再次核对字段名是否在白名单中。
- 不在白名单中的字段名 → 返回 `FIELD_NOT_FOUND`，不得写入、不得生成问题、不得展示。

这条规则优先于任何语义推断、记忆或示例。

---

## 统一错误处理

所有错误统一编码，由 `SKILL.md` 汇总输出。错误格式：

```
[图标] 错误简短描述
原因：具体原因
操作：建议用户执行的操作
影响：该错误对当前流程的影响
```

### 错误码表

| 错误码 | 含义 | 关键处理 |
|--------|------|---------|
| `CONFIG_MISSING` | 配置缺失 | 提示运行健身规划技能或手动填写 |
| `TABLE_NOT_FOUND` | 表不存在 | 提示在飞书创建表并更新配置 |
| `RECORD_NOT_FOUND` | 记录不存在 | 提示在飞书手动创建日期行 |
| `LARK_SKILL_UNAVAILABLE` | 所选后端依赖的 lark-sheets skill 未安装或不可用 | 检查是否已安装 lark-sheets skill |
| `FIELD_TYPE_MISMATCH` | 字段元数据中的类型/选项与真实表格列验证不一致 | 返回 warning，提示用户检查表格字段配置；不阻塞其他字段写入 |
| `FIELD_NOT_FOUND` | 写入请求包含表头行中不存在的字段名 | 停止该字段写入；字段名必须来自运行时读取的表头行白名单 |
| `DUPLICATE_HEADER` | 表头行中存在重复字段名 | 停止写入；提示用户检查并删除/重命名重复字段 |
| `ROW_MAP_MISSING` | 用户配置表写入时缺少字段→行号映射 | 停止该字段写入；必须提供 `row_map` |
| `FIELD_WRITE_FAILED` | 字段写入失败 | 换工具重试后仍失败，不阻塞其他字段 |
| `INVALID_OPTION` | 选项无效 | 给出可选值列表，请用户重选；一律禁止新建选项（飞书 API 会静默自动创建） |
| `XUNJI_UNAVAILABLE` | 讯记不可用 | 提示安装对应讯记 skill，继续运行 |

各场景的完整错误文案模板见对应子模块文件。

---

## 数据存储抽象层

所有读写操作通过统一 DataStore 接口，不直接操作飞书或 JSON。

### DataStore 接口定义

```javascript
const DataStore = {
  async getUserConfig() { /* 读取用户配置表，返回配置项映射 */ },
  async updateUserConfig(changes) { /* 更新用户配置表中的特定字段 */ },
  async writeDailyRecord(date, fields) { /* 写入每日记录表；日期行不存在时自动按升序创建 */ },
  async getDailyRecord(date) { /* 读取某日记录（用于校验） */ }
}
```

**支持的后端**：
- `feishu_sheets`：飞书普通表格（默认）
- `local_json`：本地 JSON 文件目录
- `obsidian`：Obsidian Vault 子目录

**后端切换方式**：
- 用户在 `atlas-config.yaml` 中指定 `fitness.backend`
- `fitness.backend` 缺失时：
  - 存在 `fitness.sheets.spreadsheet_token` → `feishu_sheets`
  - 否则默认 `feishu_sheets`，并提示用户补充配置

**技能边界**：
- 健身追踪技能只定义 DataStore 接口和业务字段语义
- Sheets 后端的具体读写委托给 `lark-sheets` skill 执行
- 调用 `lark-sheets` 时必须附带 `knowledge/sheets-calling-patterns.md` 中定义的完整命令模板，禁止只传模糊意图（如"读取表头行"）
- 健身追踪内部负责字段名→列字母映射、字段类型校验、单选选项匹配等业务逻辑；`lark-sheets` skill 负责执行具体 CLI 命令

详细实现方式见 `knowledge/field-guide.md`。

### 外部技能桥接约定

- 讯记 skill 调用约定 → `references/xunji-bridge.md`
- lark-sheets skill 调用约定 → `references/lark-sheets-bridge.md`

---

## 文件索引

| 类别 | 文件 | 说明 |
|------|------|------|
| **入口** | `SKILL.md` | 技能入口，总路由，反馈协调器 |
| **原子技能** | `skills/init/SKILL.md` | 检查配置、工具、表，初始化用户配置表 |
| | `skills/collect-data/SKILL.md` | 每日轮询、补数据、回复录入 |
| | `skills/query-data/SKILL.md` | 查看数据，只读 |
| | `skills/write-verify/SKILL.md` | 统一写入入口、字段校验、复查验证 |
| | `skills/sync-xunji/SKILL.md` | 讯记同步（可选填充，不覆盖用户数据） |
| **知识库** | `knowledge/polling-rules.md` | 时区与周定义、时段规则、字段 description 规范 |
| | `knowledge/field-guide.md` | 字段类型处理、DataStore 实现指南 |
| | `knowledge/sheets-calling-patterns.md` | 与 `lark-sheets` skill 的 9 种显式调用模式与命令模板 |
| | `knowledge/sleep-rules.md` | 睡眠数据归属 |
| | `knowledge/training-day-rules.md` | 训练日/休息日判断、碳水循环 |
| | `knowledge/target-display-guide.md` | 目标值展示规则 |
| | `knowledge/xunji-api-guide.md` | 讯记 API 规则、数据来源优先级 |
| **配置参考** | `config/sheets-schema.md` | Sheets 后端表结构参考 |
| | `config/field-metadata-schema.md` | 字段元数据子表定义（字段时段/类型/选项/填写说明） |
| | `config/user-profile-schema.md` | 用户配置表结构（权威定义） |
| | `config/openclaw-config.md` | OpenClaw 配置键与事件入口 |
| **维护** | `CHANGELOG.md` | 更新日志 |
| **工具脚本** | `scripts/build_header_map.py` | 表头行 → 字段名→列字母映射 |
| | `scripts/build_column_constraints.py` | 真实列约束解析 |
| | `scripts/prepare_write_request.py` | 构造 `+cells-set` payload |
| | `scripts/validate_field_metadata.py` | 字段元数据类型校验 |
| | `scripts/coerce_value.py` | 按真实列约束转换值形态 |
| | `scripts/check_existing_values.py` | 检查字段是否已有值 |
| | `scripts/compare_written_values.py` | 写入值 vs 回读值对比 |
| | `scripts/detect_option_pollution.py` | 检测未授权新增选项 |
| | `scripts/stage_validator.py` | Progress Checklist 阶段产物校验 |
| | `scripts/progress_reporter.py` | 进度汇报格式化 |
| | `scripts/trigger_classifier.py` | 触发意图分类 |
| | `scripts/record_fields_once.py` | 一键完成校验→转换→已有值检查→写入计划 |
| **测试** | `evals/evals.json` | 测试用例 |



## OpenClaw 配置

配置键与事件入口见 `config/openclaw-config.md`。



