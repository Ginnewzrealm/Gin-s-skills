---
# 健身追踪 - 初始化模块
# 由主技能 jian-shen-zhui-zong 在内部调用，不独立触发
---

# 健身追踪 - 初始化子技能

## 职责

- 检查 `atlas-config.yaml` 配置
- 检查数据存储是否可读写
- 检查 `lark-sheets` skill 是否可用
- 检测每日记录表是否存在
- 检测用户配置表是否存在，不存在则返回 TABLE_NOT_FOUND 错误，不自动创建
- 初始化必填配置

## 执行流程

```
技能被触发
    ↓
① 发送模块状态反馈：🔧 正在执行初始化：检查配置与数据连接...
    ↓
② 读取 atlas-config.yaml，确定使用哪个存储后端
    ↓ 无法读取 → 默认使用 feishu_sheets，并提示用户后续可配置
③ 根据后端选择/推断结果，加载对应的 skill
    ↓ lark-sheets / 无（本地后端）
④ 检查数据存储是否可读写（飞书表/JSON目录/Obsidian Vault）
    ↓ 不可用 → 返回 TABLE_NOT_FOUND 或 CONFIG_MISSING 错误
⑤ 检测每日记录表是否存在，不存在则返回 TABLE_NOT_FOUND 错误，不自动创建
⑥ 检测用户配置表是否存在，不存在则返回 TABLE_NOT_FOUND 错误，不自动创建
⑦ 通过全部检查 → 返回初始化完成
```

## 返回格式

```json
{
  "status": "success" | "partial" | "failed",
  "module": "init",
  "message": "✅ 健身追踪技能初始化完成。当前配置：飞书Sheets；每日记录表：已连接；用户配置表：已连接。",
  "data": {
    "storage_backend": "feishu_sheets",
    "daily_table_ready": true,
    "config_table_ready": true
  },
  "errors": []
}
```

## 步骤详解

### 步骤1：发送模块状态反馈

发送：`🔧 正在执行初始化：检查配置与数据连接...`

### 步骤2：读取 atlas-config.yaml 并确定后端

1. 尝试读取 `~/.atlas/atlas-config.yaml`
2. 如果存在 `fitness.backend`，按其值选择后端
3. 如果不存在，按以下顺序推断：
   - 存在 `fitness.sheets.spreadsheet_token` → `feishu_sheets`
   - 否则默认 `feishu_sheets`
4. 如果配置为空或不存在，使用默认 `feishu_sheets`，并提示用户后续可配置

### 步骤3：加载对应后端 skill

| 后端 | 加载 skill | 检查内容 |
|------|-----------|---------|
| `feishu_sheets` | `Skill(skill="lark-sheets")` | 调用 `verify_spreadsheet` 模式验证 spreadsheet 和子表存在 |
| `local_json` | 无 | 检查目录可读写 |
| `obsidian` | 无 | 检查 Vault 路径可读写 |

若所选后端依赖的 skill 不可用，返回 `LARK_SKILL_UNAVAILABLE` 错误。

### 步骤4：检查数据存储

**飞书 Sheets 方案**：
1. 调用 `lark-sheets` skill 的 `verify_spreadsheet` 模式：

   ```bash
   lark-cli sheets +workbook-info --url "<fitness.sheets.url>" --format json
   ```

   检查返回的 `sheets[].sheet_name` 中是否包含 `每日记录`、`字段元数据`、`用户配置`。任一缺失返回 `TABLE_NOT_FOUND`。
2. 如果返回权限错误，返回 `TABLE_NOT_FOUND` 错误

**local_json 方案**：
1. 检查配置的目录是否存在
2. 检查目录是否可写

**obsidian 方案**：
1. 检查 Vault 路径是否存在
2. 检查目标文件夹是否可写

### 步骤5：检测每日记录表

