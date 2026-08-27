---
# PDCA 减脂分析 - 飞书表格调用模式
# 由 pdca-jianzhi 在内部调用 lark-sheets skill 时使用
# 本文件定义 PDCA 减脂分析与飞书表格之间的调用契约
---

# PDCA 减脂分析 - 飞书表格调用模式

所有对飞书表格的访问必须通过 `Skill(skill="lark-sheets")` 发起，且必须附带本文件中定义的完整命令模板。禁止向 `lark-sheets` 传递模糊请求（如"读取表头行"）。

配置来源：本技能目录下的 `config.json`，关键字段：
- `spreadsheet_url`：电子表格 URL
- `daily_sheet_name`：每日数据子表名（默认"每日记录"）
- `pdca_sheet_name`：PDCA 输出子表名（默认"PDCA减脂分析"）

---

## 模式 1：verify_spreadsheet — 验证表格和子表存在

**用途：** `pdca-init` 初始化时确认目标表格和两个子表存在且可读写。

**命令：**
```bash
lark-cli sheets +workbook-info --url "<pdca.sheets.url>" --format json
```

**输入参数：**
- `pdca.sheets.url`：电子表格 URL（来自 `config.json.spreadsheet_url`）

**期望返回：** `sheets[]` 列表，包含 `sheet_name` 和 `sheet_id`

**消费方式：**
- 检查 `daily_sheet_name` 和 `pdca_sheet_name` 是否都在 `sheets[].sheet_name` 中
- 任一不存在 → 返回 `TABLE_NOT_FOUND`，不自动创建

---

## 模式 2：read_header — 读任意子表表头行

**用途：** 建立「字段名 → 列字母」映射。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<sheet_name>" --range "A1:<LAST_COL>1" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `sheet_name`：子表名
- `LAST_COL`：运行时表头行最右列字母。首次读取时若未知，可先读 `A1:Z1` 拿到实际范围，再用返回的 `col_indices[-1]` 作为后续调用的 `<LAST_COL>`；也可以直接省略 `--range` 读取整个子表，由返回的 `actual_range` 确定表宽。

**期望返回：** `annotated_csv` 中的第一行表头内容，`col_indices[]`

**消费方式：**
- 解析 CSV 得到字段名数组
- 用 `col_indices[i]` 得到每个字段名对应的列字母
- 用 `col_indices[-1]` 得到最右列字母，作为后续 `read_daily_rows`、`verify_row_values`、`read_column_formats` 等调用的 `<LAST_COL>`
- 读取前先用 `verify_spreadsheet` 确认子表存在
- 读取范围**必须以运行时表宽为准**，禁止硬编码列数。当前「每日记录」表可能是 43 列，但用户可能增删列；「PDCA减脂分析」表也可能从 12 列扩展。

---

## 模式 3：read_date_column — 读取日期列以定位行号

**用途：** 在「每日记录」中一次性获取所有已有日期及其行号。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.daily_sheet_name>" --range "A2:<LAST_ROW>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `LAST_ROW`：实际末行号。若不确定，可先调用一次 `+csv-get --range A2:A5000`（或更大范围）；返回的 `annotated_csv` 每行自带 `[row=N]` 前缀，空行也会返回，可据此确定真实末行。数据量大时建议加 `--output-path ./date-column.json`，把 500k 默认上限提升到约 20M。

**期望返回：** 日期列所有单元格，`annotated_csv` 每行前缀 `[row=N]` 即为实际行号

**消费方式：**
- 建立 `日期 → 行号` 映射
- 本周 7 天中找不到的日期记录为缺失

---

## 模式 4：read_daily_rows — 读取指定日期行完整数据

**用途：** 读取找到的日期行完整数据。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.daily_sheet_name>" --range "A<row>:<LAST_COL_DAILY><row>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `row`：目标行号
- `LAST_COL_DAILY`：「每日记录」表头行最右列字母，来自 `read_header` 返回的 `col_indices[-1]`

**期望返回：** 整行字段值

**消费方式：**
- 按 `header_map` 将列字母映射回字段名
- 多个日期行独立调用，或合并为一个 range（仅当行号连续时）
- 整行数据量大时改用 `--output-path ./daily-row.json` 避免截断

---

## 模式 5：find_week_row — 在 PDCA 表中按周号找行号

