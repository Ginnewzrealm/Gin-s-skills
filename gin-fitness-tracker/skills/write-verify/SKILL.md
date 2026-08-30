---
# 健身追踪 - 写入验证模块
# 由主技能 gin-fitness-tracker 在内部调用，不独立触发
---

# 健身追踪 - 写入验证子技能

## 职责

`write-verify` 是 DataStore 抽象层的**写入实现入口**。所有对每日记录表和用户配置表的写入都必须经过这里。

核心职责：
1. 统一写入入口
2. 写入前：检查当前值（已有值时需用户确认）
3. 写入时：逐字段写入→复查，每个字段独立验证
4. 写入后：换工具重试机制
5. 单选/多选字段选项防污染（三锁：写入前精确匹配 / 值构造原文复制 / 写入后选项数对比）
6. 禁止向公式字段写入

## 执行流程

### 场景进度

当前场景：gin-fitness-tracker — write-verify

Progress:
- [ ] Stage 1 LOAD_DEFS：读取表头、列约束、字段元数据 [自动]
- [ ] Stage 2 VALIDATE：类型校验、值转换、已有值检查 [硬闸门]
- [ ] Stage 3 WRITE：构造写入请求、执行写入、回读校验 [自动]
- [ ] Stage 4 REPORT：汇总成功/失败列表 [自动]

每个 Stage 结束后调用 `stage_validator.py` 校验产物；任一产物缺失或 `header_map` 无效 → 停止并输出阻塞原因。

Stage 产物清单：

| Stage | 产物 |
|-------|------|
| LOAD_DEFS | `write_request`, `header_map`, `field_metadata`, `column_constraints` |
| VALIDATE | 上述 + `validated_values`, `coerced_values`, `existing_values` |
| WRITE | 上述 + `write_plan`, `write_response`, `verify_result`, `polluted_options` |
| REPORT | 上述 + `write_result` |

禁止：
- 不要静默覆盖用户已有数据
- 不要写入公式字段
- 不要新建单选/多选选项

```
被主技能调用
    ↓
① 发送模块状态反馈：✍️ 正在写入并校验数据...
    ↓
② 接收写入请求 → 产物 write_request.json
    ↓
③ LOAD_DEFS [自动]
   ③a 调用 read_header 读取表头行 → raw_header.json
   ③b build_header_map.py → header_map.json（字段名→列字母，识别空列/重复字段）
   ③c 调用 read_column_formats 读取真实列约束 → raw_column_formats.json
   ③d build_column_constraints.py → column_constraints.json
   ③e stage_validator.py 校验 LOAD_DEFS 产物
    ↓ 任一产物缺失 / header_map 无效 → 停止，输出阻塞原因
    ↓
④ VALIDATE [硬闸门]
   ④a 读取字段元数据子表 → field_metadata.json
   ④b validate_field_metadata.py → validated_values.json
   ④c coerce_value.py → coerced_values.json
   ④d 读取目标行当前值 → current_row_values.json
   ④e check_existing_values.py → existing_values.json
       ↓ existing 非空 → REPORT (needs_user_input)
   ④f stage_validator.py 校验 VALIDATE 产物
    ↓
⑤ WRITE [自动]
   ⑤a prepare_write_request.py → write_plan.json（构造 +cells-set payload）
       ↓ write_plan.errors 非空 → REPORT (partial, FIELD_NOT_FOUND / ...)
   ⑤b stage_validator.py 校验 WRITE 产物
   ⑤c 调用 lark-cli sheets +cells-set --writes - < write_plan.json → write_response.json
   ⑤d 调用 verify_row_values 回读目标行 → verify_row.json
   ⑤e compare_written_values.py → verify_result.json
   ⑤f detect_option_pollution.py → polluted_options.json
       ↓ 回读不一致 → 换工具重试一次 → 仍不一致 → REPORT (partial, FIELD_WRITE_FAILED)
    ↓
⑥ REPORT [自动]
   汇总成功/失败列表 → write_result.json
    ↓
返回结构化结果
```

**核心控制原则**：
- `header_map.json` 是字段名→列字母的唯一权威；Agent 不得凭记忆推断列位置。
- `prepare_write_request.py` 是构造 `+cells-set` range 的唯一入口；Agent 不得自己拼接 `range`。
- `stage_validator.py` 是阶段硬闸门；缺少产物时不得进入下一阶段。

## 返回格式

