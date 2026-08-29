---
# 健身追踪 - 飞书表格调用模式
# 由主技能 gin-fitness-tracker 在内部调用 lark-sheets skill 时使用
# 本文件定义健身追踪与飞书表格之间的调用契约
---

# 健身追踪 - 飞书表格调用模式

> 最新标准桥接约定见 `references/lark-sheets-bridge.md`。本文件保留各模式的具体命令模板与消费方式。

所有对飞书表格的访问必须通过 `Skill(skill="lark-sheets")` 发起，且必须附带本文件中定义的完整命令模板。禁止向 `lark-sheets` 传递模糊请求（如"读取表头行"）。

---

### 模式 1：verify_spreadsheet — 验证表格和子表存在

**用途：** `init` 子技能初始化时确认目标表格和子表存在且可读写。

**命令：**
```bash
lark-cli sheets +workbook-info --url "<fitness.sheets.url>" --format json
```

**输入参数：**
- `fitness.sheets.url`：电子表格 URL

**期望返回：** `sheets[]` 列表，包含 `sheet_name` 和 `sheet_id`

**消费方式：**
- 检查 `每日记录`、`字段元数据`、`用户配置` 是否都在 `sheets[].sheet_name` 中
- 任一不存在 → 返回 `TABLE_NOT_FOUND`，不自动创建

---

### 模式 2：read_header — 读任意子表表头行

**用途：** 建立「字段名 → 列字母」映射。

**命令：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "<sheet_name>" --range "A1:<LAST_COL>1" --format json
```

**输入参数：**
- `fitness.sheets.url`
- `sheet_name`：子表名（如 `每日记录`、`用户配置`）
- `LAST_COL`：运行时表头行最右列字母。首次读取时若未知，可先读 `A1:Z1` 拿到实际范围，再用返回的 `col_indices[-1]` 作为后续调用的 `<LAST_COL>`；也可以直接省略 `--range` 读取整个子表，由返回的 `actual_range` 确定表宽。

**期望返回：** `annotated_csv` 中的第一行表头内容，`col_indices[]`

**消费方式：**
- 解析 CSV 得到字段名数组
- 用 `col_indices[i]` 得到每个字段名对应的列字母
- 用 `col_indices[-1]` 得到最右列字母，作为后续 `verify_row_values`、`read_column_formats` 等调用的 `<LAST_COL>`

**注意：** 读取前先用 `+workbook-info` 确认子表存在；读取范围**必须以运行时表宽为准**，禁止硬编码列数。当前表格可能是 43 列，但用户可能增删列。

---

### 模式 3：read_field_metadata — 读字段元数据子表

**用途：** 获取每个字段的时段、类型、写入方、选项、填写说明。

**命令：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "字段元数据" --range "A1:F50" --format json
```

**输入参数：**
- `fitness.sheets.url`

**期望返回：** 字段元数据表格内容

**消费方式：**
- 构建 `字段名 → {时段, 类型, 写入方, 选项, 填写说明}` 映射
- 识别公式字段：`写入方 = Sheets` 或 `类型 = 公式`
- 识别单选/多选字段及其合法选项

---

### 模式 4：read_user_config — 读用户配置子表

**用途：** 获取用户目标、阶段、碳水循环等配置。

