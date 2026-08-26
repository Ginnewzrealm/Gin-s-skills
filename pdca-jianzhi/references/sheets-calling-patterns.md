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
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<sheet_name>" --range "A1:AQ1" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `sheet_name`：子表名

**期望返回：** `annotated_csv` 中的第一行表头内容，`col_indices[]`

**消费方式：**
- 解析 CSV 得到字段名数组
- 用 `col_indices[i]` 得到每个字段名对应的列字母
- 读取前先用 `verify_spreadsheet` 确认子表存在
- 读取范围以实际表宽为准，当前表格为 43 列（`A1:AQ1`），但技能文档中应说明"以运行时表宽为准"

---

## 模式 3：read_date_column — 读取日期列以定位行号

**用途：** 在「每日记录」中一次性获取所有已有日期及其行号。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.daily_sheet_name>" --range "A2:A<last_row>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `last_row`：实际末行（可先调用一次确定 `current_region`，或直接用 `current_region` 中返回的最大行号）

**期望返回：** 日期列所有单元格，`annotated_csv` 每行前缀 `[row=N]` 即为实际行号

**消费方式：**
- 建立 `日期 → 行号` 映射
- 本周 7 天中找不到的日期记录为缺失

---

## 模式 4：read_daily_rows — 读取指定日期行完整数据

**用途：** 读取找到的日期行完整数据。

**命令：**
```bash
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.daily_sheet_name>" --range "A<row>:AQ<row>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `row`：目标行号

**期望返回：** 整行字段值

**消费方式：**
- 按 `header_map` 将列字母映射回字段名
- 多个日期行独立调用，或合并为一个 range（仅当行号连续时）

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
lark-cli sheets +csv-get --url "<pdca.sheets.url>" --sheet-name "<pdca.pdca_sheet_name>" --range "A<row>:L<row>" --format json
```

**输入参数：**
- `pdca.sheets.url`
- `row`：目标周号行号

**期望返回：** 整行字段值

**消费方式：**
- 按 `header_map` 核对每个写入字段的实际值
- 一致 → 字段写入成功
- 不一致 → 换工具/换方式重试一次，仍不一致 → `FIELD_WRITE_FAILED`

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