```json
{
  "status": "success" | "partial" | "failed" | "needs_user_input",
  "module": "write-verify",
  "message": "给用户看的自然语言摘要",
  "data": {
    "table": "daily_record" | "user_config",
    "date": "2026-07-26",
    "fields_written": ["晨起体重", "体脂率"],
    "fields_failed": [
      { "field": "晨起体重", "reason": "写入后复查不一致，重试后仍失败" }
    ],
    "fields_skipped": [
      { "field": "排便情况", "reason": "用户选择跳过" }
    ]
  },
  "errors": []
}
```

## 禁止写入公式字段

公式字段的识别**以「字段元数据」子表为准**，禁止写死字段名。识别规则（满足任意一条即视为公式字段）：

1. 「字段元数据」中「写入方」= `Sheets`
2. 「字段元数据」中「类型」= `公式`

常见被识别为公式字段的示例（实际以运行时读取结果为准）：

| 字段名 | 公式来源 |
|--------|---------|
| 周编号 | 根据日期列计算，周日为一周第一天 |
| 睡眠时长 | 根据入睡时间、起床时间计算 |
| 腰臀比 | 根据腰围 / 臀围计算 |
| 早晚体重差 | 根据前一行睡前体重 - 当日晨起体重计算 |

如果写入请求中包含这些字段，**直接跳过**，并在 `fields_skipped` 中记录原因："该字段为 Sheets 公式字段，由表格自动计算"。

**重要**：如果字段元数据中某字段未标注为公式，但写入后发现表格实际存在公式（复查值与写入值不一致），按「写入后复查不一致」走换工具重试；重试仍不一致则标记 `FIELD_WRITE_FAILED`，不得强行覆盖。

## 字段已有值检查

**重要：禁止静默覆盖用户已有数据。**

写入前，必须检查目标字段是否已有值：

```
读取目标记录的当前值
    ↓
目标字段已有值？
    ├─ 无 → 继续规范化与写入
    └─ 有 → 返回 needs_user_input，询问用户：
            "字段[XXX]已有值[YYY]，是否覆盖？回复'是'覆盖，'否'跳过"
```

**本步骤为硬闸门。目标字段已有值时输出：**
`当前阻塞：字段[XXX]已有值[YYY]，是否覆盖？回复「是」覆盖，「否」跳过。`

## 写入前字段定位与存在性校验

写入前必须已经读取：
- 每日记录表表头行（字段名 → 列位置映射）
- 「字段元数据」子表（字段名 → 类型、选项、写入方）

若字段元数据子表不存在，**禁止继续写入**，返回 `CONFIG_MISSING` 错误。

### 字段元数据与真实表格一致性检查（FIELD_TYPE_MISMATCH）

写入前必须调用 `lark-sheets` skill 的 `read_column_formats` 模式一次性读取真实列约束：

```bash
lark-cli sheets +cells-get \
  --url "<fitness.sheets.url>" \
  --sheet-name "每日记录" \
  --range "A2:<LAST_COL>2" \
  --include style,data_validation \
  --format json
```

对比字段元数据「类型/选项」列与真实 `number_format` / `data_validation.items`：
- 不一致 → 在 `errors` 中返回 `FIELD_TYPE_MISMATCH` warning，提示用户检查表格字段配置，**不阻塞其他字段写入**
- 写入时以 `read_column_formats` 返回的真实约束为准

### 通用值转换（coerce_value.py）

**不再按字段元数据「类型」列硬编码转换规则。** 写入前调用 `coerce_value.py` 脚本，输入为 `header_map`、`column_constraints`（来自 `read_column_formats`）和 `raw_values`，输出为可直接写入 Sheets 的值或错误。

转换规则（无字段特殊逻辑）：

1. **数据验证优先**：若某列 `data_validation.items` 存在，原始值必须在列表中。命中则原样返回；未命中返回 `INVALID_OPTION`。
2. **百分比格式**：若 `number_format` 包含 `%` 且原始值以 `%` 结尾 → 除以 100 转为小数；否则尝试直接解析为 float。
3. **时间格式**：若 `number_format` 为时间格式（如 `h:mm`、`HH:mm:ss`）且原始值为 `HH:mm` / `HH:mm:ss` → 转为 Excel 时间小数（天的小数部分）。
4. **数字格式**：若 `number_format` 含数字占位符（`0`、`#`）→ 转为 float。
5. **默认**：其他情况作为字符串原样返回。

**调用示例：**

```bash
cat <<'JSON' | python3 scripts/coerce_value.py
{
  "header_map": {"体脂率": "D", "早餐时间": "W", "有氧": "AO"},
  "column_constraints": {
    "D": {"number_format": "0.00%", "data_validation": null},
    "W": {"number_format": "h:mm", "data_validation": null},
    "AO": {"number_format": "General", "data_validation": {"items": ["有氧"]}}
  },
  "raw_values": {"体脂率": "21.9%", "早餐时间": "08:30", "有氧": "无"}
}
JSON
```

