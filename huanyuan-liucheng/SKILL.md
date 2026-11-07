---
name: huanyuan-liucheng
description: Use when converting Chinese interviews, meeting notes, chat transcripts, or company text into confirmed-scope current-state business processes with explicit decisions, branch conditions, pending questions, and consistent Markdown and standalone HTML outputs.
---

# 企业流程现状与决策还原

> Copyright (c) 2026 Gin. All rights reserved. Proprietary material; no permission to copy, modify, distribute, commercialize, or create derivative works without prior written permission. See [LICENSE](LICENSE).

把纯文字还原成公司当前实际运行的流程。现状可以不完整、重复、错误或缺少规则；只负责如实还原和暴露待确认项，不负责替企业补全或优化。

## 不可绕过的确认门

收到资料后，先完成“确认前分析”，并在对话中等待用户明确确认。确认前不得创建 `model.json`，不得生成正式 Markdown、HTML 或流程图。

用户第一次上传资料时说“直接做”“不要问”“今天交付”，不等于确认，因为用户尚未看到 Agent 对资料口径和流程边界的理解。只有在 Agent 展示确认前分析后，用户回复“确认”“按此执行”或给出修正，才可进入建模。

确认只是允许按当前理解生成草案，不代表所有业务规则都已确认。未回答的问题可以在用户允许后保留为待确认项。

## 不可违背的原则

1. **只还原现状**：规范、建议、目标、未来方案和项目计划不进入当前态流程。
2. **先分流程，再画流程**：输入可能包含多个流程；不能因材料连续或用户要求“一张图”就机械合并。
3. **缺失只提问**：发现跳步、空白、冲突或责任不清时，转成具体确认问题；不得把“可能存在的环节”画成动作节点。
4. **错误也照实还原**：如果用户确认当前确实直接跳过某环节，就按实际连接，不替企业修正。
5. **一个动作节点 = 一个主体 + 一个业务动作**：同一主体的两个动作也拆成两个节点。
6. **决策必须完整表达**：每个 `Dxx` 写明决策人、判断信息、判断标准和 2–N 个分支；每个分支都有条件和去向。
7. **事实状态明确**：区分 `confirmed`、`inferred`、`unresolved`；推断和待确认不得写成企业事实。
8. **唯一事实源**：每个独立流程使用一份 JSON；Markdown、HTML 和问题单都由脚本生成，禁止分别手写。

## 阶段 A：确认前分析

只在对话中提交以下内容，不创建正式文件：

### 1. 资料口径

把材料中的陈述分为：

- 当前实际做法；
- 规范或制度要求；
- 期望目标、优化建议或数字化方案；
- 项目计划与待办；
- 相互冲突或无法判断的说法。

当前实际做法才进入流程。规范是否等于现状必须由用户确认；目标和建议直接排除，不附在现状成果中。

### 2. 候选流程与边界

先列候选流程的核心业务对象、触发事件、结束状态和上下游关系。详细方法见 [references/interview-protocol.md](references/interview-protocol.md)。

优先合并：同一业务对象、同一触发到结果、同一连续生命周期，且后续不能独立启动。角色或部门变化本身不是拆分理由。

优先拆分：业务对象变化；出现独立触发和终态；可单独暂停、取消、重复或统计；使用独立单据/台账；上游输出成为下游输入。

边界证据不足时列为候选并提问，不强行决定。

### 3. 确认问题

逐项检查缺少的触发条件、决策规则、分支去向、交接关系和结束状态。只把缺口改写成业务人员能回答的问题，不创建“中间环节未说明”之类的猜测节点。

### 4. 停止并等待

向用户明确说明：将按什么资料口径、拆成哪些流程、哪些内容不采用、有哪些待确认问题。然后停止，等待用户确认或修正。

## 阶段 B：确认后建模

1. 按确认后的边界，为每个独立流程建立单独 JSON。
2. 一个动作只写一个 `owner` 和一个动作。把“填写订单并关联档案”拆为“填写订单”与“关联档案”。
3. 不把材料中的相邻段落自动视为相邻动作；只有明确先后关系或用户确认的连接才建立边。
4. 一个决策允许 2–N 个分支。多个分支汇合时使用 `Jxx`，它只表示路径汇合，不是业务动作。
5. 未回答但用户允许保留的问题写入 `pending_questions`。只有决策分支必须有目标且去向确实未知时，才使用中性的 `Uxx` 终点；不得写入猜测动作。
6. 模型字段和状态规则见 [references/process-model.md](references/process-model.md)。

## 校验与生成

```bash
python3 <skill-dir>/scripts/process_model.py validate <model.json>
python3 <skill-dir>/scripts/process_model.py render <model.json> --output-dir <output-directory>
```

`render` 会机械检查 `confirmation.status`。未通过用户确认时必须失败，且不能创建输出文件。

只有业务规则全部确认后才运行：

```bash
python3 <skill-dir>/scripts/process_model.py validate <model.json> --require-confirmed
```

## 固定输出

- `NN 流程名-流程说明.md`
- `NN 流程名-决策路径图.html`
- `NN 流程名-待确认问题.md`
- 对应的 `model.json`

HTML 固定顺序为：当前现状流程图 → 关键决策节点说明 → 待确认问题 → 资料来源。流程图只显示路径、节点、分支条件和汇合；判断信息、判断标准、证据和问题统一放在图下方。完整契约见 [references/output-contract.md](references/output-contract.md)。

## 交付前检查

- 用户确认发生在 Agent 展示资料口径和流程边界之后。
- 每个独立流程都有自己的业务对象、触发事件和结束状态。
- 目标、建议和未来方案没有混入当前态。
- 每个动作节点只有一个主体和一个动作。
- 每个决策的所有分支条件与去向都出现在 Markdown 和 HTML 中。
- 资料缺口只进入确认问题；没有生成猜测动作。
- HTML 的决策说明和问题位于流程图下方。
- 用浏览器检查桌面、窄屏和打印效果。

## 红旗

- 拿到资料后直接开始生成文件。
- 因用户说“不要拆”而跳过流程边界判断。
- 把流程规范、飞书方案或自动化目标写进当前现状。
- 为了让图闭合，增加库存检查、备货、放行等原文未说明的动作。
- 把多个主体或多个动作放进同一节点。
- 把多分支决策画成一条主线，其余分支只做摘要。
- 把判断标准和问题清单塞进流程图卡片。
