# 训记训练计划写回桥接约定

> 触发条件：用户确认训练计划后同意写入训记时，必须先读本文件。
> 前置条件：用户环境中已安装「训记训练技能」（xunji-training）。

## 目录

1. 职责边界
2. 调用方式
3. 字段构造规则
4. 单写保证（硬规则）
5. client_request_id 规则
6. 去重规则
7. 异常处理
8. 写入后验证（硬规则）
9. 写入后反馈

## 职责边界

- 健身助手负责：构造计划数据、在当天计划存档中记录写回信息、去重判断、询问用户覆盖/新建/取消。
- 训记训练技能负责：鉴权、限频、实际调用训记写回接口、返回 `localid`；API Key 由训记训练技能自己初始化和管理，健身助手不经手。
- 健身助手不直接调用训记接口、不保存训记 API Key。

## 调用方式

调用前从 `_skill-config.json` 读取 `xunji_training_skill_name`，用该名称调用。不要硬编码 skill 名。

```text
Skill(skill="{xunji_training_skill_name}", args={
  "action": "write_plan",
  "datestr": "YYYY-MM-DD",
  "title": "练胸日",
  "body_part": "胸部",
  "client_request_id": "gin-workout-planner-YYYYMMDD-body_part_pinyin-uuid",
  "plan": {
    "movements": [
      {
        "name": "杠铃卧推",
        "sets": [
          { "done": false, "weight": "60", "unit": "kg", "reps": "10" },
          { "done": false, "weight": "60", "unit": "kg", "reps": "10" },
          { "done": false, "weight": "60", "unit": "kg", "reps": "10" }
        ]
      }
    ]
  }
})
```

如果 `_skill-config.json` 中没有 `xunji_training_skill_name`，说明未初始化或未检测到训记训练技能，此时不要调用，按未安装处理。

## 字段构造规则

- `title`：≤ 4 个汉字。部位名映射：胸部→练胸日、背部→练背日、肩臂部→练肩日、臀腿部→练臀腿日、核心腹部→练腹日。
- `datestr`：当天日期。
- `body_part`：使用健身助手内部一级部位名（胸部/背部/肩臂部/臀腿部/核心腹部）。
- `client_request_id`：`gin-workout-planner-{datestr}-{body_part_pinyin}-{plan_hash}`，同一 datestr + body_part + plan_hash 必须相同。`plan_hash` 取计划内容的短哈希或 8 位随机字符。
- `plan.movements`：从本次计划「今日动作清单」提取；动作名须是训记标准动作名；`sets` 按清单中的「组数×次数」和「负荷」展开，全部 `done: false`。
- `localid`：去重记录中已有同日期同部位记录且用户选择「覆盖」时，传入旧 `localid`。

## 单写保证（硬规则）

一次用户确认 → 一次 `write_plan` 调用 → 训记里新增/更新一条训练记录。任何情况下都不允许同一计划被写入多次。

实现机制：

1. **调用前去重检查**：读取当天计划存档 `03-训练计划/{datestr}-{body_part}*.md`（同部位多次可能有 `-2` 后缀， glob 匹配）：
   - 存档的 **frontmatter `训记写回:` 行有记录**（已写入过）→ 必须停下来问用户「覆盖 / 新建 / 取消」，不允许静默新建；覆盖时取**最新一份**存档的 localid。
   - **没有 `训记写回:` 行**（未写入过，或用户当时拒绝写训记）→ 直接新建。
2. **调用前加写锁**：调用 `Skill` 之前，创建临时锁文件 `03-训练计划/.locks/.writing-lock-{datestr}-{body_part_pinyin}`：
   - 锁文件已存在 → 说明正在写入中或上次异常中断，禁止再次调用；向用户说明"正在处理，请稍等"。
   - 锁文件不存在 → 创建锁文件，然后调用。
3. **调用后立刻记录并解锁**：
   - 写入成功 → 在当天存档 frontmatter 补写 `训记写回:` 行（格式见「去重规则」），然后删除锁文件。
   - 写入失败 → 删除锁文件，不写回记录，向用户报告错误。
