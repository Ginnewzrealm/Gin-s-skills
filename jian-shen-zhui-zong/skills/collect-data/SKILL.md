---
# 健身追踪 - 数据收集模块
# 由主技能 jian-shen-zhui-zong 在内部调用，不独立触发
---

# 健身追踪 - 数据收集子技能

## 职责

`collect-data` 负责所有需要用户输入数据的场景：

1. 每日轮询
2. 补数据
3. 回复录入（用户直接报告数据）

**不处理只读查询**，只读查询由 `query-data` 负责。

## 执行流程

```
被主技能调用
    ↓
① 发送模块状态反馈：📝 正在生成当前时段需要记录的内容...
    ↓
② 校准北京时间，判断当前时段（T1/T2/T3）
    ↓
③ 读取用户配置表，展示今日目标
    ↓
④ 动态读取字段详情（表头行 + 字段元数据子表）
    ↓
④b **问题生成前强制检查清单**（每日轮询/补数据模式）
       - 字段名必须 100% 来自 read_header 返回的表头行
       - 不在表头行中的字段名 → 不得生成问题
       - 单选字段的问题选项必须来自真实下拉选项原文
    ↓
⑤ 根据模式生成问题或解析用户数据
    ↓
⑥ 调用 write-verify 写入数据
    ↓
⑦ 更新用户配置表中的当前体重/体脂
    ↓
⑧ 如果是最晚时段 → 调用 sync-xunji 填充空白字段
    ↓
⑨ 返回结构化结果
```

## 返回格式

```json
{
  "status": "success" | "partial" | "failed" | "needs_user_input",
  "module": "collect-data",
  "message": "给用户看的自然语言摘要",
  "data": {
    "date": "2026-07-26",
    "period": "morning" | "noon" | "evening",
    "fields_written": [],
    "fields_failed": [],
    "fields_skipped": []
  },
  "errors": []
}
```

## 模式说明

### 每日轮询模式

无日期参数，处理当天数据。若当日日期行不存在，调用 `create_date_row` 模式按升序插入新行。

### 补数据模式

传入具体日期。若该日期行不存在，调用 `create_date_row` 模式按日期升序插入新行。

### 回复录入模式

用户直接报告数据（如"晨起体重68.5kg"）。解析数据后：
1. 展示与目标的差异
2. 调用 `write-verify` 写入
3. 处理失败字段
4. 更新用户配置表（体重/体脂）

## 时区与时段

时区规则（UTC+8）、周定义与 Week Number、时段划分，统一以 `knowledge/polling-rules.md` 的"时区规则与周定义"和"时段划分"章节为准。


## 目标展示

### 读取用户配置

调用 `DataStore.getUserConfig()` 读取用户配置表，获取：
- 目标热量、蛋白、脂肪、碳水
- 当前阶段（减脂期/维持期/增肌期）
- 碳水循环启用状态（如果开启，展示训练日/休息日对应碳水目标）
- 用户身高（用于计算 BMI）

### 碳水循环展示

详见 `knowledge/training-day-rules.md`。

核心规则：
- 读取 `碳水循环启用`、`碳水训练日目标`、`碳水休息日目标`
- 根据讯记数据或训练频率推算当天是训练日还是休息日
- 展示对应碳水目标

## 动态问题生成

### 字段来源红线

**生成问题时，字段名必须 100% 来自 `read_header` 读取的表头行字段全集。**

禁止行为：
- ❌ 凭记忆或想象构造字段名（如"下午茶时间"、"下午茶感觉"）
- ❌ 为"补全"而添加表头行中不存在的字段
- ❌ 用语义推断字段名（如"既然有早餐，就该有下午茶"）

允许行为：
- ✅ 从表头行字段数组中筛选当前时段字段
- ✅ 用字段元数据子表中的「填写说明」和「选项」丰富问题文本

**若当前时段在表头行中没有对应字段，则该时段没有问题可问，直接进入下一流程，不得编造问题。**

### 第一步：读取字段定义