**命令：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "用户配置" --range "A2:B50" --format json
```

**输入参数：**
- `fitness.sheets.url`

**期望返回：** 配置项→值 的键值对

**消费方式：**
- 建立 `配置选项 → 值` 映射
- 用于目标展示、BMI 计算、碳水循环判断

---

### 模式 5：find_date_row — 按日期找行号

**用途：** 在 `每日记录` 表中定位某日期所在行。

**命令：**
```bash
lark-cli sheets +cells-search --url "<fitness.sheets.url>" --sheet-name "每日记录" --find "<date>" --format json
```

**输入参数：**
- `fitness.sheets.url`
- `date`：格式 `YYYY-MM-DD`

**期望返回：** 匹配单元格地址，如 `A101`

**消费方式：**
- 从地址提取行号
- 无匹配 → 日期行不存在，进入 `create_date_row`

**何时用 search，何时用 read_date_column：**
- 只查一个日期：用本模式（`+cells-search`）最快。
- 查多个日期（如本周 7 天、补录一段历史）：先用模式 11 `read_date_column` 读整列 A 建立 `日期 → 行号` 映射，再本地查表。这样可以避免 7 次 search API 调用。

---

### 模式 6：read_dropdown_options — 读字段下拉选项

**用途：** 写入单选/多选字段前，获取真实合法选项列表。

**命令：**
```bash
lark-cli sheets +dropdown-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "<col>2" --format json
```

**输入参数：**
- `fitness.sheets.url`
- `col`：字段所在列字母（来自 `read_header`）

**期望返回：** `data_validation.items` 数组

**消费方式：**
- 将用户语义映射到某个 `item`
- 映射失败 → 返回 `INVALID_OPTION`，列出全部 items
- 一律禁止新建选项

---

### 模式 7：create_date_row — 日期行不存在时插入新行

**用途：** `collect-data` 发现日期行不存在时，按日期升序插入新行并填入日期。

**命令：**
```bash
lark-cli sheets +cells-set --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A<row>" --cells '[[{"value":"<date>"}]]'
```

**输入参数：**
- `fitness.sheets.url`
- `row`：应插入的行号（按日期升序计算得出）
- `date`：格式 `YYYY-MM-DD`

**期望返回：** `ok: true`

**消费方式：**
- 确认日期写入后，继续 `write_fields_by_name`

**注意：** 健身追踪不创建子表，只在已有 `每日记录` 子表内插入数据行。

---

### 模式 8：write_fields_by_name — 按字段名映射写入单元格

**用途：** 把字段名→值映射写入指定日期行的对应列。

**前提：** 必须先完成 `read_header` 和 `read_column_formats`，得到 `header_map` 和 `column_constraints`，并根据约束完成值转换。

**步骤：**
1. 健身追踪内部根据 `read_header` 得到的映射，把字段名转换成列字母
2. 根据 `read_column_formats` 得到的 `column_constraints`，把原始值转换为符合列格式/验证的值
3. 构造 `+cells-set` 的 `--writes` 批量写入请求
4. 调用 `lark-sheets` skill 执行

**命令：**
```bash
lark-cli sheets +cells-set --url "<fitness.sheets.url>" --sheet-name "每日记录" --writes - <<'JSON'
{
  "writes": [
    {"sheet_name": "每日记录", "range": "C<row>:C<row>", "cells": [[{"value": 67.65}]]},
    {"sheet_name": "每日记录", "range": "D<row>:D<row>", "cells": [[{"value": 21.6}]]}
  ]
}
JSON
```

**输入参数：**
- `fitness.sheets.url`
- `row`：目标日期行号
- `fields`：字段名→值 映射
- `header_map`：字段名→列字母 映射

**期望返回：** `ok: true`

**消费方式：**
- 请求被接受后，必须调用 `verify_row_values` 回读校验

---

### 模式 9：verify_row_values — 回读整行校验

**用途：** 写入后读取整行，对比写入值是否真实生效。

**命令：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A<row>:<LAST_COL><row>" --format json
```

**输入参数：**
- `fitness.sheets.url`
- `row`：目标日期行号
- `LAST_COL`：表头行最右列字母，来自 `read_header` 返回的 `col_indices[-1]`

**期望返回：** 整行字段值

**消费方式：**
- 按 `header_map` 核对每个写入字段的实际值
- 一致 → 字段写入成功
- 不一致 → 换工具/换方式重试一次，仍不一致 → `FIELD_WRITE_FAILED`

**大表读取：** 如果整行数据量较大，可能触及 `--max-chars` 默认 500k 上限。此时改用 `--output-path ./verify-row.json`，上限自动提升到 20M，stdout 只返回摘要。Agent 从文件中读取 JSON 后再核对。

---

### 模式 10：read_column_formats — 读取列格式与数据验证

**用途：** 写入前一次性读取每列的真实 `number_format` 和 `data_validation`，作为值转换和校验的权威依据。替代原来逐列调用的 `read_dropdown_options`。

**命令：**
```bash
lark-cli sheets +cells-get \
  --url "<fitness.sheets.url>" \
  --sheet-name "每日记录" \
  --range "A2:<LAST_COL>2" \
  --include style,data_validation \
  --format json
```

**输入参数：**
- `fitness.sheets.url`
- `<LAST_COL>`：表头行最右侧列字母，来自 `read_header` 返回的 `col_indices[-1]`