输出：

```json
{
  "coerced": {"体脂率": 0.219, "早餐时间": 0.3541666666666667},
  "errors": {"有氧": "INVALID_OPTION: '无' not in ['有氧']"}
}
```

**原则重申**：Agent 把原始值传给 `coerce_value.py`，由脚本根据真实表格约束决定最终写入形态。禁止在 Agent prompt 中写死“体脂率要除 100”、“禁止写无”等具体字段规则。

### 字段名存在性校验

写入前再次核对：
- 字段名必须存在于当前表头行
- 字段名必须存在于字段元数据子表
- 任一不存在 → 返回 `FIELD_NOT_FOUND`，不写入

### 按字段名映射写入（禁止按位置/顺序）

**致命错误模式**：Agent 凭记忆或位置顺序把字段值拼接到列字母上。例如：

```json
// ❌ 错误：按位置推断
[
  {"range": "C<row>:C<row>", "cells": [[{"value": 68.5}]]},
  {"range": "D<row>:D<row>", "cells": [[{"value": 0.238}]]}
]
```

正确做法：**只传字段名和值给脚本，由脚本查表头决定列字母**。

```bash
cat <<'JSON' | python3 scripts/prepare_write_request.py
{
  "table": "daily_record",
  "row": 42,
  "header_map": {"晨起体重": "C", "体脂率": "E"},
  "column_constraints": {...},
  "coerced_values": {"晨起体重": 68.5, "体脂率": 0.238}
}
JSON
```

**禁止：**
- ❌ Agent 自己构造 `range` 或列字母
- ❌ 使用记忆中固定的列字母（如"晨起体重一定是 C 列"）
- ❌ 按字段顺序递增列字母（C、D、E...）

**允许：**
- ✅ 使用 `build_header_map.py` 生成的 `header_map`
- ✅ 使用 `prepare_write_request.py` 生成的 `write_plan`

### 字段类型与写入方式

**不再按字段元数据「类型」列硬编码写入形态。** Agent 写入时遵循以下通用原则：

| 真实列约束 | 写入值形态 | 说明 |
|------------------|-----------|------|
| 有 `data_validation.items` | 字符串（必须匹配选项） | 值必须出现在真实下拉选项列表中，命中后原样复制 |
| `number_format` 含 `%` | 小数 | 原始值如 `21.9%` 会被 `coerce_value.py` 转为 `0.219` |
| `number_format` 为时间格式（`h:mm` 等） | 小数 | 原始值如 `08:30` 会被转为 Excel 时间小数 `0.3542` |
| `number_format` 为数字格式 | 数字 | 直接解析为 float |
| 其他 | 字符串 | 原样写入 |
| 公式字段 | 不写入 | 「写入方」= Sheets 或「类型」= 公式 的字段直接跳过 |

**Agent 只负责：**
1. 数字字段传数字或数字字符串
2. 时间字段传 `HH:mm` 字符串（由 `coerce_value.py` 转小数）
3. 百分比字段传 `21.9%` 或 `0.219`（由 `coerce_value.py` 按 `number_format` 处理）
4. 单选字段传表格真实选项原文
5. 不写入公式字段

**注意**：数字/时间/百分比/日期的具体显示格式（小数位、`HH:mm`、日期显示等）由飞书表格的单元格格式决定，Agent 不需要也不应该自己补零或转换。

## 单选字段匹配算法

单选字段的语义映射和写入必须按以下算法执行，不允许跳过步骤或自行构造字符串。

```
步骤 1：读取真实下拉选项
    ↓ 从 read_column_formats 返回的 column_constraints[col].data_validation.items 获取
步骤 2：将用户语义映射到某个已有选项的索引
    ↓ 无法映射 → 返回 INVALID_OPTION，列出全部选项
步骤 3：写入值必须从选项列表中原样复制
    ↓ 复制该索引对应的完整字符串（含 emoji、空格、大小写）
步骤 4：写入前对比
    ↓ 写入值 ≠ 选项原文 → 停止写入，返回 INVALID_OPTION
```

**核心原则重申**：语义理解只用于「选」，不用于「写」。步骤 2 的输出只是一个索引或选项引用，步骤 3 必须原文复制。

**本步骤为硬闸门。用户选项无法匹配真实下拉选项时输出：**
`当前阻塞：「XXX」不在可选值中。可选值为：A/B/C。请回复正确选项，或回复「跳过」跳过该字段。`

## 单选/多选字段选项防污染（三锁）

