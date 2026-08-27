# 健身追踪技能 · 运维教训

> 记录实操中发现的坑与经验，供后续调用参考。

---

## 一、飞书 Sheets 读取规范

**每次读取必须先读表头，再取数据，禁止硬编码字段顺序。**

`+csv-get` 输出格式不是标准 CSV，每行开头带 `[row=N]` 前缀：
```
[row=100] 2026-08-21,2026-W33,67.55 ,22.00 ,0.00 ,,...
```

**标准读取流程（两条缺一不可）：**
1. **先读表头第一行**，获取实际字段名和顺序，建立字段→索引映射
2. **再按映射取数据**，不用硬编码假设字段位置

```python
# 错误：硬编码字段顺序 → 列对齐错位，午餐后困倦等字段遗漏
fields = {'A': '日期', 'B': '周编号', ...}  # 推算的，不可靠

# 正确：先从表头获取实际字段名和顺序
header_vals = list(csv.reader([header_part]))[0]  # 从表头行解析
field_index = {name: idx for idx, name in enumerate(header_vals)}
data_str = annotated_csv.split('] ', 1)[1]
data_vals = list(csv.reader([data_str]))[0]      # 从数据行解析
val = data_vals[field_index['午餐后困倦']]       # 按实际索引取值
```

---

## 二、BMI 列为公式字段

飞书 Sheets 里 BMI 是公式列（=体重/身高²），读取时：

- BMI 显示 `0.00` ≠ 没数据，可能是**公式未计算**或**身高字段缺失**
- 判断方式：用 `+cells-get --include formula` 查看是否有公式
- 如需 BMI 真实值，需要在表里补充身高数据，或在查询结果里标注"公式未计算"

---

## 三、训练数据读写接口分离

讯记 API 分读写两个接口：

| 用途 | 接口 |
|------|------|
| 读取训练 | `POST /api_trains_for_llm_v2` |
| 写入/更新训练 | `POST /api_upsert_trains_for_llm_v2` |

调用时注意：
- `api_upsert_trains_for_llm_v2` 支持带 `localid` 更新原记录，不带则新建
- 写回时传 `dry_run: true` 可先验证
- 写回限频 45 秒/次，`too frequent` 时等待提示的 `retry after Ns`

---

## 四、写入训练字段名是 `name` 不是 `action_name`

讯记训练写入 JSON 结构：

```json
{
  "movements": [
    {
      "name": "悍马机划船",   // ✅ 正确
      "sets": [
        {"done": true, "weight": "25", "unit": "kg", "reps": "15"}
      ]
    }
  ]
}
```

`action_name` 是读取返回数据的字段名，写入时服务端认的是 `name`，传错会报 `move name missing`。