**期望返回：** 第 2 行每个单元格的 `cell_styles.number_format` 和 `data_validation.items`

**消费方式：**
- 建立 `列字母 → {number_format, data_validation_items}` 映射
- 写入前据此转换原始值：
  - `number_format` 含 `%` 且原始值以 `%` 结尾 → 除以 100
  - `number_format` 为时间格式（如 `h:mm`）且原始值为 `HH:mm` → 转为 Excel 时间小数
  - `data_validation.items` 存在 → 值必须在列表中，否则 `INVALID_OPTION`
  - `number_format` 为数字格式 → 转为 float
  - 其他 → 字符串
- 字段元数据子表仅作为语义参考，真实格式/验证以本调用返回为准

**示例返回片段：**
```json
{
  "cells": [[
    {"cell_styles": {"number_format": "0.00%"}, "value": "24.00%"},
    {"cell_styles": {"number_format": "h:mm"}, "value": "0:00"},
    {"data_validation": {"items": ["🟢有力", "🟢正常", "🔴无力"]}, "value": null}
  ]]
}
```

---

### 模式 11：read_date_column — 读取日期列建立日期→行号映射

**用途：** 替代反复调用 `find_date_row`（`+cells-search`），一次性读取整个日期列，在本地建立「日期 → 行号」映射。

**命令：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A2:<LAST_COL_DATE>" --format json
```

**输入参数：**
- `fitness.sheets.url`
- `LAST_COL_DATE`：日期列实际末行号。若不确定，可先读 `A2:A1000` 或更大范围；返回的 `annotated_csv` 每行自带 `[row=N]` 前缀，空行也会返回，可据此确定实际末行。更好的做法是先调用一次 `+csv-get --range A2:A`（省略结束行）读取整列，但为保险起见建议传一个足够大的上限如 `A2:A5000`，并用 `--output-path` 避免大表截断。

**期望返回：** 日期列所有单元格，`annotated_csv` 每行前缀 `[row=N]` 即为实际行号

**消费方式：**
- 建立 `日期 → 行号` 映射
- 查询本周/上周数据时，用该映射一次性定位多个日期行，再批量读取目标行
- 找不到的日期 → 记录为缺失，进入 `create_date_row`

**与 `find_date_row` 的选择：**
- 只查一个日期：`+cells-search` 更快
- 查多个日期（如本周 7 天）：优先用本模式读整列，再本地查表

---

### 模式 12：read_specific_columns — 精确读取少数列

**用途：** 当只需要 1-3 个字段（如只看体重、体脂）时，按列精确读取，避免读整行。

**命令（CSV 形态，只看值）：**
```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "<COL>2:<COL><LAST_ROW>" --format json
```

**命令（Cells 形态，需要公式/样式/验证）：**
```bash
lark-cli sheets +cells-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "<COL>2:<COL><LAST_ROW>" --include value,formula,style,comment,data_validation --format json
```

**输入参数：**
- `fitness.sheets.url`
- `COL`：目标列字母（来自 `header_map`）
- `LAST_ROW`：实际末行号。不确定时可传一个足够大的值（如 5000），返回的空行可过滤掉

**期望返回：** 单列数据

**消费方式：**
- 按 `header_map` 把字段名转成列字母
- 对每列独立调用，或合并为一个 `+csv-get` / `+cells-get` 连续 range（如 `C2:C5000` 只读体重列）
- 需要同时读多列但不连续时，必须分多次调用，因为 `+csv-get` / `+cells-get` 的 `--range` 只接受单个 A1 range

**大表读取：** 单列数据量大时同样建议加 `--output-path ./col-data.json`。

---

### 模式 13：read_with_output_path — 大表读取兜底

**用途：** 当任何读取命令可能超过 500k 字符默认上限时使用。

**做法：** 在 `+csv-get` 或 `+cells-get` 后追加 `--output-path ./lark-read-<timestamp>.json`。

**效果：**
- 字符上限自动提升到约 20M
- 文件内容是标准 JSON payload，与 stdout 返回结构一致
- stdout 只返回 `output_path`、`byte_count`、`complete`/`truncated` 等摘要
- Agent 从文件中读取并解析，而不是直接解析 stdout

**注意：** 临时文件应放在系统临时目录（如 `/tmp`），不要写入项目目录或用户工作目录；读取后应及时清理。