**背景（必须理解的原因）**：飞书表格的数据验证下拉选项理论上不会被 API 静默新增，但部分写入方式仍可能绕过校验。因此写入前必须精确匹配选项列表，写入后复查选项数量。

**总原则：语义理解只用于「选」，不用于「写」。** 用户用自然语言报数时，AI 的语义分析仅用于把意图映射到某个已有选项；写入的字符串必须 100% 来自选项列表原文，AI 自己组织的措辞永远不得作为写入值。

### 单选字段的核心认知

**单选字段不是文本字段，Agent 不是在"写答案"，而是在"做选择"。**

- 用户说"午后没有能量低谷" → Agent 的工作是**选择**最匹配的已有选项 `🟢没有`
- 用户说"早上状态正常" → Agent 的工作是**选择**最匹配的已有选项 `🟢正常不精神也不疲惫`
- 用户说"昨晚睡得挺好" → Agent 的工作是**选择**最匹配的已有选项 `🟢正常`

**选择完成后，写入值必须是选项原文，一字不差。**

禁止：
- ❌ 替用户"精简"选项：把 `🟢正常不精神也不疲惫` 写成 `🟢正常`
- ❌ 替用户"换种说法"：把 `🟢没有` 写成 `🟢无`
- ❌ 去掉 emoji、改动 emoji、增减空格
- ❌ 因为"意思差不多"就构造一个新措辞

允许：
- ✅ 完全原样复制已选中的选项字符串
- ✅ 当无法映射时，列出所有选项请用户自己选择

### 锁 1（写入前·精确匹配）

**真实下拉选项是唯一权威。** 字段元数据子表中的「选项」列仅作为参考，当两者不一致时，必须以真实下拉选项为准。

1. **优先**从 `read_column_formats` 返回的 `column_constraints[col].data_validation.items` 读取该字段的真实数据验证下拉选项（写入前已统一读取，无需逐列重复调用）

2. 同时读取「字段元数据」子表中该字段的「选项」列，作为参考和兜底
3. **若字段元数据选项与真实下拉选项不一致** → 在 `errors` 中返回 `FIELD_TYPE_MISMATCH` warning，提示用户检查表格字段配置；写入时以**真实下拉选项**为准，不阻塞其他字段写入
4. 将用户语义映射到某个已有选项
5. **映射成功** → 进入锁 2 构造写入值
6. **映射不上任何选项** → **停止写入此字段**，返回 `INVALID_OPTION` 错误，列出全部真实下拉选项让用户选择
7. **一律禁止新建选项，无任何例外**：即使推断用户想要一个新选项，也只能提示「请先在飞书字段设置中手动添加该选项」，然后跳过此字段。新增选项的唯一途径是用户在飞书侧手动配置

**为什么真实下拉优先？**

字段元数据是人工维护的参考文档，可能滞后或写错（如「早起状态」多写了 `疲惫 / 正常`）。只有真实表格列的数据验证下拉选项才是 Sheets 实际接受的值。Agent 若按字段元数据写入不存在的选项，会导致写入失败或数据格式错误。

### 锁 2（值构造·原文复制）

- 写入值必须从选项列表中**原样复制**，禁止凭印象重打：emoji、空格、大小写都必须与选项原文一致
- **严禁任何形式的改写或构造**：
  - ❌ 把 `🟢没有` 写成 `🟢无`
  - ❌ 把 `🟢正常不精神也不疲惫` 写成 `🟢正常`
  - ❌ 把 `⚠️轻度异常` 写成 `⚠️轻微异常`
  - ❌ 去掉 emoji、改动 emoji、增减空格、替换同义词
- 多选字段：数组中每个元素都必须是选项列表原文

**正确示例**：用户说"没有午后能量低谷"，语义映射到选项 `🟢没有`，写入值必须是 `🟢没有`，不得是 `🟢无`、`没有`、`无` 等任何变体。

### 锁 3（写入后·选项数对比）

1. 写入单选/多选字段前，通过 `build_column_constraints.py` 记录该字段的选项数量 N（写入前 `column_constraints_before.json`）
2. 单元格复查通过后，重新调用 `read_column_formats` 读取约束，并通过 `build_column_constraints.py` 生成 `column_constraints_after.json`
3. 调用 `detect_option_pollution.py` 对比前后选项数量：

   ```bash
   cat <<'JSON' | python3 scripts/detect_option_pollution.py
   {
     "before": {"E": {"data_validation": {"items": ["🟢正常", "🔴异常"]}}},
     "after": {"E": {"data_validation": {"items": ["🟢正常", "🔴异常", "🟡待定"]}}},
     "header_map": {"大解状态": "E"}
   }
   JSON
   ```

