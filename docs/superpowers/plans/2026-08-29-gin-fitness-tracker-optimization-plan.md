# gin-fitness-tracker 融入 Progress Checklist + 桥接规范优化方案

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `/Users/fubo/Downloads/AI技能进度条设计指南.md` 中的 Progress Checklist 设计模式融入 `gin-fitness-tracker`，同时按 `/Users/fubo/Downloads/技能桥接模式技术规范.md` v2.0 补齐标准桥接文件（xunji-bridge、lark-sheets-bridge）。

**架构：** 在 `SKILL.md` 路由器层增加统一 Progress 规则与场景定位句；在 5 个子技能 `skills/*/SKILL.md` 中把现有执行流程改写成 micro-checklist；使用 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]` 标签标注步骤属性；新建/重构 `references/xunji-bridge.md` 和 `references/lark-sheets-bridge.md` 为标准五章格式。

**技术栈：** Markdown 技能文档 + YAML frontmatter，无新增脚本，无需依赖。

---

## 涉及文件

| 文件 | 当前职责 | 改动内容 |
|------|---------|---------|
| `gin-fitness-tracker/SKILL.md` | 主路由器、反馈协调器、路由表、子模块调用规范 | 新增 `## Progress Checklist 使用规则`；更新触发/状态/完成反馈与 checklist 对齐；登记新建桥接文件 |
| `gin-fitness-tracker/skills/init/SKILL.md` | 初始化子技能 | 执行流程改写成 micro-checklist；标注硬闸门/可回环 |
| `gin-fitness-tracker/skills/collect-data/SKILL.md` | 数据收集子技能 | 执行流程改写成 micro-checklist；标注问题生成前检查单、write-verify 调用等硬闸门 |
| `gin-fitness-tracker/skills/write-verify/SKILL.md` | 写入验证子技能 | 12 步写入流程改写成 micro-checklist；标注字段已有值确认、单选项校验等硬闸门 |
| `gin-fitness-tracker/skills/query-data/SKILL.md` | 查询子技能 | 执行流程改写成 micro-checklist |
| `gin-fitness-tracker/skills/sync-xunji/SKILL.md` | 讯记同步子技能 | 执行流程改写成 micro-checklist；标注讯记不可用降级 |
| `gin-fitness-tracker/references/xunji-bridge.md` | 不存在 | 新建标准五章桥接文件，整合 `knowledge/xunji-api-guide.md` 核心内容 |
| `gin-fitness-tracker/references/lark-sheets-bridge.md` | 不存在 | 新建标准五章桥接文件，收敛 `knowledge/sheets-calling-patterns.md` 的调用契约 |
| `gin-fitness-tracker/CHANGELOG.md` | 技能变更记录 | 顶部追加 v3.4.0 优化条目 |
| `gin-fitness-tracker/SKILL.md` frontmatter | 版本号 | `version` 从 `v3.3.0` 改为 `v3.4.0` |

---

### 任务 1：在 `SKILL.md` 增加统一 Progress 规则

**文件：**
- 修改：`gin-fitness-tracker/SKILL.md`

- [ ] **步骤 1：在「路由规则」之前插入 `## Progress Checklist 使用规则` 章节**

在 `## 路由规则` 标题之前（约第 116 行）插入以下内容：

```markdown
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
```

- [ ] **步骤 2：更新「统一反馈规则」与 checklist 展示时机对齐**

在「### 触发反馈（必须在最前面）」段落末尾追加：

```markdown
触发反馈发送后，如果本次进入新子模块，紧接着输出该子模块的场景定位句 + micro-checklist。
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/SKILL.md
git commit -m "docs(gin-fitness-tracker): 增加 Progress Checklist 使用规则

- 新增场景定位句与 micro-checklist 标签说明
- 明确展示时机与禁止项
- 触发反馈后输出 checklist"
```

---

### 任务 2：初始化子技能 `init` 改写成 micro-checklist

**文件：**
- 修改：`gin-fitness-tracker/skills/init/SKILL.md`

- [ ] **步骤 1：在 `## 执行流程` 后插入 micro-checklist**

在 `## 执行流程` 标题后、流程图之前插入：