**用途：** 在「PDCA减脂分析」中定位某周号所在行。

**命令：**
```bash
lark-cli sheets +cells-search --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --find "<week_id>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `week_id`：格式 `YYYY-WXX`

**期望返回：** 匹配单元格地址，如 `A5`

**消费方式：**
- 从地址提取行号
- 无匹配 → 周号行不存在，进入 `create_week_row`

**何时用 search，何时用 read_week_column：**
- 只查一个周号：用本模式（`+cells-search`）最快。
- 需要同时查多个历史周号（如读取上周报告）：先用模式 12 `read_week_column` 读「PDCA减脂分析」A 列整列建立 `周号 → 行号` 映射，再本地查表。

---

## 模式 6：create_week_row — 周号行不存在时插入新行

**用途：** 按周号升序在「PDCA减脂分析」中插入新行。

**命令：**
```bash
lark-cli sheets +cells-set --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --range "A<row>" --cells '[[{"value":"<week_id>"}]]'
```

**输入参数：**
- `pdca.sheets.url`
- `row`：应插入的行号（按周号升序计算得出）
- `week_id`：格式 `YYYY-WXX`

**期望返回：** `ok: true`

**消费方式：**
- 确认周号写入后，继续 `write_fields_by_name`

---

## 模式 7：write_fields_by_name — 按字段名映射写入单元格

**用途：** 把字段名→值映射写入指定周号行的对应列。

**步骤：**
1. PDCA 内部根据 `read_header` 得到的映射，把字段名转换成列字母
2. 构造 `+cells-set` 的批量写入请求
3. 调用 `lark-sheets` skill 执行

**命令：**
```bash
lark-cli sheets +cells-set --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --writes - <<'JSON'
{
  "writes": [
    {"sheet_name": "PDCA减脂分析", "range": "B<row>:B<row>", "cells": [[{"value":"2026-08-24"}]]},
    {"sheet_name": "PDCA减脂分析", "range": "D<row>:D<row>", "cells": [[{"value":"本周闭环总结文本"}]]}
  ]
}
JSON
```

**输入参数：**
- `pdca.sheets.url`
- `row`：目标周号行号
- `fields`：字段名→值 映射
- `header_map`：字段名→列字母 映射

**期望返回：** `ok: true`

**消费方式：**
- 请求被接受后，必须调用 `verify_row_values` 回读校验

---

## 模式 8：verify_row_values — 回读整行校验

**用途：** 写入后读取整行，对比写入值是否真实生效。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --range "A<row>:<LAST_COL_PDCA><row>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `row`：目标周号行号
- `LAST_COL_PDCA`：「PDCA减脂分析」表头行最右列字母，来自该子表 `read_header` 返回的 `col_indices[-1]`（默认 12 列 L，但禁止硬编码）

**期望返回：** 整行字段值

**消费方式：**
- 按 `header_map` 核对每个写入字段的实际值
- 一致 → 字段写入成功
- 不一致 → 换工具/换方式重试一次，仍不一致 → `FIELD_WRITE_FAILED`
- 整行数据量大时改用 `--output-path ./verify-pdca-row.json` 避免截断

---

## 模式 9：read_column_formats — 读取列格式与数据验证

**用途：** 写入「PDCA减脂分析」表前，一次性读取每列的真实 `number_format` 和 `data_validation`，作为值转换和校验的权威依据。当前 PDCA 表字段以文本/日期为主，但当表结构扩展出数字/单选/多选/复选框字段时，本调用可防止写错类型或写入非法选项。

**命令：**
```bash
lark-cli sheets +cells-get \
  --url "<pdca.sheets.url>" \
  --sheet-name "<pdca.pdca_sheet_name>" \
  --range "A2:<LAST_COL>2" \
  --include style,data_validation \
  --format json
