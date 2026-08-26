# 写入与回执确认规则（pdca-write 模块）

> 报告生成后读取本文件执行写入。

## 步骤

1. 读取「PDCA减脂分析」表头行（`read_header`），建立字段名→列字母映射，核对 12 列结构 → 见 `输出表结构.md`
2. **读取真实列约束**：调用 `read_column_formats` 读取第 2 行每列的 `number_format` 和 `data_validation`
3. 按 Sheets CellValue 格式规则构造 12 个字段值：
   - 当前 PDCA 表以**文本**和**日期**字段为主，可直接写入字符串或 `YYYY-MM-DD`
   - 若未来表结构扩展出数字 / 百分比 / 时间 / 单选 / 多选字段，**必须**先调用 `scripts/coerce_value.py` 根据真实列约束转换原始值，禁止在 prompt 中写死字段级规则
4. 调用 `find_week_row` 按周号查找行号：
   - 存在 → 使用现有行
   - 不存在 → 按周号升序计算插入位置，调用 `create_week_row`
5. 调用 `write_fields_by_name` 写入该行
6. **回执确认**：调用 `verify_row_values` 回读整行，逐字段比对
7. 读回失败 → 重试，最多 3 次；仍失败 → 触发终止条件，走统一错误处理

## 关键禁令

- 周号字段由周计算算法确定，**禁止手动写入周号字段**
- 禁止跳过回执确认直接报告成功
- 写入前必须先 `read_header` 核对字段，禁止假设字段存在
- **禁止写死字段级转换规则**（如“体脂率要除 100”、“禁止写无”）；所有类型转换必须通过 `read_column_formats` + `coerce_value.py` 由真实表格约束驱动
