# 企业流程现状还原确认门与流程边界 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `huanyuan-liucheng` 在用户确认资料口径和流程边界后才生成成果，并稳定输出多分支路径图、底部决策说明和待确认问题。

**Architecture:** 保留“一份 JSON 生成三份成果”的结构，在 schema 2.0 中加入确认状态、流程边界元数据、结构化问题与汇合节点。渲染器用递归分支树代替单一主线；判断细节和问题从图中移到 HTML 底部。技能文档负责判断性流程，脚本负责可机械验证的硬约束。

**Tech Stack:** Python 3 标准库、`unittest`、单文件离线 HTML/CSS、Markdown、JSON。

**Spec:** `docs/superpowers/specs/2026-11-07-huanyuan-liucheng-confirmation-boundary-design.md`

## Global Constraints

- 只还原当前现状；未来方案、规范和优化建议不进入现状流程。
- 用户明确确认前不得渲染正式文件。
- 资料缺失只生成确认问题，不生成猜测动作节点。
- 每个动作节点必须有且只有一个主体和一个业务动作。
- HTML 流程图只显示路径、节点和分支；决策说明与问题统一位于页面底部。
- 不增加第三方依赖，不加载外部脚本、字体或样式。
- 正确公司名称为“网际”；原始资料中的错误名称只作为原始证据保留。

## Review Focus

- 用户在首次上传时说“直接做”不能绕过确认门；Task 1 的未确认渲染测试覆盖。
- 结构化问题引用不存在节点时必须失败；Task 1 的引用校验测试覆盖。
- 一个决策有四个分支时每条条件都必须出现在图中；Task 2 的多分支渲染测试覆盖。
- 多个分支汇入同一节点时不能复制或丢失后续路径；Task 2 的汇合引用测试覆盖。
- 决策详情不能重新挤进流程图区域；Task 2 的区域隔离测试覆盖。

---

### Task 1: Schema 2.0 与确认门

**Files:**
- Modify: `huanyuan-liucheng/tests/test_process_model.py`
- Modify: `huanyuan-liucheng/tests/fixtures/sales-order.json`
- Modify: `huanyuan-liucheng/scripts/process_model.py`

**Interfaces:**
- Produces: `validate_model(model) -> list[str]` 对 schema 2.0 的校验；`render` 在 `confirmation.status != "confirmed"` 时返回非零且不创建输出。
- Consumes: 无。

- [ ] **Step 1: 写失败测试**

增加测试：确认状态为 `pending` 时 `render` 被拒绝且输出目录为空；缺少 `action.owner` 时失败；缺少流程边界字段时失败；结构化问题 ID 重复或引用不存在节点时失败；四分支决策通过校验。

- [ ] **Step 2: 运行测试并确认 RED**

Run: `python3 -m unittest huanyuan-liucheng.tests.test_process_model -v`

Expected: 新测试因 schema 2.0 和确认门尚未实现而失败。

- [ ] **Step 3: 最小实现 schema 2.0 校验**

在 `process_model.py` 中支持顶层 `confirmation`、流程边界字段、必填动作主体、结构化 `pending_questions` 和 `join` 节点；`render` 在未确认时退出，不创建文件。

- [ ] **Step 4: 更新销售订单 fixture**

把 `A01` 拆成“填写销售订单”和“关联客户档案”两个动作；加入确认和边界字段；问题改为 `Qxx` 对象；加入 `J01` 汇合，避免两个审批路径直接重复指向出库动作。

- [ ] **Step 5: 运行测试并确认 GREEN**

Run: `python3 -m unittest huanyuan-liucheng.tests.test_process_model -v`

Expected: Task 1 全部测试通过。

- [ ] **Step 6: Commit**

```bash
git add huanyuan-liucheng/tests/test_process_model.py huanyuan-liucheng/tests/fixtures/sales-order.json huanyuan-liucheng/scripts/process_model.py
git commit -m "feat: enforce process confirmation and boundaries"
```

### Task 2: 多分支 HTML 与底部说明

**Files:**
- Modify: `huanyuan-liucheng/tests/test_process_model.py`
- Modify: `huanyuan-liucheng/scripts/process_model.py`

**Interfaces:**
- Consumes: Task 1 的 schema 2.0、结构化问题和 `join` 节点。
- Produces: `render_html(model) -> str`，包含 `flow-map`、`decision-details`、`pending-questions` 三个有序区域。

- [ ] **Step 1: 写失败测试**

增加测试：流程图区域不含判断信息/判断标准/问题正文；决策说明和问题位于图后；四分支条件全部可见；重复目标显示汇合引用；HTML 不含外部 URL。

- [ ] **Step 2: 运行目标测试并确认 RED**

Run: `python3 -m unittest huanyuan-liucheng.tests.test_process_model.ProcessModelCliTests.test_render_separates_path_map_from_decision_details -v`

