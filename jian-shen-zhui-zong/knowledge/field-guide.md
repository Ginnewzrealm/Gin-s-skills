# 字段填写说明

## 核心原则：动态字段读取

**本技能不硬编码任何字段名。每次操作前必须先读取实时字段定义。**

## 读取字段定义

**本技能不硬编码任何字段名。每次操作前必须先读取实时字段定义。**

Sheets 后端读取方式：

- **Sheets 后端**：调用 `lark-sheets` skill 的 `read_header` 模式读取表头行：

  ```bash
  lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A1:AQ1" --format json
  ```

  返回 `annotated_csv` 和 `col_indices`，建立「字段名 → 列字母」映射。
- **local_json / obsidian**：直接读取文件中的字段键

**通用规则**：
- 查询模式允许复用已读取的完整字段清单
- **禁止自行挑选字段子集读取**：不得以判断只读取部分字段
- 写入前必须重新读取字段定义，以实时返回的字段名组织写入内容
- 单选/多选字段必须校验选项存在

## 字段来源唯一权威

**所有字段名必须以运行时读取的表头行字段全集为唯一来源。**

本技能不硬编码任何字段名，也不允许 Agent 凭任何其他来源构造字段名。

### 禁止的字段来源

以下来源一律无效，使用即视为编造字段：

- ❌ 凭记忆、印象或"常见健身字段"构造字段名（如"下午茶时间"、"下午茶感觉"）
- ❌ 从示例、模板、历史对话、训练数据中提取字段名
- ❌ 为"补全"、"美化"或"让用户多填点"而想象字段名
- ❌ 用字段语义推断字段名（如"既然有早餐，就该有下午茶"）
- ❌ 从字段元数据子表之外的任何文档复制字段名

### 唯一合法的字段来源

- ✅ 调用 `read_header` 模式读取的表头行数组
- ✅ 调用 `read_field_metadata` 模式读取的「字段名」列

### 执行原则

1. **生成问题前**：必须先 `read_header`，问题只能从返回的字段名数组中筛选。
2. **展示数据前**：`raw_record` 的键必须 100% 来自表头行字段名，不得补全不存在的字段。
3. **写入数据前**：必须再次 `read_header`，以实时字段名组织写入内容；写入请求中的字段名若不在表头行中，立即返回 `FIELD_NOT_FOUND`。
4. **字段不存在时**：不猜测、不替代、不补全，直接跳过或报错。

### 为什么这是红线

飞书表格的真实字段由用户在表格中定义。Agent 编造字段名会导致：
- 向用户询问不存在的字段，浪费交互
- 把数据写入不存在的列，造成写失败或写错列
- 污染表格结构（若某些写入方式会自动创建列/选项）
- 让用户对 Agent 的可信度产生怀疑

---

## DataStore 接口实现指南

**重要**：DataStore 接口由 AI 按照以下指南"实现"执行，不需要预先写好的代码。所有飞书相关操作均通过 `Skill(skill="lark-sheets")` 委托给 `lark-sheets` skill 执行。调用时必须附带 `knowledge/sheets-calling-patterns.md` 中定义的完整命令模板，禁止只传模糊意图。健身追踪内部负责字段名→列字母映射、字段类型校验、单选选项匹配等业务逻辑；`lark-sheets` skill 负责执行具体 CLI 命令。

### FeishuSheetsStore 实现方式

**getUserConfig() 实现步骤**：
1. 读取 atlas-config.yaml 获取 `fitness.sheets.url` 和 `fitness.sheets.config_sheet_name`
2. 调用 `lark-sheets` skill 的 `read_user_config` 模式读取「用户配置」子表：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "用户配置" --range "A2:B50" --format json
   ```

3. 解析每行的"配置选项"和"值"列
4. 返回 `{ 配置项: 值 }` 映射

**writeDailyRecord(date, fields) 实现步骤**：
1. 调用 `lark-sheets` skill 的 `find_date_row` 模式在「每日记录」子表的日期列中查找 `date`：

   ```bash
   lark-cli sheets +cells-search --url "<fitness.sheets.url>" --sheet-name "每日记录" --find "<date>" --format json
   ```

2. **行不存在** → 调用 `create_date_row` 模式按日期升序插入新行：

   ```bash
   lark-cli sheets +cells-set --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A<row>" --cells '[[{"value":"<date>"}]]'
   ```

3. **行存在** → 先调用 `read_header` 与 `read_column_formats` 获取字段名→列字母映射和列真实约束，再调用 `write_fields_by_name` 模式更新该行对应字段列的单元格
4. 调用 `verify_row_values` 模式回读该行，对比写入值

**updateUserConfig(changes) 实现步骤**：
1. 调用 `lark-sheets` skill 的 `read_user_config` 模式读取「用户配置」子表全部数据
2. 遍历 changes 中的每个字段，在本地查找"配置选项"等于字段名的行
3. 调用 `write_fields_by_name` 模式更新该行的"值"列

### 子技能写入入口约束

`collect-data`、`query-data`、`init` 等子技能**不直接调用** `DataStore.writeDailyRecord()` 或 `DataStore.updateUserConfig()`。所有写入必须经过 `write-verify` 子技能统一入口，由 `write-verify` 完成字段校验、单选匹配、公式字段跳过、写入后回读验证，再委托给 `lark-sheets` skill 执行具体 CLI。

### LocalJsonStore 实现方式

存储目录下的 JSON 文件：
- `daily_records/<date>.json` — 每日记录
- `user_config.json` — 用户配置

直接读写 JSON 文件，无需 lark-cli。

**配置**：在 `atlas-config.yaml` 中指定目录路径：
```yaml
storage:
  backend: local_json
  path: /home/user/fitness-data