4. **数量增加** → 说明有未授权选项被创建，立即单独告警用户：「⚠️ 检测到字段[XXX]被新增未授权选项[YYY]，请到飞书字段设置中手动删除」
5. 该告警不影响本次写入的成功状态，但必须明确告知用户，不得静默忽略

## 执行写入

Sheets 后端通过 `lark-sheets` skill 的 `write_fields_by_name` 模式写入单元格。

**关键原则：** `+cells-set` 写入时会覆盖单元格整个对象（包括样式），因此必须在每个 cell JSON 中显式附带 `number_format`，否则原列的 `0.00%`、`h:mm` 等格式会被重置为 General。

**字段定位硬闸门：**
- Agent **禁止**自己把字段名转成列字母，也 **禁止** 自己构造 `range`。
- 所有 `range` 必须由 `prepare_write_request.py` 根据当前 `header_map.json` 生成。
- 写入前必须调用 `stage_validator.py` 校验 WRITE stage 产物。

**调用流程：**

```bash
# 1. 构造 write_plan.json（由脚本确保列字母、number_format 正确）
cat <<'JSON' | python3 scripts/prepare_write_request.py > write_plan.json
{
  "table": "daily_record",
  "row": 42,
  "header_map": {"日期": "A", "晨起体重": "C", "体脂率": "E"},
  "column_constraints": {
    "C": {"number_format": "0.00", "data_validation": null},
    "E": {"number_format": "0.00%", "data_validation": null}
  },
  "coerced_values": {"晨起体重": 67.65, "体脂率": 0.216}
}
JSON

# 2. 校验 WRITE stage 产物
cat <<'JSON' | python3 scripts/stage_validator.py
{
  "stage": "WRITE",
  "artifacts": {
    "write_request": {"table": "daily_record", "date": "2026-08-22", "fields": {...}},
    "header_map": {"valid": true, "header_map": {"晨起体重": "C", "体脂率": "E"}},
    "field_metadata": {...},
    "column_constraints": {...},
    "validated_values": {...},
    "coerced_values": {"晨起体重": 67.65, "体脂率": 0.216},
    "existing_values": {"existing": [], "blank": ["晨起体重", "体脂率"]},
    "write_plan": <write_plan.json 内容>
  }
}
JSON

# 3. 执行写入（直接使用 write_plan.json，不修改其中 range）
lark-cli sheets +cells-set --url "<fitness.sheets.url>" --sheet-name "每日记录" --writes - < write_plan.json
```

**`write_plan.json` 示例：**

```json
{
  "writes": [
    {"sheet_name": "每日记录", "range": "C42:C42", "cells": [[{"value": 67.65, "number_format": "0.00"}]], "field_name": "晨起体重"},
    {"sheet_name": "每日记录", "range": "E42:E42", "cells": [[{"value": 0.216, "number_format": "0.00%"}]], "field_name": "体脂率"}
  ],
  "errors": {}
}
```

**`number_format` 来源：**
- 写入前 `read_column_formats` 已读取每列真实 `number_format`，保存在 `column_constraints[col].number_format`
- `prepare_write_request.py` 构造 `--writes` 时把目标列的 `number_format` 一并写入每个 cell 的 JSON
- 百分比列传小数（如 `0.216`）+ `"0.00%"`，飞书会渲染为 `21.60%`
- 时间列传 Excel 时间小数 + `"h:mm"` 或 `"HH:mm:ss"`

**用户配置表写入：**

`user_config` 是行-based 存储，需要额外传入 `row_map`：

```bash
cat <<'JSON' | python3 scripts/prepare_write_request.py
{
  "table": "user_config",
  "header_map": {"配置选项": "A", "值": "B"},
  "column_constraints": {"B": {"number_format": "0.00"}},
  "coerced_values": {"当前体重": 68.5},
  "row_map": {"当前体重": 5}
}
JSON
```

### 写入后必须记录成功证据

`lark-cli sheets +cells-set` 返回的响应中必须包含：

- `revision`：表格版本号
- `updated_cells_count`：实际更新的单元格数量

**如果调用没有返回上述字段，或返回错误，视为写入失败。** 不得仅凭命令"执行了"就假设写入成功。

### 写入前最终检查

1. **公式字段**：若字段元数据中「写入方」= Sheets 或「类型」= 公式 → 跳过
2. **字段存在性**：字段名必须存在于当前表头行和字段元数据子表
3. **写入组织形式**：必须按「字段名 → 值」键值对传递，禁止按数组顺序

## 字段元数据类型校验

`collect-data` 用 LLM 从自然语言中提取字段和值后，`write-verify` 必须按字段元数据子表的「类型」做硬校验。

