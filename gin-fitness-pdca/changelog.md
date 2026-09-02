# Changelog — gin-fitness-pdca

> 规则：本技能的每一次优化和更新，都必须在本文件追加一条记录，包含**日期、版本号、更新内容**三项。新记录追加在最上方。版本号采用语义化版本：主版本.次版本.修订号（破坏性改流程进主版本，新增功能进次版本，修复进修订号）。

## v1.4.0 — 2026-09-02

- 新增：Progress Checklist 进度条体系，初始化与主流程均升级为"4 阶段 + 步骤标签"可视化
- 新增：`scripts/progress_reporter.py` 统一渲染宏观/微观 checklist
- 新增：`scripts/stage_validator.py` 阶段合法性校验、非法跳跃拦截、回环目标解析
- 新增：`scripts/progress_store.py` 与 `progress.md` 持久化，支持会话中断恢复
- 新增：硬闸门阻塞提示、回环规则（重新映射字段 / 修改目标 / 修改定时 / 重新校验 / 重新扫描 / 重新生成报告）
- 更新：`SKILL.md` 新增"进度条使用规则"章节，更新触发反馈、资源索引与版本号
- 更新：`references/pdca-init.md` 与 `references/main-flow.md` 补充 Progress checklist、标签、阻塞提示、会话恢复、回环规则
- 新增测试：`tests/test_progress_reporter.py`、`tests/test_stage_validator.py`、`tests/test_progress_store.py`

## v1.3.1 — 2026-08-26

- 新增：`references/sheets-calling-patterns.md` 模式 9 `read_column_formats`，写入前读取真实列约束
- 优化：`references/pdca-write.md` 写入流程增加真实列约束探查步骤，明确文本/日期字段直接写入，数字/百分比/时间/单选/多选字段必须经 `scripts/coerce_value.py` 转换
- 复用：新增 `scripts/coerce_value.py` 软链接，复用健身追踪的通用值转换脚本
- 更新：`SKILL.md` 资源索引增加 `scripts/coerce_value.py`

## v1.3.0 — 2026-08-26

- 重构：存储后端从飞书多维表格（Bitable）迁移到飞书电子表格（Sheets）
- 变更：`config.json` 从 `input_app_token` / `input_table_id` / `output_app_token` / `output_table_id` 改为 `spreadsheet_url` + `daily_sheet_name` + `pdca_sheet_name`
- 变更：所有 `lark-cli base` 调用改为 `lark-sheets` skill 调用
- 变更：日期字段写入格式从毫秒时间戳改为 `YYYY-MM-DD`
- 新增：`references/sheets-calling-patterns.md`，定义 PDCA 场景下的 8 种 Sheets 调用模式

## v1.2.2 — 2026-08-20

- 修复：知识库调用链路两处隐患——①m1-m9扫描规则.md 由按书名引用改为按路径引用（避免知识库扩充后歧义）；②pdca-summary.md 与 m1-m9扫描规则.md 移除硬编码数字（100~150 kcal、25~30%、0.5~1% 等），数字一律以 knowledge/ 文档原文为准，消除双写漂移风险
- 新增：main-flow.md 知识库调用规则补充「按路径引用，不按书名号引用」约定

## v1.2.1 — 2026-08-20

- 优化：提升触发准确率——description 扩充中文触发词（4 个 → 10 个）并增加意图级触发场景（周度总结/复盘/分析类请求）；增加排除项（医疗诊断、单日数据查询、闲聊式健康咨询）防止误触发；SKILL.md 正文触发词列表同步

## v1.2.0 — 2026-08-20

- 优化：SKILL.md 瘦身重构为纯总路由文件（触发识别 + 触发反馈 + 路由决策 + 边界 + 更新日志规则 + 资源索引）
- 新增：references/main-flow.md，承接主流程 8 步、数据质量双闸、关键禁令、知识库调用、首次运行说明
- 变更：终止条件从 SKILL.md 移除重复定义，统一由 references/错误处理.md 单点维护

## v1.1.0 — 2026-08-20

- 新增：本更新日志文件（changelog.md），并在 SKILL.md 中固化自动记录规则
- 新增：触发反馈——人工触发词触发后立即向用户输出固定反馈话术

## v1.0.1 — 2026-08-20

- 修复：week_number.py 跨年递归丢失天数差（1 月 1~3 日 dayOfWeek 错误），改为以上一年第一个周日为基准重算
- 修复：pdca-init.md 步骤 8 cron 注册 payload 的 skill 名与实际技能名不匹配（PDCA减脂分析 → gin-fitness-pdca）

## v1.0.0 — 2026-08-20

- 初始创建：单技能 + references 渐进披露架构
- 主流程 8 步：周号计算 → 开始通知 → 读取数据 → 数据质量双闸 → M1-M9 扫描 → 9 字段报告 → 写入回执 → 完成通知
- 知识库：knowledge/减脂速度评估与调整频率指南.md（只读调用）
- 关键决策固化：M2 阈值 0.5~1% 体重/周；进度三指标双闸（体重必选，腰围/体脂率二有一）；覆盖率 <5 天终止；初始化后不立即首析