```markdown
### 场景进度

当前场景：gin-fitness-tracker — init

Progress:
- [ ] Step 1 发送模块状态反馈 [自动]
- [ ] Step 2 读取 atlas-config.yaml 并确定存储后端 [自动]
- [ ] Step 3 加载对应后端 skill [自动]
- [ ] Step 4 检查数据存储是否可读写 [自动]
- [ ] Step 5 检测每日记录表是否存在 [自动]
- [ ] Step 6 检测字段元数据子表是否存在 [自动]
- [ ] Step 7 检测用户配置表是否存在 [自动]
- [ ] Step 8 字段元数据一致性抽查 [自动]
- [ ] Step 9 返回初始化完成 [自动]

禁止：
- 不要在表不存在时自动创建
- 不要在后端 skill 不可用时降级为直连 API
```

- [ ] **步骤 2：commit**

```bash
git add gin-fitness-tracker/skills/init/SKILL.md
git commit -m "docs(init): 初始化流程改写成 Progress Checklist

- 插入 9 步 micro-checklist
- 标注所有步骤为自动"
```

---

### 任务 3：数据收集子技能 `collect-data` 改写成 micro-checklist

**文件：**
- 修改：`gin-fitness-tracker/skills/collect-data/SKILL.md`

- [ ] **步骤 1：在 `## 执行流程` 后插入 micro-checklist**

在 `## 执行流程` 标题后、流程图之前插入：

```markdown
### 场景进度

当前场景：gin-fitness-tracker — collect-data

Progress:
- [ ] Step 1 发送模块状态反馈 [自动]
- [ ] Step 2 校准北京时间并判断当前时段 [自动]
- [ ] Step 3 读取用户配置表 [自动]
- [ ] Step 4 动态读取字段详情（表头行 + 字段元数据） [自动]
- [ ] Step 5 问题生成前强制检查清单 [硬闸门]
- [ ] Step 6 生成问题或解析用户数据 [需确认] / [自动]
- [ ] Step 7 调用 write-verify 写入数据 [自动]
- [ ] Step 8 更新用户配置表中的当前体重/体脂 [自动]
- [ ] Step 9 最晚时段触发 sync-xunji [自动]
- [ ] Step 10 返回结构化结果 [自动]

禁止：
- 不要凭记忆构造字段名
- 不要为表头行中不存在的字段生成问题
- 不要静默覆盖用户已有数据
```

- [ ] **步骤 2：在 Step 5 检查清单后增加硬闸门阻塞提示**

在「问题生成前强制检查清单」段落后追加：

```markdown
   **本步骤为硬闸门。任一检查不通过时输出：**
   `当前阻塞：字段名/选项校验未通过，不能生成问题。请检查表格字段配置后回复「继续」，或回复「重来」从 Step 4 开始。`
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/skills/collect-data/SKILL.md
git commit -m "docs(collect-data): 数据收集流程改写成 Progress Checklist

- 插入 10 步 micro-checklist
- 标注问题生成前检查单为硬闸门
- 增加硬闸门阻塞提示"
```

---

### 任务 4：写入验证子技能 `write-verify` 改写成 micro-checklist

**文件：**
- 修改：`gin-fitness-tracker/skills/write-verify/SKILL.md`

- [ ] **步骤 1：在 `## 执行流程` 后插入 micro-checklist**

在 `## 执行流程` 标题后、流程图之前插入：

```markdown
### 场景进度

当前场景：gin-fitness-tracker — write-verify

Progress:
- [ ] Step 1 发送模块状态反馈 [自动]
- [ ] Step 2 接收写入请求 [自动]
- [ ] Step 3 读取字段元数据 + 表头行 [自动]
- [ ] Step 4 读取每列真实格式与验证约束 [自动]
- [ ] Step 5 写入前强制检查清单 [硬闸门]
- [ ] Step 6 字段名白名单校验 [自动]
- [ ] Step 7 跳过公式字段 [自动]
- [ ] Step 8 字段已有值检查 [硬闸门]
- [ ] Step 9 按真实列约束转换原始值 [自动]
- [ ] Step 10 单选/多选字段匹配表格选项 [硬闸门]
- [ ] Step 11 执行写入 [自动]
- [ ] Step 12 写入值 vs 复查值对比 [自动]
- [ ] Step 13 选项污染检测 [自动]
- [ ] Step 14 换工具重试 [自动]
- [ ] Step 15 汇总成功/失败列表 [自动]

禁止：
- 不要静默覆盖用户已有数据
- 不要写入公式字段
- 不要新建单选/多选选项
```

- [ ] **步骤 2：在 Step 8 字段已有值检查后增加阻塞提示**

在「字段已有值检查」章节末尾追加：