**调用脚本：**

```bash
cat <<'JSON' | python3 scripts/validate_field_metadata.py
{
  "field_metadata": {
    "入睡时间": {"type": "时间", "options": null, "description": "格式 HH:mm，24小时制"},
    "大解状态": {"type": "单选", "options": ["🟢正常1次", "⚠️异常无/少"], "description": "..."},
    "晨起体重": {"type": "数字", "options": null, "description": "单位 kg，保留2位小数"}
  },
  "raw_values": {
    "入睡时间": "01:00",
    "大解状态": "⚠️异常无/少",
    "晨起体重": "68.5"
  }
}
JSON
```

**输出：**

```json
{
  "valid": {
    "入睡时间": "01:00",
    "大解状态": "⚠️异常无/少",
    "晨起体重": 68.5
  },
  "errors": {}
}
```

**校验规则：**

| 元数据类型 | 校验内容 |
|-----------|---------|
| 数字 | 必须能解析为数字；支持从字符串中提取第一个数字 |
| 时间 | 必须匹配 `HH:mm` 或 `HH:mm:ss`，规范化为两位小时 |
| 日期 | 必须匹配 `YYYY-MM-DD` |
| 单选 | 值必须在选项列表中（支持 emoji/空格归一化兜底） |
| 多选 | 每个元素都必须在选项列表中 |
| 文本 | 任意字符串 |
| 公式 | Agent 不写入，返回跳过错误 |

**硬闸门行为：**

- `errors` 为空 → 继续执行 `coerce_value.py` 和写入
- `errors` 非空 → 停止对应字段写入，返回错误给用户，不阻塞其他字段
- 单选字段值不在选项中时，错误信息必须列出全部可选值

### 按字段类型传值

Agent 只负责传语义原始值，`coerce_value.py` 根据 `read_column_formats` 返回的真实约束自动转换。具体显示格式由飞书表格单元格格式决定，Agent 不需要也不应该自己补零或转换；但必须在 cell JSON 中附带 `number_format`，否则写入后格式会被重置为 General。

| 真实列约束 | Agent 应传值 | 示例 | coerce_value.py 处理后 |
|------------------|-------------|------|------------------------|
| 数字格式 | 数字或数字字符串 | `67.65` | `67.65` |
| 百分比格式 | 可带 `%` 的字符串 | `"21.9%"` | `0.219` |
| 时间格式 | `HH:mm` 字符串 | `"08:30"` | `0.354166...` |
| 日期格式 | 字符串 | `"2026-08-22"` | `"2026-08-22"` |
| 有下拉选项 | 字符串（必须来自真实 items） | `"🟢正常不精神也不疲惫"` | 原样返回 |
| 其他文本 | 字符串 | `"备注"` | 原样返回 |
| 公式 | 不写入 | — | — |

Agent 只需要保证：
- 数字字段传数字
- 时间字段传 `HH:mm` 字符串
- 百分比字段传 `21.9%` 或小数
- 单选字段传表格真实选项原文
- 不写入公式字段

### 列定位

- 写入前必须调用 `read_header`，再由 `build_header_map.py` 建立「字段名 → 列字母」映射
- `build_header_map.py` 会识别空列、重复字段，并返回 `valid` 状态；`valid=false` 时禁止写入
- 每个字段独立定位到自己的列
- **禁止假设字段顺序**：即使今天第 3 列是「体脂率」，明天也不能假设它还是第 3 列
- 所有 range 由 `prepare_write_request.py` 生成，Agent 不得自行拼接

### 字段名存在性校验

写入前由 `prepare_write_request.py` 再次核对：
- 字段名必须存在于当前 `header_map`
- 字段名必须存在于字段元数据子表（由 `validate_field_metadata.py` 校验）
- 任一不存在 → 返回 `FIELD_NOT_FOUND`，不写入

## 写入后回读验证

**这是防止"伪写入"的核心防线。** 写入操作必须闭环验证：写入 → 回读 → 对比 → 一致后才算成功。

### 写入值 vs 复查值对比

**复查基准：以 `header_map` 和 `write_plan` 为准，禁止以写入时内存中的字段映射为基准。**

调用 `lark-sheets` skill 的 `verify_row_values` 模式读取目标行：

```bash
lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A<row>:<LAST_COL><row>" --format json
```

`LAST_COL` 来自 `read_header` 返回的 `col_indices[-1]`。若整行数据较大，改用 `--output-path ./verify-row.json` 读取文件内容再核对。

读取到 `verify_row.json` 后，调用 `compare_written_values.py`：

