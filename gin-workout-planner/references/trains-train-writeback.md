# 训记训练计划写回桥接约定

> 触发条件：用户确认训练计划后同意写入训记时，必须先读本文件。
> 前置条件：用户环境中已安装「训记训练技能」（xunji-training）。

## 职责边界

- 健身助手负责：构造计划数据、生成本地写回记录、去重判断、询问用户覆盖/新建/取消。
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

- `title`：≤ 4 个汉字。部位名映射：胸部→练胸日、背部→练背日、肩臂部→练肩日、臀髋部→练臀日、腿部→练腿日、核心腹部→练腹日。
- `datestr`：当天日期。
- `body_part`：使用健身助手内部一级部位名（胸部/背部/肩臂部/臀髋部/腿部/核心腹部）。
- `client_request_id`：`gin-workout-planner-{datestr}-{body_part_pinyin}-{plan_hash}`，同一 datestr + body_part + plan_hash 必须相同。`plan_hash` 取计划内容的短哈希或 8 位随机字符。
- `plan.movements`：从本次计划「今日动作清单」提取；动作名须是训记标准动作名；`sets` 按清单中的「组数×次数」和「负荷」展开，全部 `done: false`。
- `localid`：去重记录中已有同日期同部位记录且用户选择「覆盖」时，传入旧 `localid`。

## 单写保证（硬规则）

一次用户确认 → 一次 `write_plan` 调用 → 训记里新增/更新一条训练记录。任何情况下都不允许同一计划被写入多次。

实现机制：

1. **调用前读去重记录**：读取 `plan-writeback-log.json`，若 `datestr + body_part` 已存在记录，必须停下来问用户「覆盖 / 新建 / 取消」，不允许静默新建。
2. **调用前加写锁**：调用 `Skill` 之前，创建临时锁文件 `.xunji-writeback/.writing-lock-{datestr}-{body_part_pinyin}`：
   - 锁文件已存在 → 说明正在写入中或上次异常中断，禁止再次调用；向用户说明"正在处理，请稍等"。
   - 锁文件不存在 → 创建锁文件，然后调用。
3. **调用后立刻更新记录并解锁**：
   - 写入成功 → 把记录追加到 `records`，写回完整 JSON，然后删除锁文件。
   - 写入失败 → 删除锁文件，不更新记录，向用户报告错误。
4. **禁止重试**：`trains-train-writeback.md` 和 `xunji-training` 技能都禁止自动重试。一次调用失败后，必须等用户明确说"再试一次"才能再次调用。

## client_request_id 规则

`client_request_id` 必须对同一份计划保持一致：

```
gin-workout-planner-{datestr}-{body_part_pinyin}-{plan_hash}
```

其中 `plan_hash` 取计划内容（动作名、组数、次数、负荷）的短哈希或 8 位随机字符。**同一 datestr + body_part + plan_hash 必须生成相同的 client_request_id**，这样即使意外调用两次，训记服务端如果支持幂等也能去重。

## 去重规则

1. 读取 `{knowledge_base_root}/.xunji-writeback/plan-writeback-log.json`，解析为 JSON。
2. 文件结构必须是 `{ "schema_version": "1.0", "records": [...] }`。
   - 若文件是旧版空数组 `[]` 或其他异常结构 → 先按规范重建为 `{ "schema_version": "1.0", "records": [] }`，并向用户报告"已修复写回记录格式"。
   - 也可运行修复脚本：`python3 scripts/repair_writeback_log.py <plan-writeback-log.json 路径>`。
3. 以 `datestr + body_part` 查询 `records` 数组。
4. 已存在记录 → 向用户展示旧记录（`title`、`written_at`）并询问：「训记里今天已有 {body_part} 计划，覆盖 / 新建 / 取消？」
5. 不存在 → 直接新建。
6. 写入成功后，把新记录 `{localid, client_request_id, title, datestr, body_part, written_at}` 追加到 `records` 数组；若覆盖则更新原记录。
7. **写回文件时必须是完整结构**：

```json
{
  "schema_version": "1.0",
  "records": [
    {
      "datestr": "2026-08-22",
      "body_part": "胸部",
      "localid": 123456,
      "client_request_id": "gin-workout-planner-20260822-xiongbu-uuid",
      "title": "练胸日",
      "written_at": "2026-08-22T10:30:00+08:00"
    }
  ]
}
```

禁止只写 `records` 数组或空数组到文件。

## 异常处理

| 情况 | 处理 |
|------|------|
| 训记训练技能未安装 | 告知用户未安装，仅本地存档 |
| 调用返回 error | 展示 error_msg，不更新本地记录 |
| 返回缺少 localid | 视为失败，不更新本地记录 |
| 动作名不在训记标准名表 | 写回前让用户确认标准名；无法确认则不写回 |
| 超出训记限制 | 提示用户精简计划 |

## 写入后验证（硬规则）

调用 `Skill` 返回后，必须解析响应并按以下规则判断，**未确认结果前禁止重试**：

1. **成功判定**：响应中 `success === true`。
   - 即使响应里有 `res` / `res.trains` / `localid` 等看起来像训练记录的数据，也属于**写入成功的回执**，不是读取接口返回。
   - 从 `res.trains[0].localid` 提取 `localid`，保存到本地写回记录。
   - 向用户反馈：「计划已写入训记，标题「{title}」，本地记录已更新。」

2. **失败判定**：响应中 `success === false` 或 `success` 字段不存在。
   - 原样展示 `error` 信息给用户。
   - **不更新本地写回记录，不解锁后重试，不自动再次调用**。
   - 话术：「写入训记失败了：{error}。**我不会自动重试。**如果你确认要我重新试，请说"重新试"或"再试一次"。」——只有用户明确说"重新试"或"再试一次"时，才能再次调用。
   - 如果 `error` 包含 `retry after Xs`，告诉用户「请等待 X 秒后再说"重新试"」。

3. **结果不明确**（响应解析失败、既无 `success` 也无 `error`）：
   - 向用户说明"训记返回了无法识别的结果"。
   - 不更新本地记录。
   - 不自动重试。

## 写入后反馈

向用户反馈：「计划已写入训记，标题「{title}」。本地写回记录已更新。」