1. 调用 `lark-sheets` skill 的 `read_header` 模式读取每日记录表头行
   （表名与表头行范围定义见 `config/sheets-schema.md` 的「每日记录子表」章节）：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A1:<LAST_COL>1" --format json
   ```

   返回的 `col_indices[-1]` 即为 `<LAST_COL>`。

2. 调用 `lark-sheets` skill 的 `read_field_metadata` 模式读取「字段元数据」子表
   （表名与范围定义见 `config/sheets-schema.md` 的「字段元数据子表」章节）：

   ```bash
   lark-cli sheets +csv-get --url "<fitness.sheets.url>" --sheet-name "字段元数据" --range "A1:F50" --format json
   ```

### 第二步：确定字段时段归属

按 `knowledge/polling-rules.md` 的"字段时段归属规则"执行：

1. **优先**：若「字段元数据」子表中包含该字段，以子表中的「时段」列为准。
2. **兜底**：若子表中不存在，按字段名中的关键词模式匹配：
   - 包含"晨起"、"早餐"、"起床"、"入睡"、"早起"、"晨间"、"半夜" → 晨间
   - 包含"午餐"、"午后"、"午间" → 午间
   - 包含"晚餐"、"睡前"、"傍晚"、"训练"、"晚间" → 晚间
   - 无法判断 → 全天/元字段

### 第三步：筛选当前时段问题

根据当前时段，从**表头行字段全集**中筛选字段归属为该时段的字段。

### 第四步：生成问题

对于每个字段：
1. 使用「字段元数据」子表中的「填写说明」作为问题文本；若子表无该字段，用字段名本身。
2. 如果「选项」列有值，格式化选项列表供用户选择。
3. **如果字段缺少时段归属，用字段名本身作为问题文本，继续轮询，不停止**

## 写入流程

### 写入前检查

**重要：先确认记录存在，不存在则自动创建。**

1. 调用 `lark-sheets` skill 的 `find_date_row` 模式在「每日记录」子表日期列中查找 `date`：

   ```bash
   lark-cli sheets +cells-search --url "<fitness.sheets.url>" --sheet-name "每日记录" --find "<date>" --format json
   ```

2. **行不存在** → 调用 `lark-sheets` skill 的 `create_date_row` 模式按日期升序插入新行：

   ```bash
   lark-cli sheets +cells-set --url "<fitness.sheets.url>" --sheet-name "每日记录" --range "A<row>" --cells '[[{"value":"<date>"}]]'
   ```

3. **行存在** → 获取行号，调用 `write-verify` 写入

### BMI 计算

如果写入字段包含"晨起体重"且用户配置中有"身高"：
1. 读取当前身高 `h`（单位 m）
2. 计算 `BMI = 晨起体重 / (h * h)`
3. 将 BMI 作为额外字段加入写入请求

### 调用 write-verify

将用户回复的数据组织为字段映射，调用 `write-verify` 写入：

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

**注意**：`collect-data` 只做初步语义解析（如从"68.5kg"中提取数字和单位），**不提前做类型规范化**。所有类型校验、时间补零、单选选项匹配、公式字段跳过等规则统一由 `write-verify` 执行，避免两个模块规则不一致导致格式错误。

### 处理写入结果

**write-verify 返回格式**（统一契约）：

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

**处理分支**：

```
检查 status
    ↓
    ├─ status == "success" → 全部写入成功
    ├─ status == "partial" → 读取 data.fields_failed，在 errors/message 中告知用户，不阻塞其他字段
    ├─ status == "needs_user_input" → 将覆盖确认权交还主技能，等待用户回复
    └─ status == "failed" → 记录 errors，不阻塞其他流程
```

## 轮询示例

### 晨间轮询

```
今日营养目标（供参考）：
  总热量：1936 kcal｜蛋白：124g｜脂肪：69g｜碳水：205g
  当前阶段：维持期

请告诉我晨间数据：
1. 晨起体重是多少？
2. 体脂率是多少？
3. 排便情况？（🟢正常1次 / ⚠️异常无/少 / 🔴连续异常 / 🟢正常 / 少量）
4. 今早起床食欲如何？
```

### 晚间轮询

```
今日营养目标（供参考）：
  总热量：1936 kcal｜蛋白：124g｜脂肪：69g｜碳水：205g
  当前阶段：维持期

请告诉我今日数据（截至目前，待晚餐后补充完整）：
1. 总热量今日吃了多少？（kcal）
2. 蛋白质吃了多少？（g）
3. 脂肪吃了多少？（g）
4. 碳水吃了多少？（g）
5. 今天训练了吗？（训练日/休息日）
   → 训练日：训练内容是什么？感受如何？
```

## 睡眠数据归属

入睡时间统一记录在起床日期那一行。详见 `knowledge/sleep-rules.md`。

## 讯记同步调用

如果当前是最晚时段轮询，调用 `sync-xunji` 填充当日未录入的空白字段。详见 `skills/sync-xunji/SKILL.md`。