```bash
cat <<'JSON' | python3 scripts/compare_written_values.py
{
  "write_plan": <write_plan.json 内容>,
  "verify_row_values": {"晨起体重": 67.65, "体脂率": 0.216}
}
JSON
```

输出：

```json
{
  "matched": ["晨起体重"],
  "mismatched": [{"field": "体脂率", "expected": 0.216, "actual": 0.238}],
  "missing": []
}
```

按结果处理：

```
compare_written_values.py 结果
    ↓
    ├─ matched 包含全部写入字段 → 此字段验证通过
    ├─ mismatched 非空 → 执行换工具重试
    └─ missing 非空 → 视为写入失败，不得标记为 success
```

### 验证通过的硬性标准

一个字段要被标记为 `fields_written`，必须同时满足：

1. `lark-cli` 返回包含 `revision` 和 `updated_cells_count`（即 lark-cli 返回的 revision 和 updated_cells_count 必须存在）
2. 回读到的值与写入值一致
3. （单选/多选字段）选项数量未增加

**任一条件不满足 → 不得标记为 success**，按以下规则处理：
- API 无返回/返回错误 → 标记为失败，返回 `FIELD_WRITE_FAILED` 或 `LARK_SKILL_UNAVAILABLE`
- 回读值不一致 → 执行换工具重试；重试后仍不一致 → 标记为失败
- 选项数量增加 → 告警用户，但该字段本身若回读一致仍可视为成功

### 未通过回读验证不得标记为 success

严禁出现以下行为：
- ❌ lark-cli 调用失败或没有返回，仍然汇报"已写入"
- ❌ 没有执行回读就汇报"验证通过"
- ❌ 回读值与写入值不一致，仍然标记字段为成功
- ❌ 把"计划执行的命令"当作"已执行的证据"

### 返回数据中的写入证据

`write-verify` 返回的 `data` 中应包含：

```json
{
  "fields_written": ["晨起体重"],
  "fields_failed": [],
  "write_evidence": {
    "revision": 123,
    "updated_cells_count": 1
  }
}
```

如果没有 `revision` 和 `updated_cells_count`，`status` 不得为 `success`。

## 透明自动重试机制

**核心原则**：写入失败后必须让用户知道，不能静默修复；但 skill 应该主动尝试修复，而不是把控制权交给 Agent 去手动调 `lark-cli`。

### 重试流程

```
写入后复查不一致
    ↓
【第一次通知用户】
「字段[XXX]写入后复查不一致，准备换工具重试...」
    ↓
换工具/换方式重试写入
    ↓
再次读取复查
    ↓
├─ 重试后一致 → 此字段验证通过
└─ 重试后仍不一致
    ↓
【第二次通知用户】
「重试后仍不一致，将自动重新读取表头并执行完整写入流程...」
    ↓
自动重新执行一次完整流程：
  LOAD_DEFS → VALIDATE → WRITE → REPORT
  （重新读取表头、列约束、字段元数据，重新生成 write_plan，重新写入并复查）
    ↓
  ├─ 自动重跑后一致 → 返回 success，明确告知用户「已重新读取表头并完成写入」
  └─ 自动重跑后仍不一致 → 标记为 FIELD_WRITE_FAILED，返回错误，并明确提示用户回复「重来」
```

### 透明要求

每次进入重试或自动重跑前，必须向用户发送状态消息：

1. **第一次 mismatch**：`⚠️ 字段[XXX]写入后复查不一致，准备换工具重试...`
2. **换工具重试仍失败**：`⚠️ 重试后仍不一致，将自动重新读取表头并执行完整写入流程...`
3. **自动重跑成功**：`✅ 已重新读取表头并完成写入，写入字段：...`
4. **自动重跑失败**：`❌ 自动修复失败，请检查飞书表格；不要手动修改，可回复「重来」让技能重新执行`

**禁止**：
- ❌ 静默重试不通知用户
- ❌ 让 Agent 用 `lark-cli` 逐格手动修复
- ❌ 在未告知用户的情况下直接返回 `partial`/`failed`

### 重试策略

| 当前工具 | 重试工具 |
|---------|---------|
| `lark-sheets` 工具 A | `lark-sheets` 工具 B（如可用） |
| 单一工具 | 在 skill 内部尝试不同参数/批量/单格写入 |

### 自动重跑条件

只有同时满足以下条件时才自动重跑完整流程：

1. 换工具重试后仍有字段 mismatch
2. 该字段不是公式字段
3. 该字段不是因为已有值被用户拒绝覆盖
4. 此前在本 turn 内没有已经自动重跑过（最多 1 次，防止无限循环）

自动重跑产物：
- `retry_attempted: true`
- `retry_succeeded: true/false`
- `retry_header_map`、`retry_write_plan` 等保留用于排查

