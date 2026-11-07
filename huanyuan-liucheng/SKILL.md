---
name: huanyuan-liucheng
description: Use when converting Chinese natural-language interviews, meeting notes, chat transcripts, or plain-text company materials into a current-state business process with explicit decisions, branch conditions, pending questions, and consistent Markdown and standalone HTML outputs.
---

# 企业流程与决策还原

把纯文字中的公司实际运行方式还原成可审阅的流程。重点不是画得复杂，而是让每个关键决策的判断信息、判断标准、分支条件和去向一眼可见。

## 不可违背的原则

1. 只还原输入资料；不把常识、建议或模型猜测写成企业事实。
2. 区分三类内容：`confirmed`（原文明确）、`inferred`（由原文逻辑推出但未直接说明）、`unresolved`（缺失或冲突）。
3. 只要后续动作取决于条件、审批、判断或选择，就建立独立的 `Dxx` 决策节点，不把它埋进动作描述。
4. 每个决策必须写明：决策人、判断信息、判断标准、所有分支、每个分支的条件和去向。
5. 资料不足时仍生成草案，用红色待确认分支和问题单暴露缺口；不得停下来补造规则。
6. Markdown 和 HTML 必须从同一份 JSON 生成，禁止分别手写后再人工同步。

## 工作流程

### 1. 整理原始文字

- 识别流程名称、范围、起点、终点、角色、动作、单据、系统和时间顺序。
- 从“如果、是否、超过、否则、同意、拒绝、退回、异常、谁审批”等表达中识别决策。
- 将“现在怎么做”与“希望以后怎么做”分开；默认只建当前运行现状。
- 对矛盾、缺失阈值、未说明的拒绝路径和模糊责任人标记 `unresolved`。

详细提取方法见 [references/interview-protocol.md](references/interview-protocol.md)。

### 2. 建立唯一流程模型

先创建 JSON，不直接画图。字段和状态规则见 [references/process-model.md](references/process-model.md)。完整示例见 [tests/fixtures/sales-order.json](tests/fixtures/sales-order.json)。

要求：

- 节点按 `S01`、`A01`、`D01`、`U01`、`T01` 编号。
- 每个 `decision` 至少有两个分支；每个分支都有非空 `condition` 和有效 `target`。
- 每个决策恰好一个 `primary=true`，只用于确定 HTML 中央主线；它不代表分支更重要。
- 所有路径最终到达 `terminal` 或 `unresolved`。
- 所有待确认事实同步写入 `pending_questions`，问题应能由业务人员直接回答。

### 3. 校验模型

将 `<skill-dir>` 替换为本文件所在目录：

```bash
python3 <skill-dir>/scripts/process_model.py validate <model.json>
```

发现错误先修 JSON，不要改渲染结果绕过校验。只有业务方已确认全部规则时，才运行严格校验：

```bash
python3 <skill-dir>/scripts/process_model.py validate <model.json> --require-confirmed
```

### 4. 生成固定输出

```bash
python3 <skill-dir>/scripts/process_model.py render <model.json> --output-dir <output-directory>
```

必须交付：

- `NN 流程名-流程说明.md`：完整文字决策树、每个决策的判断信息/标准/分支、待确认问题。
- `NN 流程名-决策路径图.html`：可单独打开的视觉决策图；蓝色动作、黄色决策、红色其他或待确认分支、绿色终态。
- `NN 流程名-待确认问题.md`：下一轮访谈清单。
- 原始 `model.json`：两种输出的唯一事实来源，随结果一并保留。

输出契约见 [references/output-contract.md](references/output-contract.md)。

### 5. 交付前检查

- 逐个核对 `Dxx`：问题、决策人、判断信息、标准、分支条件、去向均存在。
- 搜索原文，确认 `confirmed` 都有文字依据；无法指回原文的内容降为 `inferred` 或 `unresolved`。
- 确认 Markdown 与 HTML 的决策编号集合完全相同。
- 用浏览器实际打开 HTML，检查中央主线、右侧分支、长文字、小屏换行和打印效果。
- 不直接编辑生成的 Markdown/HTML；需要修改时更新 JSON 后重新渲染。

## 快速判断表

| 输入情况 | 处理 |
|---|---|
| 原文明确说明规则和去向 | `confirmed` |
| 由原文逻辑可推出，但原文没有直接说 | `inferred`，并写明依据 |
| 阈值、责任人、组合关系或拒绝路径缺失 | `unresolved` + 待确认问题 |
| 同一资料出现冲突规则 | 两条都保留为证据，适用关系标 `unresolved` |
| 用户只给少量对话 | 生成可用草案，不补造，红色暴露缺口 |
| 用户要求建议未来流程 | 与当前现状分文件处理，不混在同一模型 |

## 红旗

- 把“通常、应该、一般公司会”改写成该公司的既定规则。
- 只有“是/否”分支名，没有可执行的分支条件。
- 决策图漂亮，但缺少拒绝、异常、退回或绕行路径。
- 在 Markdown 和 HTML 中使用不同编号或不同条件。
- 为了让流程闭合，擅自决定金额阈值、审批人、时限或失败后的处理方式。