Expected: 当前 HTML 将判断详情放在节点卡片中，测试失败。

- [ ] **Step 3: 重写 HTML 路径渲染**

用递归分支结构渲染全部节点和 2–N 分支；流程卡只保留编号、主体和动作/问题；重复节点生成汇合引用。随后在页面底部渲染决策说明和结构化问题。

- [ ] **Step 4: 更新 Markdown 与问题单渲染**

从结构化问题对象读取 `id`、`text`、`related_nodes`，保证三份输出编号一致。

- [ ] **Step 5: 运行目标测试和模块测试**

Run: `python3 -m unittest huanyuan-liucheng.tests.test_process_model -v`

Expected: 模块测试全部通过。

- [ ] **Step 6: Commit**

```bash
git add huanyuan-liucheng/tests/test_process_model.py huanyuan-liucheng/scripts/process_model.py
git commit -m "feat: render complete decision paths and bottom details"
```

### Task 3: 技能行为契约与评测

**Files:**
- Modify: `huanyuan-liucheng/SKILL.md`
- Modify: `huanyuan-liucheng/references/interview-protocol.md`
- Modify: `huanyuan-liucheng/references/process-model.md`
- Modify: `huanyuan-liucheng/references/output-contract.md`
- Modify: `huanyuan-liucheng/evals/evals.json`
- Modify: `huanyuan-liucheng/agents/openai.yaml`

**Interfaces:**
- Consumes: Task 1–2 的 schema 和输出结构。
- Produces: 可被 Agent 直接执行的两阶段工作流和覆盖真实失败模式的行为评测。

- [ ] **Step 1: 更新 eval 场景**

加入混合现状/目标、多个流程被要求硬合并、审批到出库之间资料缺失、首次请求直接出成果、单节点多动作等场景；检查项描述可观察行为，不复制实现措辞。

- [ ] **Step 2: 写最小技能约束**

在 `SKILL.md` 明确确认门、流程边界、现状/目标分类、原样还原、缺失只提问、原子动作、多分支和输出顺序。将详细访谈与 schema 规则放到对应 reference，避免入口文件膨胀。

- [ ] **Step 3: 更新模型与输出文档**

使 `process-model.md` 和 `output-contract.md` 与 schema 2.0、HTML 底部结构一致；`interview-protocol.md` 提供候选流程与确认问题的形成方法。

- [ ] **Step 4: 运行技能快速校验**

Run: `python3 /Users/fubo/.codex/skills/.system/skill-creator/scripts/quick_validate.py huanyuan-liucheng`

Expected: `Skill is valid!`

- [ ] **Step 5: Commit**

```bash
git add huanyuan-liucheng/SKILL.md huanyuan-liucheng/references huanyuan-liucheng/evals/evals.json huanyuan-liucheng/agents/openai.yaml
git commit -m "docs: add confirmation-first process restoration workflow"
```

### Task 4: 样例再生成与完整验证

**Files:**
- Modify: `huanyuan-liucheng/sample-output/03 销售订单-流程说明.md`
- Modify: `huanyuan-liucheng/sample-output/03 销售订单-决策路径图.html`
- Modify: `huanyuan-liucheng/sample-output/03 销售订单-待确认问题.md`
- Verify: `huanyuan-liucheng/tests/test_copyright_notice.py`

**Interfaces:**
- Consumes: Task 1–3 的最终模型、渲染器与技能契约。
- Produces: 与 fixture 一致的样例输出和完整验证证据。

- [ ] **Step 1: 从 fixture 重新生成样例**

Run: `python3 huanyuan-liucheng/scripts/process_model.py render huanyuan-liucheng/tests/fixtures/sales-order.json --output-dir huanyuan-liucheng/sample-output`

Expected: 生成三份文件，HTML 为单文件且无外部资源。

- [ ] **Step 2: 运行技能模块测试**

Run: `python3 -m unittest discover -s huanyuan-liucheng/tests -p 'test_*.py' -v`

Expected: 全部通过，0 failures。

- [ ] **Step 3: 运行仓库完整测试**

Run: `bash run_all_tests.sh`

Expected: 全部通过，0 failures。

- [ ] **Step 4: 浏览器验证 HTML**

在桌面和窄屏打开样例 HTML，确认分支不重叠、决策说明和问题位于流程图下方、打印布局可读。

- [ ] **Step 5: 用更新后的技能复跑行为场景**

让新上下文 Agent 使用技能处理基线三个场景，确认它先提出一次性确认稿、不混入未来目标、不顺从错误合并、不创建猜测节点。

- [ ] **Step 6: Commit**

```bash
git add huanyuan-liucheng/sample-output
git commit -m "test: refresh process restoration sample outputs"
```