4. **禁止重试**：`trains-train-writeback.md` 和 `xunji-training` 技能都禁止自动重试。一次调用失败后，必须等用户明确说"再试一次"才能再次调用。

## client_request_id 规则

`client_request_id` 必须对同一份计划保持一致：

```
gin-workout-planner-{datestr}-{body_part_pinyin}-{plan_hash}
```

其中 `plan_hash` 取计划内容（动作名、组数、次数、负荷）的短哈希或 8 位随机字符。**同一 datestr + body_part + plan_hash 必须生成相同的 client_request_id**，这样即使意外调用两次，训记服务端如果支持幂等也能去重。

## 去重规则

**写没写过训记，记在当天计划存档里，没有独立账本文件。**

1. 定位当天存档：glob `03-训练计划/{datestr}-{body_part}*.md`（`body_part` 用健身助手内部一级部位名：胸部/背部/肩臂部/臀腿部/核心腹部）。
2. 存档存在、且 frontmatter 含 `训记写回:` 行 → **已写入过**：向用户展示该行内容（localid、写入时间）并询问：「训记里今天已有 {body_part} 计划，覆盖 / 新建 / 取消？」；用户选「覆盖」时，取**最新一份**存档（`-2` 后缀等）的 localid 传入。
3. 存档不存在，或存档存在但 frontmatter **没有** `训记写回:` 行 → **未写入过**（可能是用户当时拒绝写训记，也可能是存档后流程中断）→ 直接新建。
4. 写入成功后，在存档 frontmatter 补写 `训记写回:` 行，格式：

```markdown
---
训练日期: 2026-08-22
训练部位: 胸部
训记写回: 已写入｜localid: 123456｜client_request_id: gin-workout-planner-20260822-xiongbu-a1b2c3d4｜2026-08-22T10:30:00+08:00
---
```

   - 一行四段固定顺序：`已写入｜localid: {localid}｜client_request_id: {client_request_id}｜{written_at 时间戳}`。
   - 覆盖更新时改写该行为最新值；禁止在正文追加第二行 `训记写回:`。
   - 已写入过但当天有多份存档（`-2` 后缀）：只在本次实际写入对应的存档文件上记录；去重检查时以最新一份为准。

## 异常处理

| 情况 | 处理 |
|------|------|
| 训记训练技能未安装 | 告知用户未安装，仅本地存档 |
| 调用返回 error | 展示 error_msg，不写回记录 |
| 返回缺少 localid | 视为失败，不写回记录 |
| 动作名不在训记标准名表 | 写回前让用户确认标准名；无法确认则不写回 |
| 超出训记限制 | 提示用户精简计划 |

## 写入后验证（硬规则）

调用 `Skill` 返回后，必须解析响应并按以下规则判断，**未确认结果前禁止重试**：

1. **成功判定**：响应中 `success === true`。
   - 即使响应里有 `res` / `res.trains` / `localid` 等看起来像训练记录的数据，也属于**写入成功的回执**，不是读取接口返回。
   - 从 `res.trains[0].localid` 提取 `localid`，按「去重规则」的格式写入当天存档 frontmatter 的 `训记写回:` 行。
   - 向用户反馈：「计划已写入训记，标题「{title}」，存档已记录。」

2. **失败判定**：响应中 `success === false` 或 `success` 字段不存在。
   - 原样展示 `error` 信息给用户。
   - **不写回记录，不解锁后重试，不自动再次调用**。
   - 话术：「写入训记失败了：{error}。**我不会自动重试。**如果你确认要我重新试，请说"重新试"或"再试一次"。」——只有用户明确说"重新试"或"再试一次"时，才能再次调用。
   - 如果 `error` 包含 `retry after Xs`，告诉用户「请等待 X 秒后再说"重新试"」。

3. **结果不明确**（响应解析失败、既无 `success` 也无 `error`）：
   - 向用户说明"训记返回了无法识别的结果"。
   - 不写回记录。
   - 不自动重试。

## 写入后反馈

向用户反馈：「计划已写入训记，标题「{title}」。存档已记录写回信息。」