```markdown
   **本步骤为硬闸门。目标字段已有值时输出：**
   `当前阻塞：字段[XXX]已有值[YYY]，是否覆盖？回复「是」覆盖，「否」跳过。`
```

- [ ] **步骤 3：在 Step 10 单选匹配后增加阻塞提示**

在「单选/多选字段匹配表格选项」章节末尾追加：

```markdown
   **本步骤为硬闸门。用户选项无法匹配真实下拉选项时输出：**
   `当前阻塞：「XXX」不在可选值中。可选值为：A/B/C。请回复正确选项，或回复「跳过」跳过该字段。`
```

- [ ] **步骤 4：commit**

```bash
git add gin-fitness-tracker/skills/write-verify/SKILL.md
git commit -m "docs(write-verify): 写入验证流程改写成 Progress Checklist

- 插入 15 步 micro-checklist
- 标注已有值检查、单选项匹配为硬闸门
- 增加硬闸门阻塞提示"
```

---

### 任务 5：查询子技能 `query-data` 改写成 micro-checklist

**文件：**
- 修改：`gin-fitness-tracker/skills/query-data/SKILL.md`

- [ ] **步骤 1：在 `## 执行流程` 后插入 micro-checklist**

在 `## 执行流程` 标题后、流程图之前插入：

```markdown
### 场景进度

当前场景：gin-fitness-tracker — query-data

Progress:
- [ ] Step 1 发送模块状态反馈 [自动]
- [ ] Step 2 解析查询目标范围 [自动]
- [ ] Step 3 校准北京时间并判断当前时段 [自动]
- [ ] Step 4 读取表头行 [自动]
- [ ] Step 5 读取用户配置表 [自动]
- [ ] Step 6 读取目标日期行数据 [自动]
- [ ] Step 7 汇总展示（已填/空白/完整记录） [自动]
- [ ] Step 8 返回结构化结果 [自动]

禁止：
- 不要过滤空白字段
- 不要凭记忆添加表头行中不存在的字段
```

- [ ] **步骤 2：commit**

```bash
git add gin-fitness-tracker/skills/query-data/SKILL.md
git commit -m "docs(query-data): 查询流程改写成 Progress Checklist

- 插入 8 步 micro-checklist
- 标注所有步骤为自动"
```

---

### 任务 6：讯记同步子技能 `sync-xunji` 改写成 micro-checklist

**文件：**
- 修改：`gin-fitness-tracker/skills/sync-xunji/SKILL.md`

- [ ] **步骤 1：在 `## 执行流程` 后插入 micro-checklist**

在 `## 执行流程` 标题后、流程图之前插入：

```markdown
### 场景进度

当前场景：gin-fitness-tracker — sync-xunji

Progress:
- [ ] Step 1 发送模块状态反馈 [自动]
- [ ] Step 2 检测讯记 skill 是否可用 [自动]
- [ ] Step 3 调用讯记 skill 拉取数据 [自动]
- [ ] Step 4 对比用户已录入数据 [自动]
- [ ] Step 5 只填充空白字段（不覆盖用户数据） [自动]
- [ ] Step 6 标记数据来源为「讯记同步」 [自动]
- [ ] Step 7 返回结构化结果 [自动]

禁止：
- 不要覆盖用户主动录入的数据
- 不要估算或编造讯记缺失数据
- 不要代劳讯记领域的操作需求
```

- [ ] **步骤 2：在 Step 2 检测不可用后增加降级说明**

在「现场检测讯记 skill 是否可用」段落后追加：

```markdown
   **讯记 skill 不可用时，本步骤不阻塞主流程，输出：**
   `当前阻塞：讯记同步不可用（xunji-xxx skill 未安装）。跳过讯记填充，继续运行。`
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/skills/sync-xunji/SKILL.md
git commit -m "docs(sync-xunji): 讯记同步流程改写成 Progress Checklist

- 插入 7 步 micro-checklist
- 标注讯记不可用时不阻塞主流程
- 增加降级提示"
```

---

### 任务 7：新建 `references/xunji-bridge.md`

**文件：**
- 创建：`gin-fitness-tracker/references/xunji-bridge.md`

- [ ] **步骤 1：创建标准五章桥接文件**

文件内容：

