---
name: jian-shen-zhui-zong
description: >
  健身数据追踪技能。用户消息中包含「健身追踪」四个字时立即触发（最高优先级）。
  当用户主动报告身体、饮食、睡眠、训练等健康数据时使用，包括但不限于：
  体重、体脂、排便、腰围等身体数据；入睡/起床时间、睡眠质量、能量、情绪、压力等状态数据；
  三餐时间、热量、蛋白、脂肪、碳水、水分等饮食数据；训练内容、训练时长、训练感受等训练数据。
  当用户说「记录体重」「今天吃了多少」「看看健身」「健身数据」「健身记录」「查询健身」
  「看看这周数据」「补数据」「补一下」「同步讯记」「健身追踪配置」「配置健身」等表达，
  或 cron 每日轮询定时触发时也使用。
  支持每日轮询、自然语言报数录入、补录历史数据、查看今日/本周/上周数据、
  讯记同步与初始化配置。
  **触发后必须立即发送反馈"🏃 健身追踪技能已激活，正在连接数据..."，然后再执行任何操作。**
  不用于制定训练计划、每周复盘分析、推荐健身房/补剂/动作或提供健身建议。
version: "v3.3.0"
---

# 健身追踪 v3.3.0

## 概述

健身追踪是三层健身架构中的**数据层**，负责每日健康数据的记录、查询与同步。

核心原则：
- 在正确的时刻问正确的问题
- 不覆盖用户主动录入的数据
- 所有写入必须复查验证
- **用户始终知道技能正在执行哪一步**

## 何时使用

- 用户消息中出现「健身追踪」四字
- 用户主动报告身体/饮食/睡眠/训练等健康数据字段（如体重、三餐时间、入睡时间、热量、训练内容等）
- 用户说"看看健身"、"健身数据"、"看看这周数据"等查看类表达
- cron 定时轮询触发
- 用户需要补数据、同步讯记或配置健身追踪

## 不使用场景

- 制定训练计划 → 使用健身规划技能
- 每周复盘分析 → 使用健身复盘技能
- 推荐健身房/补剂/动作 → 不提供建议

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

---

## 路由规则

### 核心触发词：「健身追踪」（最高优先级）

**用户消息中只要出现「健身追踪」四个字，必须立即触发本技能，无需其他条件。**

### 路由表

| 用户输入 | 路由目标 | 模式 |
|---------|---------|------|
| "健身追踪" 四字单独出现 | `collect-data` | 每日轮询 |
| "健身追踪" + 日期词（昨天/前天/上周 X/具体日期） | `collect-data` | 补数据模式 |
| "健身追踪" + 时段词（早上/上午/中午/下午/晚上/睡前） | `collect-data` | 轮询或询问确认 |
| "健身追踪" + 日期 + 时段 | `collect-data` | 指定时段补数据 |
| "补数据" / "补一下" + 日期描述 | `collect-data` | 补数据模式 |
| "看看健身" / "健身数据" / "健身记录" / "查询健身" | `query-data` | 查看数据 |
| "健身追踪配置" / "配置健身" | `init` | 初始化 |
| "同步讯记" | `sync-xunji` | 讯记同步 |
| 其他（含具体数据，如"晨起体重68.5kg"） | `collect-data` | 回复录入模式 |

**默认路由规则：** 用户仅说「健身追踪」四字时，进入**每日轮询**流程。

**路由优先级：** 「健身追踪」字面触发 > 触发词匹配 > cron 定时 > 上下文推断。

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
  "context": {}
}
```

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
| **测试** | `evals/evals.json` | 测试用例 |



## OpenClaw 配置

配置键与事件入口见 `config/openclaw-config.md`。



