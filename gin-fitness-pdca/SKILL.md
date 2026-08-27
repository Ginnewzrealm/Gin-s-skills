---
name: gin-fitness-pdca
description: PDCA减脂分析（健康数据周报自动化）。当用户说「PDCA分析」「PDCA分析一下」「本周健身总结」「健身周报」「减脂周报」「本周减脂总结」「本周PDCA」「代谢分析」「跑一下周报」「周报总结」等，或要求对本周健康/减脂/健身数据做周度总结、复盘、分析时使用；也响应 cron 定时事件 cron:pdca_weekly。功能：读取飞书电子表格的每日健康数据，执行 M1-M9 代谢问题扫描，生成 9 字段 PDCA 循环报告，自动写入 PDCA 周表并推送飞书通知。仅做减脂数据分析与决策建议；不用于医疗诊断、单日数据查询、闲聊式健康咨询。
---

# PDCA减脂分析（总路由）

本文件只做触发识别与路由，全部执行逻辑按需加载 references 子文件。

## 触发入口（双入口，汇合为同一路由）

1. **用户触发词**：PDCA分析、PDCA分析一下、本周健身总结、健身周报、减脂周报、本周减脂总结、本周PDCA、代谢分析、跑一下周报、周报总结；以及意图等价的表达（如要求对本周健康/减脂/健身数据做周度总结、复盘、分析）
2. **cron 定时事件**：`cron:pdca_weekly`（无人值守；异常时仅发飞书错误通知，无法当面追问）

## 触发反馈（仅人工触发词触发）

识别到人工触发词后、开始任何处理之前，先向用户输出固定反馈话术（每次都相同，不得改写）：

```
🔄 PDCA减脂分析进行中，正在处理本周数据，请稍候…
```

cron 定时触发为无人值守场景，不输出对话反馈（由飞书开始通知承担告知职责）。

## 路由决策

读取本技能目录下的 `config.json`：

- 不存在或 `initialized != true` → 读取 `references/pdca-init.md`，按初始化流程执行，完成后结束，等待下次触发
- `initialized == true` → 读取 `references/main-flow.md`，严格按其执行主流程

## config.json 结构

初始化完成后，本技能目录下生成 `config.json`：

```json
{
  "initialized": true,
  "spreadsheet_url": "https://xxx.feishu.cn/sheets/xxx",
  "daily_sheet_name": "每日记录",
  "pdca_sheet_name": "PDCA减脂分析",
  "target_weight": 58,
  "target_waist": 65,
  "target_bodyfat": 0.15,
  "target_sleep_duration": 7,
  "schedule": "sunday 14:00"
}
```

- `spreadsheet_url`：健身追踪电子表格 URL
- `daily_sheet_name`：每日数据源子表名（默认"每日记录"）
- `pdca_sheet_name`：PDCA 输出子表名（默认"PDCA减脂分析"）
- `target_*`：目标参数，保留在 config.json
- `schedule`：cron 定时

## 边界（不可逾越）

- 仅做减脂数据分析与决策建议
- 不提供医疗诊断建议；数据呈现疑似疾病信号时，提示用户咨询医生，不下诊断结论

## 更新日志（硬规则）

本技能的每一次优化和更新，都必须在 `changelog.md` 追加一条记录，包含**日期、版本号、更新内容**三项，新记录追加在最上方。版本号采用语义化版本：主版本.次版本.修订号（破坏性改流程进主版本，新增功能进次版本，修复进修订号）。完成修改后先更新 changelog，再视为本次修改完成。

## 资源索引

| 场景 | 读取 |
|------|------|
| 初始化（8 步：lark-cli 检测→spreadsheet URL→子表验证→字段映射→目标参数→定时→config→cron） | `references/pdca-init.md` |
| 主流程调度（8 步周报流程、数据质量双闸、关键禁令、知识库调用） | `references/main-flow.md` |
| 周号计算与周边界 | `references/周计算规则.md` / `scripts/week_number.py` |
| 飞书 Sheets 与 lark-cli 用法、CellValue 格式 | `references/工具映射.md` + `references/sheets-calling-patterns.md` |
| 错误分类、重试策略、终止条件 | `references/错误处理.md` |
| M1-M9 判定阈值与组合规则 | `references/m1-m9扫描规则.md` |
| 9 字段报告生成、缺轴降级、下周行动方法论 | `references/pdca-summary.md` |
| 写入与回执确认 | `references/pdca-write.md` + `references/输出表结构.md` + `scripts/coerce_value.py` |
| 通知发送 | `references/pdca-notify.md` + `references/话术模板.md` |
| 减脂速度与调整方法论（阈值依据） | `knowledge/减脂速度评估与调整频率指南.md` |
| 每次修改技能后追加更新记录 | `changelog.md` |
