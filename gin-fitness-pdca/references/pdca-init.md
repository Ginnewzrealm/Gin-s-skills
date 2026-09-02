# 初始化流程（pdca-init 模块）

> 当 config.json 不存在或 initialized ≠ true 时读取本文件，按 8 步 4 阶段顺序执行，每步失败按说明处理。
> 每次阶段切换、遇到硬闸门、会话恢复时，必须向用户展示当前 Progress checklist。

## 宏观进度

```markdown
🔄 PDCA减脂分析 · 初始化进度

阶段 1/4：环境准备
阶段 2/4：表结构确认
阶段 3/4：目标配置
阶段 4/4：持久化与注册
```

## 步骤 1：检测 lark-cli [自动]

依次检测：`which lark-cli`、`~/.npm-global/bin/lark-cli`、`/usr/local/bin/lark-cli`。
失败时告知用户安装命令：`npm install -g @larksuiteoapi/node-sdk-cli`，并终止。

## 步骤 2：询问电子表格链接 [硬闸门]

话术：
```
请提供你的健身数据电子表格链接
格式：https://xxx.feishu.cn/sheets/{spreadsheet_token}
这个表格里需要包含「每日记录」和「PDCA减脂分析」两个子表。
```

从 URL 提取 spreadsheet_token，保存完整 `spreadsheet_url`。

## 步骤 3：验证表格和子表存在 [自动]

调用 `lark-cli sheets +workbook-info --url "<spreadsheet_url>" --format json`。

检查返回的 `sheets[]` 中是否同时包含：
- `每日记录`（默认数据源子表，可在步骤 7 中修改 `daily_sheet_name`）
- `PDCA减脂分析`（默认输出子表，可在步骤 7 中修改 `pdca_sheet_name`）

任一不存在 → 返回 `TABLE_NOT_FOUND`，告知用户手动创建子表，不自动创建。

## 步骤 4：读取表头并建立字段映射 [需确认] [可回环]

1. 调用 `lark-sheets` skill 的 `read_header` 模式读取「每日记录」表头行
2. 调用 `lark-sheets` skill 的 `read_header` 模式读取「PDCA减脂分析」表头行
3. 建立「分析维度 → 实际字段名」映射：
   - 优先匹配「字段元数据」子表中的填写说明
   - 若字段元数据不存在，按字段名语义推断（如"晨起体重"→体重）
4. 将映射展示给用户确认后再继续

展示 checklist 示例：
```markdown
阶段 2/4：表结构确认
Progress:
- [✓] Step 1 检测 lark-cli [自动]
- [✓] Step 2 询问并保存电子表格链接 [硬闸门]
- [✓] Step 3 验证表格和子表存在 [自动]
- [ ] Step 4 读取表头并建立字段映射 [需确认] [可回环]  ← 当前
- [ ] Step 5 询问目标参数 [硬闸门] [可回环]
- [ ] Step 6 询问定时时间 [硬闸门] [可回环]
- [ ] Step 7 保存 config.json [自动]
- [ ] Step 8 注册 cron [自动]
```

## 步骤 5：询问目标参数 [硬闸门] [可回环]

| 参数 | 说明 | 示例 |
|------|------|------|
| 目标体重 | kg | 58 |
| 目标腰围 | cm | 65 |
| 目标体脂率 | % | 15 |
| 目标睡眠时长 | 小时/晚 | 7 |

## 步骤 6：询问定时时间 [硬闸门] [可回环]

格式：周几 + 时间。示例：周日14:00、周一08:00。

## 步骤 7：保存 config.json [自动]

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

## 步骤 8：注册 cron [自动]

```json
{
  "action": "add",
  "schedule": "{用户配置的星期和时间，如 sunday 14:00}",
  "payload": { "kind": "agentTurn", "skill": "gin-fitness-pdca", "event": "cron:pdca_weekly" }
}
```

## 完成后

结束本次会话，告知用户初始化完成。**不立即执行首次分析**——首次分析等待下次 cron 或触发词触发。

完成时 checklist：
```markdown
阶段 4/4：持久化与注册 [当前]
Progress:
- [✓] Step 1 检测 lark-cli [自动]
- [✓] Step 2 询问并保存电子表格链接 [硬闸门]
- [✓] Step 3 验证表格和子表存在 [自动]
- [✓] Step 4 读取表头并建立字段映射 [需确认] [可回环]
- [✓] Step 5 询问目标参数 [硬闸门] [可回环]
- [✓] Step 6 询问定时时间 [硬闸门] [可回环]
- [✓] Step 7 保存 config.json [自动]
- [✓] Step 8 注册 cron [自动]

✅ PDCA减脂分析初始化完成，下次触发时将自动执行周报分析。
```

## 会话恢复

如果初始化流程中断，下次触发时读取 `progress.md`，从当前未完成步骤继续，而不是从头开始。

恢复输出示例：
```markdown
🔄 PDCA减脂分析 · 初始化（恢复）

阶段 1/4：环境准备 [✓]
阶段 2/4：表结构确认 [当前]
  Progress:
  - [✓] Step 1 检测 lark-cli [自动]
  - [✓] Step 2 询问并保存电子表格链接 [硬闸门]
  - [✓] Step 3 验证表格和子表存在 [自动]
  - [ ] Step 4 读取表头并建立字段映射 [需确认] [可回环]  ← 当前
  - [ ] Step 5 询问目标参数 [硬闸门] [可回环]
  - [ ] Step 6 询问定时时间 [硬闸门] [可回环]
  - [ ] Step 7 保存 config.json [自动]
  - [ ] Step 8 注册 cron [自动]

当前阻塞：等待你审阅字段映射结果。
```

## 回环规则

当用户提出以下请求时，回退到对应步骤并重置后续 checklist 状态：

| 用户指令 | 回退目标 |
|---|---|
| "重新映射字段" / "字段映射不对" / "表头认错了" | Step 4 |
| "修改目标" / "目标参数错了" / "目标改一下" | Step 5 |
| "修改定时" / "换个时间" / "定时改一下" | Step 6 |

回退话术示例：
```markdown
返回阶段 2/4：表结构确认

阶段 1/4：环境准备 [✓]
阶段 2/4：表结构确认 [当前]
  Progress:
  - [✓] Step 1 检测 lark-cli [自动]
  - [✓] Step 2 询问并保存电子表格链接 [硬闸门]
  - [✓] Step 3 验证表格和子表存在 [自动]
  - [ ] Step 4 读取表头并建立字段映射 [需确认] [可回环]  ← 当前
  - [ ] Step 5 询问目标参数 [硬闸门] [可回环]
  - [ ] Step 6 询问定时时间 [硬闸门] [可回环]
  - [ ] Step 7 保存 config.json [自动]
  - [ ] Step 8 注册 cron [自动]
```