## 批量字段处理规则

**用户一段话包含多个字段时，必须逐字段独立处理。**

**写入顺序**：先处理所有字段（成功写入的记录到内存，失败的记录 reason），最后一起汇总告知用户。

**不允许**等用户确认失败字段后再一起写入——这样会导致用户体验割裂，且如果用户离开会话数据丢失。

```
接收多字段写入请求
    ↓
对每个字段：跳过公式字段 → 已有值检查 → 选项校验 → 写入 → 复查 → 换工具重试
    ↓
每个字段独立验证，一个失败不影响其他字段
    ↓
全部完成后汇总告知用户
```

**失败字段的后续处理**：用户可以对失败字段选择重新录入（会覆盖已写的字段）或跳过（保持已写入状态）。

## 复查时机

| 操作 | 是否需要复查 |
|------|------------|
| 每日记录表写入（任何字段） | ✅ 必须复查 |
| 用户配置表写入（当前体重/体脂） | ✅ 必须复查 |
| 初始化时的测试记录写入 | ✅ 必须复查 |

## 错误提示模板

```
⚠️ 字段[XXX]为公式字段，已跳过
原因：该字段由 Sheets 公式自动计算，Agent 不写入
操作：无需操作，公式会根据依赖字段自动更新
影响：该字段保持公式计算值

❌ 字段[XXX]不在表头行白名单中
原因：写入请求包含的字段名不是当前表格真实存在的字段
操作：请检查字段名拼写，或从表头行字段列表中选择
影响：该字段未写入，返回 `FIELD_NOT_FOUND`

⚠️ 字段[XXX]已有值[YYY]
原因：该字段已存在用户录入数据
操作：请确认是否覆盖（回复"是"覆盖，"否"跳过）
影响：不覆盖则保持原值

❌ 字段[XXX]写入被飞书拒绝
原因：传入值[YYY]不符合该字段的单元格格式或数据验证规则（如数字列传了文本、单选值不在下拉列表中）
操作：请检查字段[XXX]的单元格格式，或从以下现有选项中选择：[合法选项]
影响：该字段未写入，不阻塞其他字段录入

⚠️ 字段[XXX]写入失败
原因：写入后复查不一致，换工具重试 + 自动重新读取表头重跑完整流程后仍失败
操作：请检查飞书表格；不要手动修改，回复「重来」让技能重新执行
影响：该字段未写入，不阻塞其他字段录入

❌ 选项[YYY]不在字段[XXX]可选值中
原因：用户输入与字段选项不匹配；本技能一律禁止新建选项
操作：请从以下现有选项中选择：选项A / 选项B / 选项C；如需新增选项，请先在飞书字段设置中手动添加后再录入
影响：该字段未写入

⚠️ 字段[XXX]元数据与真实表格不一致
原因：字段元数据中的「类型/选项」与飞书表格实际列验证不一致
操作：请检查表格字段配置或字段元数据子表
影响：该字段写入前已告警，其他字段继续处理

⚠️ 检测到未授权新选项
原因：写入后字段[XXX]的选项数量增加，存在未授权选项[YYY]
操作：请到飞书表格的字段设置中手动删除该选项
影响：本次写入值本身有效，但选项列表被污染

❌ 表头存在重复字段[XXX]
原因：字段[XXX]在当前表头行中出现多次（如 C 列和 G 列），无法确定写入哪一列
操作：请检查飞书表格表头，删除或重命名重复字段
影响：该字段未写入，返回 `DUPLICATE_HEADER`

❌ 当前阶段缺少必要产物[YYY]
原因：Progress Checklist 阶段[XXX]的必要产物未生成或无效，无法继续执行
操作：请检查前置步骤是否成功完成，或回复「重来」从 Stage 1 开始
影响：写入流程被硬闸门阻塞，未执行任何写入
```

## 输入输出示例

### 输入

```json
{
  "table": "daily_record",
  "date": "2026-07-19",
  "fields": {
    "晨起体重": { "value": 68.25, "unit": "kg" },
    "体脂率": { "value": 23.8, "unit": "%" },
    "总热量": { "value": 1838.76, "unit": "kcal" }
  }
}
```

### 输出

```json
{
  "status": "success",
  "module": "write-verify",
  "message": "✅ 已写入并校验 3 个字段：晨起体重、体脂率、总热量。",
  "data": {
    "table": "daily_record",
    "date": "2026-07-19",
    "fields_written": ["晨起体重", "体脂率", "总热量"],
    "fields_failed": [],
    "fields_skipped": []
  },
  "errors": []
}
```