```

### ObsidianStore 实现方式

存储在 Obsidian Vault 的指定目录下：
- `<vault>/fitness/daily_records/<date>.md` — 每日记录（Markdown格式）
- `<vault>/fitness/user_config.json` — 用户配置

**配置**：在 `atlas-config.yaml` 中指定 Vault 路径：
```yaml
storage:
  backend: obsidian
  vault: /home/user/Documents/Obsidian/Vault
  folder: fitness
```

直接读写 Markdown/JSON 文件，无需 lark-cli。

## 字段处理规则

| 字段类型 | 读取 | 写入 |
|---------|------|------|
| 数字字段 | 解析数值 | Agent 传数字（整数/小数），由表格 `number_format` 控制显示小数位 |
| 时间字段 | 解析为时间字符串 | Agent 可传 `HH:mm` 字符串；`coerce_value.py` 根据 `number_format`（如 `h:mm`）自动转为 Excel 时间小数 |
| 百分比字段 | 解析为百分比字符串 | Agent 可传 `21.9%` 或 `0.219`；`coerce_value.py` 根据 `number_format` 含 `%` 自动处理 |
| 单选字段 | 解析选项文本 | **不是写，是选**：写入值必须从真实下拉选项中**原样复制**，禁止任何改写、缩写、同义词替换、emoji 增减 |
| 多选字段 | 解析选项数组 | **不是写，是选**：每个元素必须是选项列表原文 |
| 日期字段 | 解析 YYYY-MM-DD | 格式化为 YYYY-MM-DD |
| 公式字段 | 读取计算结果 | **Agent 不写入公式字段**（周编号、睡眠时长、腰臀比、早晚体重差由 Sheets 公式自动计算） |
| BMI | 读取静态数值 | **Agent 根据用户身高和晨起体重计算后写入静态数值**，不使用公式 |

**真实转换的唯一权威：**
- 写入前调用 `lark-sheets` skill 的 `read_column_formats` 模式一次性读取每列的 `number_format` 和 `data_validation`
- `coerce_value.py` 根据这些真实约束把原始值转为 Sheets 可接受的值
- 字段元数据子表中的「类型」列仅作为语义提示，当元数据与真实表格不一致时，以 `read_column_formats` 结果为准

**选项来源（Sheets 后端）**：
- 优先调用 `lark-sheets` skill 的 `read_column_formats` 模式一次性读取全部列的数据验证：

  ```bash
  lark-cli sheets +cells-get \
    --url "<fitness.sheets.url>" \
    --sheet-name "每日记录" \
    --range "A2:<LAST_COL>2" \
    --include style,data_validation \
    --format json
  ```

- 字段元数据子表中的「选项」列仅作为参考和兜底

## 写入失败与降级

DataStore 写入后必须回读验证。若回读不一致：

1. 首先由被委托的 skill（`lark-sheets`）在其内部尝试换工具/换方式重试
2. 重试后仍不一致 → 返回 `FIELD_WRITE_FAILED` 错误
3. 告知用户手动检查目标表，不阻塞其他字段的写入

## 常见执行错误（注意事项）

以下错误在真实执行中发生过，必须避免：

### 错误1：读取时自行挑选字段子集

- ❌ 错误做法：读取数据时凭判断只指定部分字段（如只读 8 个字段）
- 后果：数据漏读，后续分析与展示基于不完整数据
- ✅ 正确做法：读取记录前先通过对应 skill 获取字段全集；不得自行传字段子集参数

### 错误2：凭记忆中的字段名/顺序写入

- ❌ 错误做法：不重新读取字段定义，凭记忆组织字段映射写入
- 后果：字段名或结构与飞书实际表不一致，数据写错字段
- ✅ 正确做法：写入前必须重新读取字段定义，以其实时返回的字段名组织写入内容

### 错误3：按位置/顺序构造写入内容

- ❌ 错误做法：把字段值按数组顺序拼接写入
- 后果：值被写入错误的字段
- ✅ 正确做法：写入内容必须组织为"字段名→值"键值对，通过对应 skill 按字段映射写入

### 错误4：把语义理解的结果直接写入单选字段

- ❌ 错误做法：用户自然语言报数（如"今天感觉挺好"），AI 把自己理解的措辞（"挺好"）直接写入单选字段
- 后果：飞书多维表格 API 对不存在的选项值会**静默自动创建新选项**，不报错、返回成功——选项列表被污染，且写入值 vs 读回值的常规复查检测不到
- ✅ 正确做法：语义理解只用于「选」，不用于「写」。写入值必须从字段定义返回的选项列表中原样复制（含 emoji、空格、大小写）；映射不上任何已有选项时停止写入并让用户从现有选项中选择。一律禁止新建选项，新增选项只能由用户在飞书字段设置中手动添加。详见 skills/write-verify/SKILL.md「单选/多选字段选项防污染（三锁）」

### 错误5：Agent 向公式字段写入值

- ❌ 错误做法：把用户输入或计算值写入"周编号"、"睡眠时长"、"腰臀比"、"早晚体重差"等公式列
- 后果：覆盖 Sheets 公式，导致后续无法自动计算
- ✅ 正确做法：这些字段由 Sheets 公式自动计算，Agent 只写入其依赖字段（日期、入睡时间、起床时间、腰围、臀围、睡前体重、晨起体重）

### 错误6：用公式计算 BMI

- ❌ 错误做法：在 Sheets 中把 BMI 设为公式列
- 后果：用户身高变更后历史 BMI 会被统一重算，不符合"按当日记录静态保存"的需求
- ✅ 正确做法：BMI 由 Agent 根据用户身高和当日晨起体重计算后写入静态数值