```

**输入参数：**
- `pdca.sheets.url`
- `pdca.pdca_sheet_name`
- `LAST_COL`：表头行最右侧列字母，来自 `read_header` 返回的 `col_indices[-1]`

**期望返回：** 第 2 行每个单元格的 `cell_styles.number_format` 和 `data_validation.items`

**消费方式：**
- 建立 `列字母 → {number_format, data_validation_items}` 映射
- 写入前据此转换原始值：
  - `data_validation.items` 存在 → 值必须在列表中，否则 `INVALID_OPTION`
  - `number_format` 含 `%` 且原始值以 `%` 结尾 → 除以 100
  - `number_format` 为时间格式（如 `h:mm`）且原始值为 `HH:mm` → 转为 Excel 时间小数
  - `number_format` 为数字格式 → 转为 float
  - 其他 → 保持字符串或日期字符串
- 字段元数据/输出表结构仅作为语义参考，真实格式/验证以本调用返回为准

**复用脚本：** 可调用本技能目录下的 `scripts/coerce_value.py` 完成上述转换：

```bash
cat <<'JSON' | python3 scripts/coerce_value.py
{
  "header_map": {"起始日期": "B", "本周体重变化": "M"},
  "column_constraints": {
    "B": {"number_format": "yyyy-mm-dd", "data_validation": null},
    "M": {"number_format": "0.00%", "data_validation": null}
  },
  "raw_values": {"起始日期": "2026-08-16", "本周体重变化": "-0.5%"}
}
JSON
```

输出：

```json
{
  "coerced": {"起始日期": "2026-08-16", "本周体重变化": -0.005},
  "errors": {}
}
```

---

## 模式 10：read_specific_columns — 精确读取少数列

**用途：** 当只需要 1-3 个字段（如只看周号、起始日期）时，按列精确读取，避免读整行。

**命令（CSV 形态，只看值）：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<sheet_name>" --range "<COL>2:<COL><LAST_ROW>" --format json
```

**命令（Cells 形态，需要公式/样式/验证）：**
```bash
lark-cli sheets +cells-get --url "<pdca.sheets.url>" --sheet-name "<sheet_name>" --range "<COL>2:<COL><LAST_ROW>" --include value,formula,style,comment,data_validation --format json
```

**输入参数：**
- `pdca.sheets.url`
- `sheet_name`：子表名
- `COL`：目标列字母（来自 `header_map`）
- `LAST_ROW`：实际末行号。不确定时可传一个足够大的值（如 5000），返回的空行可过滤掉

**期望返回：** 单列数据

**消费方式：**
- 按 `header_map` 把字段名转成列字母
- 对每列独立调用，或合并为一个 `+csv-get` / `+cells-get` 连续 range（如 `A2:A5000` 只读周号列）
- 需要同时读多列但不连续时，必须分多次调用，因为 `+csv-get` / `+cells-get` 的 `--range` 只接受单个 A1 range

**大表读取：** 单列数据量大时同样建议加 `--output-path ./col-data.json`。

---

## 模式 11：read_with_output_path — 大表读取兜底

**用途：** 当任何读取命令可能超过 500k 字符默认上限时使用。

**做法：** 在 `+csv-get` 或 `+cells-get` 后追加 `--output-path ./lark-read-<timestamp>.json`。

**效果：**
- 字符上限自动提升到约 20M
- 文件内容是标准 JSON payload，与 stdout 返回结构一致
- stdout 只返回 `output_path`、`byte_count`、`complete`/`truncated` 等摘要
- Agent 从文件中读取并解析，而不是直接解析 stdout

**注意：** 临时文件应放在系统临时目录（如 `/tmp`），不要写入项目目录或用户工作目录；读取后应及时清理。

---

## 模式 12：read_week_column — 读取周号列建立周号→行号映射

**用途：** 替代反复调用 `find_week_row`（`+cells-search`），一次性读取「PDCA减脂分析」A 列所有周号，在本地建立「周号 → 行号」映射，用于读取上周报告等场景。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --range "A2:A<LAST_ROW>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `pdca.pdca_sheet_name`
- `LAST_ROW`：实际末行号。若不确定，可传一个足够大的值（如 5000），返回的 `annotated_csv` 每行自带 `[row=N]` 前缀

**期望返回：** 周号列所有单元格，`annotated_csv` 每行前缀 `[row=N]` 即为实际行号

**消费方式：**
- 建立 `周号 → 行号` 映射
- 读取上周报告时，直接用映射定位行号，再调用 `read_daily_rows`/`verify_row_values` 读取整行
- 找不到的周号 → 记录为缺失，进入 `create_week_row`

**与 `find_week_row` 的选择：**
- 单个周号：用 `+cells-search`。
- 多个周号（如同时读本周和上周）：优先用本模式读整列再本地查表。