```markdown
# 讯记技能调用约定（桥接，不直连接口）

> 何时读我：`sync-xunji` 子技能被调用前，以及用户询问讯记同步规则时，必须先读本文件。
> 前提：用户环境中已安装 `xunji-body` / `xunji-food` / `xunji-training` 中至少一个。未安装则降级运行并提醒安装。

## 一、职责边界（禁止越界）

- **讯记 skill 负责**：
  - 从自身数据源（训记 App 等）查询身体/饮食/训练数据
  - 完成鉴权、限频、错误处理
  - 返回结构化数据给本技能
- **本技能（gin-fitness-tracker）负责**：
  - 检测讯记 skill 是否已安装
  - 调用讯记 skill 拉取数据
  - 接收结果后只填充当日空白字段，不覆盖用户主动录入的数据
  - 标记数据来源为「讯记同步」
- **本技能明确不执行**：
  - 不直接调用讯记 App 接口
  - 不存储、不读取、不经手讯记凭证
  - 不代替讯记 skill 写入数据到讯记 App
  - 不在讯记数据缺失时估算或编造

## 二、依赖检测

1. 按技能名检测运行环境中是否已安装以下 skill：
   - `xunji-body`：体重/体脂数据
   - `xunji-food`：饮食数据
   - `xunji-training`：训练数据
2. **已安装** → 调用对应 skill
3. **未安装** → 记录状态、继续运行、告知用户该 skill 未安装

## 三、输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `date` | string | 是 | 目标日期，格式 `YYYY-MM-DD` |
| `data_type` | string | 是 | `body` / `food` / `training` |
| `user_context` | object | 否 | 用户配置中的目标值、碳水循环状态等 |

## 四、输出结果

| 字段名 | 类型 | 存在条件 | 说明 |
|--------|------|----------|------|
| `status` | string | 始终 | `success` / `partial` / `failed` |
| `data` | object | 成功/部分成功时 | 拉取到的数据字段，如 `晨起体重`、`总热量`、`训练内容` |
| `error` | object | 失败时 | `code` + `message` |

## 五、异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| 讯记 skill 未安装 | 不阻塞主流程，返回 `XUNJI_UNAVAILABLE` 错误，提示用户安装 |
| 调用返回失败 | 原样展示错误原因，继续运行，该类型数据需用户手动录入 |
| 讯记数据缺失 | 留空，不估算、不编造 |
| 用户要求操作讯记侧数据 | 引导用户使用讯记 skill，本技能不代劳 |
```

- [ ] **步骤 2：在 `knowledge/xunji-api-guide.md` 顶部增加指针**

在 `knowledge/xunji-api-guide.md` 第一行 `# 讯记 API 规则` 后追加：

```markdown
> 最新标准桥接约定见 `references/xunji-bridge.md`。本文件保留调用时机、数据来源优先级等业务规则参考。
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/references/xunji-bridge.md gin-fitness-tracker/knowledge/xunji-api-guide.md
git commit -m "docs(bridge): 新增 xunji 标准桥接约定

- 按技能桥接模式技术规范 v2.0 五章格式创建 references/xunji-bridge.md
- 明确讯记 skill 与本技能的职责边界、输入输出、异常降级
- xunji-api-guide.md 增加指向桥接文件的指针"
```

---

### 任务 8：新建 `references/lark-sheets-bridge.md`

**文件：**
- 创建：`gin-fitness-tracker/references/lark-sheets-bridge.md`

- [ ] **步骤 1：创建标准五章桥接文件**

文件内容：

