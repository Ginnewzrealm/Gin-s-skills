# OpenClaw 配置参考

> 由主 SKILL.md 引用。配置场景（init、排障）时读取。

## 配置键

### 存储后端选择

| 配置项 | key | 说明 |
|--------|-----|------|
| 存储后端 | `fitness.backend` | `feishu_sheets` / `local_json` / `obsidian`，默认 `feishu_sheets` |

### Sheets 后端

| 配置项 | key | 说明 |
|--------|-----|------|
| 电子表格 token | `fitness.sheets.spreadsheet_token` | 飞书电子表格 token |
| 每日记录子表 | `fitness.sheets.daily_sheet_name` | 默认 `每日记录` |
| 用户配置子表 | `fitness.sheets.config_sheet_name` | 默认 `用户配置` |
| 字段元数据子表 | `fitness.sheets.field_metadata_sheet_name` | 默认 `字段元数据`，用于定义字段时段、类型、选项、填写说明 |
| 日期列 | `fitness.sheets.date_column` | 日期所在列，默认 `A` |
| 表头行 | `fitness.sheets.header_row` | 字段名所在行，默认 `1` |
| 数据起始行 | `fitness.sheets.data_start_row` | 第一条数据所在行，默认 `2` |

### 通用配置

| 配置项 | key | 说明 |
|--------|-----|------|
| 轮询时间点 | `fitness.polling_schedule` | 用户配置的轮询时间数组，格式：`["09:00", "21:00"]` |
| 激励语 | `fitness.motivation_text` | 用户自定义激励语，无则留空 |
| 讯记 skill 状态 | `fitness.training_skill.available` | 自动检测结果 |

## 后端推断规则

`fitness.backend` 缺失时按以下规则推断：

1. 若存在 `fitness.sheets.spreadsheet_token` → 视为 `feishu_sheets`
2. 否则默认 `feishu_sheets`，并提示用户补充配置

## 事件入口

| 入口 | 触发来源 | 处理流程 | 目标分支 |
|------|----------|---------|---------|
| `user_message` | 用户主动发消息或回复轮询 | 先由 `scripts/trigger_classifier.py` 分类意图，再按模式路由 | 触发词路由 / 回复录入 |
| `cron:daily_poll` | 用户配置的轮询时间 | 直接触发 `collect-data` 每日轮询 | 每日轮询 |

`trigger_classifier.py` 输出 `mode` 后，由 `SKILL.md` 协调器按路由表调用子技能。

---