**Sheets**：
1. 调用 `lark-sheets` skill 的 `read_header` 模式读取 `daily_sheet_name` 表头
   （表名与表头行范围定义见 `config/sheets-schema.md` 的「每日记录子表」章节）：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A1:AQ1" --format json
   ```

2. **成功** → 子表存在
3. **失败（子表不存在）** → 返回 `TABLE_NOT_FOUND` 错误

**注意**：每日记录表采用**自动按日期升序创建行**模式。日期行由 `collect-data` / `write-verify` 在写入时按需自动插入，无需用户手动创建。

### 步骤5.5：检测字段元数据子表

**Sheets**：
1. 调用 `lark-sheets` skill 的 `read_field_metadata` 模式读取 `field_metadata_sheet_name`（默认 `字段元数据`）
   （表名与范围定义见 `config/sheets-schema.md` 的「字段元数据子表」章节）：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "字段元数据" --range "A1:F50" --format json
   ```

2. **成功** → 子表存在，检查表头完整性（字段名、时段、类型、写入方、选项、填写说明）
3. **失败** → 返回 `TABLE_NOT_FOUND` 错误，不自动创建

**字段元数据一致性抽查（初始化时执行一次）**：
1. 从字段元数据中选取 3-5 个单选/多选字段
2. 对每个字段调用 `read_dropdown_options` 模式读取真实下拉选项：

   ```bash
   lark-cli sheets +dropdown-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "<col>2" --format json
   ```

3. 对比字段元数据中的「选项」列与真实下拉选项
4. 不一致 → 在初始化结果中返回 warning，提示用户检查表格字段配置，但不阻塞初始化

字段元数据子表用于统一约束 Agent 填写行为。若子表为空或缺失部分字段，运行时回退到字段名模式匹配。

### 步骤6：检测用户配置表

**Sheets**：
1. 调用 `lark-sheets` skill 的 `read_user_config` 模式读取 `config_sheet_name`
   （表名与范围定义见 `config/sheets-schema.md` 的「用户配置子表」章节）：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "用户配置" --range "A2:B50" --format json
   ```

2. **成功** → 子表存在，检查表头完整性
3. **失败** → 返回 `TABLE_NOT_FOUND` 错误，不自动创建

用户配置表用于存储目标阶段、热量、营养目标、身高、当前体重/体脂等。若表为空，后续写入时会按需创建配置行。

**初始化必填配置**：

| 配置选项 | 类型 | 是否必填 |
|---------|------|---------|
| 目标阶段 | 文本 | ✅ |
| TDEE | 文本 | ✅ |
| 目标热量 | 文本 | ✅ |
| 蛋白目标 | 文本 | ✅ |
| 脂肪目标 | 文本 | ✅ |
| 碳水目标 | 文本 | ✅ |
| 当前体重 | 文本 | ✅ |
| 当前体脂 | 文本 | ✅ |
| 身高 | 文本 | ✅ |

如果配置缺失，返回 `CONFIG_MISSING` 错误，提示用户运行健身规划技能或手动填写。

### 步骤7：初始化完成

返回成功结果：

```json
{
  "status": "success",
  "module": "init",
  "message": "✅ 健身追踪技能初始化完成。当前配置：飞书Sheets；每日记录表：已连接；用户配置表：已连接；字段元数据表：已连接；lark-sheets：已就位。下一步：请运行\"健身追踪\"开始日常记录。",
  "data": {},
  "errors": []
}
```

## 讯记 skill 检测（可选）

按技能名检测运行环境中是否已安装以下外部独立 skill（不在本技能包内查找其文件）：
1. `xunji-body`（体重/体脂）
2. `xunji-food`（饮食数据）
3. `xunji-training`（训练数据）

已安装 → 在 `message` 中告知就位（如"检测到 xunji-training，训练数据同步已就位"）；未安装 → 在 `data` 中记录并提示安装。**初始化不因此中断，其余功能照常。**

注意：初始化检测只用于告知就位状态；实际同步时由 sync-xunji 现场重新检测，不依赖本环节的一次性结论。

未安装时的提示模板：

```
⚠️ 讯记同步不可用：xunji-training skill 未安装
原因：对应讯记 skill 未安装
操作：如需训练数据自动同步，请安装 xunji-training skill
影响：本 skill 继续运行，该类型数据需用户手动录入
```