```markdown
# lark-sheets（飞书表格）调用约定（桥接，不直连接口）

> 何时读我：任何子技能需要读写飞书表格前，必须先读本文件。
> 前提：用户环境中已安装 `lark-sheets` skill 或 `lark` CLI。未安装则返回 `LARK_SKILL_UNAVAILABLE` 错误。

## 一、职责边界（禁止越界）

- **lark-sheets skill / lark CLI 负责**：
  - 飞书开放接口的鉴权、请求发送、限频控制与重试
  - 返回结果的格式整理与错误信息返回
  - 凭证的存储与管理（在其自身配置中）
- **本技能（gin-fitness-tracker）负责**：
  - 检测 lark-sheets 能力是否可用
  - 构造业务参数（表格 URL、子表名、日期、字段映射等）
  - 接收返回结果并按本技能规则使用与验证（写后复查、截断检测等）
- **本技能明确不执行**：
  - 不直接向飞书开放接口发起网络请求
  - 不存储、不读取、不经手任何飞书凭证（App ID / App Secret / Token 等）
  - 不实现重试逻辑（重试由 lark-sheets 能力内部负责）
  - 不修改 lark-sheets 能力的行为逻辑

## 二、依赖检测

1. 检测环境中 `lark-sheets` skill 是否可用
2. 不可用则检测 `lark` CLI 是否已安装（`command -v lark`）
3. **任一可用** → 继续执行
4. **均不可用** → 返回 `LARK_SKILL_UNAVAILABLE` 错误，提示用户安装

## 三、输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `spreadsheet_url` | string | 是 | 飞书电子表格 URL，来自 `atlas-config.yaml` 的 `fitness.sheets.url` |
| `sheet_name` | string | 是 | 子表名，如 `每日记录`、`字段元数据`、`用户配置` |
| `range` | string | 视模式而定 | 单元格范围，如 `A1:Z1` |
| `fields` | object | 写入时 | `字段名 → 值` 的映射 |
| `date` | string | 查询/写入时 | 格式 `YYYY-MM-DD` |

具体调用模式（verify_spreadsheet / read_header / read_field_metadata / find_date_row / create_date_row / read_column_formats 等）详见 `knowledge/sheets-calling-patterns.md`。

## 四、输出结果

| 字段名 | 类型 | 存在条件 | 说明 |
|--------|------|----------|------|
| `status` | string | 始终 | `success` / `failed` |
| `data` | object/array | 成功时 | 读取到的表头、记录、配置等 |
| `error` | object | 失败时 | `code` + `message` |
| `revision` | string | 写入成功时 | 用于写后复查的证据 |
| `updated_cells_count` | number | 写入成功时 | 写入单元格数 |

## 五、异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| lark-sheets / lark CLI 未安装 | 返回 `LARK_SKILL_UNAVAILABLE`，提示安装 |
| 表格或子表不存在 | 返回 `TABLE_NOT_FOUND`，不自动创建 |
| 写入后复查不一致 | 换工具重试，仍不一致则返回 `FIELD_WRITE_FAILED` |
| 返回字段数量/长度异常 | 标截断风险，降级手动粘贴 |
| 权限错误 | 返回 `TABLE_NOT_FOUND`，提示检查表格权限 |
```

- [ ] **步骤 2：在 `knowledge/sheets-calling-patterns.md` 顶部增加指针**

在第一行 `# 健身追踪 - 飞书表格调用模式` 后追加：

```markdown
> 最新标准桥接约定见 `references/lark-sheets-bridge.md`。本文件保留各模式的具体命令模板与消费方式。
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/references/lark-sheets-bridge.md gin-fitness-tracker/knowledge/sheets-calling-patterns.md
git commit -m "docs(bridge): 新增 lark-sheets 标准桥接约定

- 按技能桥接模式技术规范 v2.0 五章格式创建 references/lark-sheets-bridge.md
- 明确 lark-sheets 与本技能的职责边界、输入输出、异常降级
- sheets-calling-patterns.md 增加指向桥接文件的指针"
```

---

### 任务 9：主 `SKILL.md` 登记桥接文件并更新版本号

**文件：**
- 修改：`gin-fitness-tracker/SKILL.md`

- [ ] **步骤 1：在「数据存储抽象层」章节后登记桥接文件**

在 `## 数据存储抽象层` 章节末尾追加：

```markdown
### 外部技能桥接约定

- 讯记 skill 调用约定 → `references/xunji-bridge.md`
- lark-sheets skill 调用约定 → `references/lark-sheets-bridge.md`
```

- [ ] **步骤 2：更新 frontmatter version**

将第 15 行：

```yaml
version: "v3.3.0"
```

改为：

```yaml
version: "v3.4.0"
```

- [ ] **步骤 3：commit**

```bash
git add gin-fitness-tracker/SKILL.md
git commit -m "docs(gin-fitness-tracker): 登记桥接文件并升级版本号

- 在数据存储抽象层章节登记 xunji-bridge 与 lark-sheets-bridge
- version 从 v3.3.0 升级到 v3.4.0"
```

---

### 任务 10：更新 `CHANGELOG.md`

**文件：**
- 修改：`gin-fitness-tracker/CHANGELOG.md`

- [ ] **步骤 1：在文件顶部追加 v3.4.0 条目**

在 `### v3.3.0 — 2026-08-26` 之前插入：

