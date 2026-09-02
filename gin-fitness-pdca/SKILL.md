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

阶段 1/4：周边界与数据拉取
Progress:
- [ ] Step 1 计算本周周号与日期边界 [自动]
- [ ] Step 2 发送开始通知 [自动]
- [ ] Step 3 读取本期 7 天数据与上期输出表 [自动]  ← 当前

阶段 2/4：数据质量校验 [待开始]
阶段 3/4：扫描与报告生成 [待开始]
阶段 4/4：写入与通知 [待开始]
```

cron 定时触发为无人值守场景，不输出完整对话 checklist（由飞书开始通知承担告知职责）。

## 进度条使用规则

本 skill 采用 Progress Checklist 设计模式。每次触发、每次阶段跳转、每次会话恢复时，必须向用户展示当前进度：

1. **被用户直接触发时**：先输出阶段定位句 + 当前阶段微观 checklist。
2. **被 core 或其他 skill 调用时**：只展示本环节 micro-checklist，不重复展示完整宏观 4 阶段仪表盘。
3. **进入新阶段后**：更新 checklist，已完成步骤标记为 `[✓]`，当前步骤标记为 `← 当前`。
4. **遇到硬闸门时**：输出 `⚠️ 当前阻塞：...` 及可选操作。
5. **会话中断后恢复时**：读取 `progress.md`，输出完整 4 阶段进度状态，从当前步骤继续。
6. **用户要求回退时**：根据回环映射表重置后续步骤状态，checklist 同步更新。

checklist 步骤标签：

| 标签 | 含义 |
|------|------|
| `[自动]` | AI/脚本自动执行，无需用户输入 |
| `[需确认]` | 需要用户查看并确认，但非强制通过 |
| `[硬闸门]` | 用户不通过则无法继续下一步 |
| `[可回环]` | 用户提出修改时，返回前面步骤重做 |

### 宏观 4 阶段映射

**初始化流程**：

| 阶段 | 包含步骤 | 关键硬闸门 |
|---|---|---|
| 阶段 1/4：环境准备 | 检测 lark-cli、询问电子表格链接 | 询问电子表格链接 |
| 阶段 2/4：表结构确认 | 验证表格和子表存在、读取表头并建立字段映射 | 字段映射确认 |
| 阶段 3/4：目标配置 | 询问目标参数、询问定时时间 | 目标参数、定时时间 |
| 阶段 4/4：持久化与注册 | 保存 config.json、注册 cron | 无 |

**主流程**：

| 阶段 | 包含步骤 | 关键硬闸门 |
|---|---|---|
| 阶段 1/4：周边界与数据拉取 | 计算周号、发送开始通知、读取数据 | 无 |
| 阶段 2/4：数据质量校验 | 执行数据质量双闸 | 数据质量双闸 |
| 阶段 3/4：扫描与报告生成 | M1-M9 扫描、生成 9 字段报告 | 无 |
| 阶段 4/4：写入与通知 | 写入周表并回执确认、发送完成通知 | 无 |

### 回环映射

| 用户指令 | 回退目标 | 适用流程 |
|---|---|---|
| "重新映射字段" / "字段映射不对" | 初始化 Step 4 | init |
| "修改目标" / "目标参数错了" | 初始化 Step 5 | init |
| "修改定时" / "换个时间" | 初始化 Step 6 | init |
| "重新校验数据" | 主流程 Step 4 | main |
| "重新扫描" | 主流程 Step 5 | main |
| "重新生成报告" | 主流程 Step 6 | main |

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

**当前版本**：v1.4.0  
**最后更新**：2026-09-02

本技能的每一次优化和更新，都必须在 `changelog.md` 追加一条记录，包含**日期、版本号、更新内容**三项，新记录追加在最上方。版本号采用语义化版本：主版本.次版本.修订号（破坏性改流程进主版本，新增功能进次版本，修复进修订号）。完成修改后先更新 changelog，再视为本次修改完成。

## 资源索引

| 场景 | 读取 |
|------|------|
| 初始化（8 步 4 阶段，含 Progress checklist、标签、阻塞提示、回环路径） | `references/pdca-init.md` |
| 主流程调度（8 步 4 阶段，含 Progress checklist、数据质量双闸、关键禁令、知识库调用） | `references/main-flow.md` |
| 进度条渲染与阶段校验 | `scripts/progress_reporter.py` + `scripts/stage_validator.py` + `scripts/progress_store.py` |
| 周号计算与周边界 | `references/周计算规则.md` / `scripts/week_number.py` |
| 飞书 Sheets 与 lark-cli 用法、CellValue 格式 | `references/工具映射.md` + `references/sheets-calling-patterns.md` |
| 错误分类、重试策略、终止条件 | `references/错误处理.md` |
| M1-M9 判定阈值与组合规则 | `references/m1-m9扫描规则.md` |
| 9 字段报告生成、缺轴降级、下周行动方法论 | `references/pdca-summary.md` |
| 写入与回执确认 | `references/pdca-write.md` + `references/输出表结构.md` + `scripts/coerce_value.py` |
| 通知发送 | `references/pdca-notify.md` + `references/话术模板.md` |
| 减脂速度与调整方法论（阈值依据） | `knowledge/减脂速度评估与调整频率指南.md` |
| 每次修改技能后追加更新记录 | `changelog.md` |
