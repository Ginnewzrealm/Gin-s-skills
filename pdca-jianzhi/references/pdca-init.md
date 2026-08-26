# 初始化流程（pdca-init 模块）

> 当 config.json 不存在或 initialized ≠ true 时读取本文件，按 8 步顺序执行，每步失败按说明处理。

## 步骤 1：检测 lark-cli

依次检测：`which lark-cli`、`~/.npm-global/bin/lark-cli`、`/usr/local/bin/lark-cli`。
失败时告知用户安装命令：`npm install -g @larksuiteoapi/node-sdk-cli`，并终止。

## 步骤 2：询问电子表格链接

话术：
```
请提供你的健身数据电子表格链接
格式：https://xxx.feishu.cn/sheets/{spreadsheet_token}
这个表格里需要包含「每日记录」和「PDCA减脂分析」两个子表。
```

从 URL 提取 spreadsheet_token，保存完整 `spreadsheet_url`。

## 步骤 3：验证表格和子表存在

调用 `lark-cli sheets +workbook-info --url "<spreadsheet_url>" --format json`。

检查返回的 `sheets[]` 中是否同时包含：
- `每日记录`（默认数据源子表，可在步骤 7 中修改 `daily_sheet_name`）
- `PDCA减脂分析`（默认输出子表，可在步骤 7 中修改 `pdca_sheet_name`）

任一不存在 → 返回 `TABLE_NOT_FOUND`，告知用户手动创建子表，不自动创建。

## 步骤 4：读取两个子表的表头

1. 调用 `lark-sheets` skill 的 `read_header` 模式读取「每日记录」表头行
2. 调用 `lark-sheets` skill 的 `read_header` 模式读取「PDCA减脂分析」表头行
3. 建立「分析维度 → 实际字段名」映射：
   - 优先匹配「字段元数据」子表中的填写说明
   - 若字段元数据不存在，按字段名语义推断（如"晨起体重"→体重）
4. 将映射展示给用户确认后再继续

## 步骤 5：询问目标参数

| 参数 | 说明 | 示例 |
|------|------|------|
| 目标体重 | kg | 58 |
| 目标腰围 | cm | 65 |
| 目标体脂率 | % | 15 |
| 目标睡眠时长 | 小时/晚 | 7 |

## 步骤 6：询问定时时间

格式：周几 + 时间。示例：周日14:00、周一08:00。

## 步骤 7：保存 config.json

在本技能目录下创建：

```json
{
  "initialized": true,
  "spreadsheet_url": "...",
  "daily_sheet_name": "每日记录",
  "pdca_sheet_name": "PDCA减脂分析",
  "target_weight": 0,
  "target_waist": 0,
  "target_bodyfat": 0,
  "target_sleep_duration": 0,
  "schedule": "..."
}
```

## 步骤 8：注册 cron

```json
{
  "action": "add",
  "schedule": "{用户配置的星期和时间，如 sunday 14:00}",
  "payload": { "kind": "agentTurn", "skill": "pdca-jianzhi", "event": "cron:pdca_weekly" }
}
```

## 完成后

结束本次会话，告知用户初始化完成。**不立即执行首次分析**——首次分析等待下次 cron 或触发词触发。