```markdown
### v3.4.0 — 2026-08-29

**更新类型**：优化

**涉及文件**：
- `SKILL.md`
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/query-data/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `references/xunji-bridge.md`
- `references/lark-sheets-bridge.md`
- `knowledge/xunji-api-guide.md`
- `knowledge/sheets-calling-patterns.md`
- `CHANGELOG.md`

**内容**：

1. **新增 Progress Checklist 使用规则**：主 `SKILL.md` 增加统一规则、场景定位句、标签说明、展示时机与禁止项
2. **5 个子技能执行流程 checklist 化**：init/collect-data/write-verify/query-data/sync-xunji 分别插入 micro-checklist，标注 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]`
3. **硬闸门显性化**：在 collect-data 问题生成前检查单、write-verify 已有值检查、单选项匹配等位置增加 `当前阻塞：等待你确认 XXXX` 提示
4. **新增 `references/xunji-bridge.md`**：按技能桥接模式技术规范 v2.0 五章格式，整合讯记桥接约定
5. **新增 `references/lark-sheets-bridge.md`**：按规范五章格式，收敛飞书表格调用契约
6. **知识库文件增加桥接指针**：`xunji-api-guide.md` 与 `sheets-calling-patterns.md` 顶部增加指向新桥接文件的说明
7. **版本号升级**：`SKILL.md` frontmatter version 从 `v3.3.0` 升级到 `v3.4.0`

---
```

- [ ] **步骤 2：commit**

```bash
git add gin-fitness-tracker/CHANGELOG.md
git commit -m "chore(gin-fitness-tracker): 更新日志记录 v3.4.0 优化

- 新增 Progress Checklist 与标准桥接文件条目
- 记录 5 个子技能 checklist 化与硬闸门显性化"
```

---

### 任务 11：验证文档一致性与渲染

**文件：**
- 涉及：`gin-fitness-tracker/SKILL.md`、`gin-fitness-tracker/skills/*/*.md`、`gin-fitness-tracker/references/*.md`、`gin-fitness-tracker/knowledge/*.md`

- [ ] **步骤 1：全局搜索 Progress 相关关键词**

```bash
cd gin-fitness-tracker
grep -R "^Progress:" SKILL.md skills/ references/ | wc -l
grep -R "当前场景：gin-fitness-tracker" SKILL.md skills/ | wc -l
```

预期：`Progress:` 标题 6 处（主 SKILL + 5 个子技能）；场景定位句 6 处。

- [ ] **步骤 2：检查每个 micro-checklist 是否包含标签**

```bash
grep -R "^- \[ \] Step" SKILL.md skills/ | grep -vE '\[(自动|需确认|硬闸门|可回环)\]' || echo "All steps have tags"
```

- [ ] **步骤 3：检查硬闸门后是否有阻塞提示**

```bash
grep -R "当前阻塞：等待你确认" SKILL.md skills/ | wc -l
```

预期至少 4 处（collect-data 检查单、write-verify 已有值、write-verify 单选项、sync-xunji 降级提示）。

- [ ] **步骤 4：验证桥接文件五章齐全**

```bash
grep -E "^## [一二三四五]、" references/xunji-bridge.md
grep -E "^## [一二三四五]、" references/lark-sheets-bridge.md
```

预期各输出 5 行。

- [ ] **步骤 5：验证版本号一致**

```bash
grep "version:" SKILL.md
head -20 CHANGELOG.md | grep "v3.4.0"
```

- [ ] **步骤 6：commit**

```bash
git add -A
git commit -m "chore(gin-fitness-tracker): Progress Checklist 与桥接规范一致性检查

- 确认 Progress 标题、场景定位句、标签、阻塞提示统一
- 确认 xunji-bridge 与 lark-sheets-bridge 五章齐全
- 确认版本号 v3.4.0 已同步"
```

---

## 自检

**1. 规格覆盖度：**
- ✅ 主 SKILL.md 统一 Progress 规则
- ✅ 5 个子技能 micro-checklist
- ✅ 硬闸门 / 可回环标签
- ✅ 阻塞提示话术
- ✅ `references/xunji-bridge.md` 标准五章
- ✅ `references/lark-sheets-bridge.md` 标准五章
- ✅ 知识库文件桥接指针
- ✅ CHANGELOG 更新
- ✅ version 升级到 v3.4.0
- ✅ 一致性检查

**2. 占位符扫描：**
- 无 "TODO"、"待定"、"后续实现"
- 每个步骤都有具体插入位置和文案

**3. 类型一致性：**
- 统一使用 "当前场景：gin-fitness-tracker — [子模块名]"
- 统一使用 `Progress:` 标题
- 统一使用 `- [ ] Step N 动作 [标签]` 格式
- 桥接文件统一使用规范五章格式

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-08-29-gin-fitness-tracker-optimization-plan.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
