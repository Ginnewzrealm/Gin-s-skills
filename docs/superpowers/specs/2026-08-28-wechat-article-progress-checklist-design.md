# 微信公众号写作技能组 Progress checklist 设计

> 版本：v1.0  
> 日期：2026-08-28  
> 范围：`gin-wechat-article-core` 及 7 个微信公众号写作子 skill

---

## 1. 背景与目标

微信公众号写作技能组已经具备完整的主编排流程（`gin-wechat-article-core` 17 个内部 stage + 7 个子 skill），但存在两个体验问题：

1. **跳跃步骤**：用户或 AI 可能跳过本应先完成的阶段（如未确认大纲就写正文）。
2. **阶段不清**：用户不知道当前做到哪一步、下一步是什么、卡在哪个环节。

本设计借鉴 `bigpeng-resume-generate` 的 Progress checklist 设计思想，以及仓库内 `gin-resume-builder` 已落地的 `[自动]/[需确认]/[硬闸门]/[可回环]` 标签实践，为微信公众号写作技能组增加统一的进度展示层。

---

## 2. 设计概述

### 2.1 核心原则

- **展示层级分离**：`gin-wechat-article-core` 负责宏观 6 阶段仪表盘，7 个子 skill 负责本环节 micro-checklist。
- **标签统一**：沿用 4 种步骤标签，与 `gin-resume-builder` 保持一致。
- **调用方式差异化**：子 skill 被 core 调用时不重复展示完整 6 阶段；单独调用时补充阶段定位句。
- **会话恢复友好**：中断恢复时展示全部 6 阶段 + 当前步骤高亮。

### 2.2 架构图

```
用户触发 gin-wechat-article-core
  ↓
core 读取 progress.md / context.md
  ↓
stage_validator 决定当前 stage
  ↓
调用 progress_reporter.render_macro() 输出 6 阶段仪表盘
  ↓
硬闸门 → 等待用户确认
  ↓
调用子 skill
  ↓
子 skill 调用 progress_reporter.render_micro() 输出 micro-checklist
  ↓
子 skill 执行完成返回 core
  ↓
core 更新 progress.md，再次输出宏观仪表盘
```

---

## 3. 6 个宏观阶段

将内部 17 个 stage 聚合为 6 个用户可见阶段：

| 宏观阶段 | 内部 stage | 核心产出 | 关键硬闸门 |
|---|---|---|---|
| 阶段 1/6：初始化与需求澄清 | init, clarify | context.md, selected_template, requirements | 需求记录确认 |
| 阶段 2/6：素材诊断与角度选择 | template_loaded, angle_diagnosed, role_boundary | narrative_protocol, angle_candidates, diagnosis_report | 人-AI 协作契约书确认 |
| 阶段 3/6：大纲生成与确认 | angle_matched, outline_generated, outline_selected, outline_confirmed | selected_outline | 大纲选择 + 开始写正文确认 |
| 阶段 4/6：正文写作与人工改写 | draft_written, draft_revised | article_draft.md, draft_revised.md | 人工二次改写确认 |
| 阶段 5/6：润色、小标题与标题优化 | polished, titled, title_confirmed | polished_draft.md, selected_title | 标题确认 |
| 阶段 6/6：质量检查与终审定稿 | quality_checked, finalized, markdown_output, publish_decision | final_article.md | 终审定稿确认 |

### 3.1 core 输出示例

```markdown
📝 公众号长文写作进度

阶段 1/6：初始化与需求澄清
- [x] 检查配置路径 [自动]
- [x] 选择风格模板 [自动]
- [ ] 确认主题、读者、核心观点 [硬闸门]  ← 当前

阶段 2/6：素材诊断与角度选择 [待开始]
阶段 3/6：大纲生成与确认 [待开始]
阶段 4/6：正文写作与人工改写 [待开始]
阶段 5/6：润色、小标题与标题 [待开始]
阶段 6/6：质量检查与终审定稿 [待开始]
```

---

## 4. 步骤标签定义

沿用 `gin-resume-builder` 的 4 种标签：

| 标签 | 含义 | 用户行为 |
|---|---|---|
| `[自动]` | AI/脚本自动执行，无需用户实时参与 | 观看结果 |
| `[需确认]` | 需要用户查看或回应，但不强制通过 | 可回应，也可让 AI 继续等待 |
| `[硬闸门]` | 用户不通过则无法继续下一步 | 必须明确说 OK / 批准 / 继续 |
| `[可回环]` | 用户提出修改时，可回退到前面步骤重做 | 输入"重新生成"/"修改"等 |

---

## 5. 子 skill micro-checklist

### 5.1 展示规则

| 调用方式 | 展示内容 |
|---|---|
| 被 `gin-wechat-article-core` 调用 | 只展示本阶段 micro-checklist（不展示完整 6 阶段标题） |
| 被用户直接调用 | 先展示阶段定位句，再展示 micro-checklist |

阶段定位句示例：

```markdown
当前处于公众号长文写作的阶段 3/6：大纲生成与确认。
```

### 5.2 `gin-wechat-article-clarify`

```markdown
阶段 1/6：初始化与需求澄清
Progress:
- [ ] Step 1 读取已有素材与已选模板信息 [自动]
- [ ] Step 2 结构化访谈：确认主题/读者/核心观点/字数 [需确认]  ← 当前
- [ ] Step 3 确认说话位置与素材完整性 [需确认]
- [ ] Step 4 写入 requirements 到 context.md [自动]
- [ ] Step 5 用户确认需求记录 [硬闸门]
```

### 5.3 `gin-wechat-article-angle`

```markdown
阶段 2/6：素材诊断与角度选择
Progress:
- [ ] Step 1 读取 context.md 与 materials_full.md [自动]
- [ ] Step 2 提取素材信号（痛点/反常识/数字/故事/身份/教程） [自动]
- [ ] Step 3 匹配切入角度与情绪触发点 [自动]
- [ ] Step 4 输出素材诊断报告 [自动]
- [ ] Step 5 用户确认诊断结果或补充素材 [需确认]
```

### 5.4 `gin-wechat-article-outline`

```markdown
阶段 3/6：大纲生成与确认
Progress:
- [ ] Step 1 读取 context.md 与 reference_briefs [自动]
- [ ] Step 2 为可用角度生成候选大纲 [自动]
- [ ] Step 3 自检排序并标注风险点 [自动]
- [ ] Step 4 展示候选大纲 [需确认]
- [ ] Step 5 用户选择/修改大纲 [硬闸门] [可回环]
```

### 5.5 `gin-wechat-article-writer`

```markdown
阶段 4/6：正文写作与人工改写
Progress:
- [ ] Step 1 读取 selected_outline 与 narrative_protocol [自动]
- [ ] Step 2 按章节逐段生成正文 [自动]
- [ ] Step 3 标注需用户补充位置 [自动]
- [ ] Step 4 输出 article_draft.md [自动]
- [ ] Step 5 用户二次改写 [硬闸门] [可回环]
```

### 5.6 `gin-wechat-article-polish`

```markdown
阶段 5/6：润色、小标题与标题优化
Progress:
- [ ] Step 1 读取 draft_revised.md 与 reference_briefs [自动]
- [ ] Step 2 调用 title 子 skill 优化小标题 [自动]
- [ ] Step 3 按规则去 AI 味、增强口语化 [自动]
- [ ] Step 4 输出 polished_draft.md [自动]
- [ ] Step 5 用户审阅润色稿 [需确认]
```

### 5.7 `gin-wechat-article-title`

`mode=article` 时：

```markdown
阶段 5/6：润色、小标题与标题优化
Progress:
- [ ] Step 1 读取正文与模板规则 [自动]
- [ ] Step 2 提取亮点并套用标题公式 [自动]
- [ ] Step 3 生成 3-6 个候选标题 [自动]
- [ ] Step 4 用 qa-checklist 剔除 hard-fail [自动]
- [ ] Step 5 展示候选标题 [需确认]
- [ ] Step 6 用户选择/修改标题 [硬闸门] [可回环]
```

`mode=subheading` 由 polish 内部调用，不单独向用户展示 checklist。

### 5.8 `gin-wechat-article-quality`

```markdown
阶段 6/6：质量检查与终审定稿
Progress:
- [ ] Step 1 读取最终标题与润色后正文 [自动]
- [ ] Step 2 执行 L1-L4 四层自检 [自动]
- [ ] Step 3 输出质量报告 [自动]
- [ ] Step 4 用户审阅质量报告 [需确认]
- [ ] Step 5 用户终审定稿确认 [硬闸门] [可回环]
```

---

## 6. 核心脚本设计

### 6.1 `gin-wechat-article-core/scripts/progress_reporter.py`

新增轻量脚本，统一渲染 Progress checklist 格式。

```python
def render_macro(
    current_stage: str,
    completed_stages: list[str],
    pending_stages: list[str],
    current_step: str | None = None,
    steps: list[dict] | None = None,
) -> str:
    """输出宏观 6 阶段仪表盘。"""

def render_micro(
    phase_name: str,
    steps: list[dict],
    current_step: str,
    show_phase_locator: bool = False,
) -> str:
    """输出子 skill 的 micro-checklist。"""
```

### 6.2 步骤数据结构

```python
step = {
    "name": "读取 context.md 与 reference_briefs",
    "tags": ["自动"],  # 或 ["硬闸门", "可回环"]
    "status": "pending",  # pending / done / current
}
```

### 6.3 阶段映射表

```python
STAGE_TO_PHASE = {
    "init": 1,
    "clarify": 1,
    "template_loaded": 2,
    "angle_diagnosed": 2,
    "role_boundary": 2,
    "angle_matched": 3,
    "outline_generated": 3,
    "outline_selected": 3,
    "outline_confirmed": 3,
    "draft_written": 4,
    "draft_revised": 4,
    "polished": 5,
    "titled": 5,
    "title_confirmed": 5,
    "quality_checked": 6,
    "quality_failed": 6,
    "finalized": 6,
    "markdown_output": 6,
    "publish_decision": 6,
}
```

---

## 7. 会话恢复机制

当检测到同目录下 `progress.md` 已存在时：

1. 读取当前 stage。
2. 调用 `render_macro()` 展示全部 6 阶段 + 当前步骤高亮。
3. 如果当前 stage 是硬闸门，输出当前阻塞提示。
4. 等待用户输入或继续执行。

恢复输出示例：

```markdown
📝 公众号长文写作进度（恢复）

阶段 1/6：初始化与需求澄清 [x]
阶段 2/6：素材诊断与角度选择 [x]
阶段 3/6：大纲生成与确认 [当前]
  Progress:
  - [x] Step 1 读取 context.md 与 reference_briefs [自动]
  - [x] Step 2 为可用角度生成候选大纲 [自动]
  - [x] Step 3 自检排序并标注风险点 [自动]
  - [ ] Step 4 展示候选大纲 [需确认]  ← 当前
  - [ ] Step 5 用户选择/修改大纲 [硬闸门] [可回环]
```

---

## 8. 错误处理与回环机制

### 8.1 跳跃步骤拦截

现有 `stage_validator.py` 已经校验 stage 进入前提。本次叠加 checklist 层后，拦截输出示例：

```markdown
📝 公众号长文写作进度

阶段 1/6：初始化与需求澄清 [x]
阶段 2/6：素材诊断与角度选择 [x]
阶段 3/6：大纲生成与确认 [当前]
  - [x] Step 1 读取 context.md 与 reference_briefs [自动]
  - [x] Step 2 为可用角度生成候选大纲 [自动]
  - [x] Step 3 自检排序并标注风险点 [自动]
  - [ ] Step 4 展示候选大纲 [需确认]  ← 当前
  - [ ] Step 5 用户选择/修改大纲 [硬闸门] [可回环]

⚠️ 无法跳过当前阶段。请先完成大纲确认，或输入"重新生成大纲"返回 Step 2。
```

### 8.2 回环映射

| 用户请求 | 回退目标 |
|---|---|
| "大纲要改" | 阶段 3 Step 2 |
| "正文重新写" | 阶段 4 Step 2 |
| "标题重新想" | 阶段 5 Step 2 |
| "润色得不行" | 阶段 5 Step 3 |

回退时同步更新 checklist，把已完成的后续步骤重置为 `[ ]`。

### 8.3 异常场景

| 场景 | 处理方式 |
|---|---|
| `progress.md` 损坏 | 提示用户"进度文件损坏，是否从阶段 1 重新开始" |
| `context.md` 缺失 | 必须回退到阶段 1 |
| 子 skill 执行失败 | core 捕获异常，checklist 停留在当前步骤，输出错误原因 |
| 用户输入无法识别 | 保持当前阶段不变，重新输出 checklist |

---

## 9. 文件改动清单

| 文件 | 改动类型 | 改动内容 |
|---|---|---|
| `gin-wechat-article-core/SKILL.md` | 修改 | 增加 Progress checklist 规则、6 阶段映射、子 skill 调用约束 |
| `gin-wechat-article-clarify/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-angle/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-outline/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-writer/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-polish/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-title/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-quality/SKILL.md` | 修改 | 增加 micro-checklist 和调用方式说明 |
| `gin-wechat-article-core/scripts/progress_reporter.py` | 新增 | 统一渲染 macro/micro checklist |
| `gin-wechat-article-core/scripts/stage_validator.py` | 可选修改 | 阶段转换时调用 progress_reporter 输出 |

---

## 10. 测试方案

1. **单元测试**：`gin-wechat-article-core/tests/test_progress_reporter.py`
   - 验证 `render_macro` 输出格式
   - 验证 `render_micro` 标签渲染
   - 验证 `STAGE_TO_PHASE` 映射完整

2. **路由回归测试**：更新 `tests/skill-routing-cases.yaml`（如存在）
   - 增加"用户要求跳过阶段"的拦截用例
   - 增加"会话恢复"用例

3. **端到端虚构案例**（可选）：`docs/end-to-end-fictional-case.md`
   - 展示从阶段 1 到阶段 6 的完整 checklist 流转

4. **人工验证**：
   - 每个硬闸门是否正确等待用户确认
   - 回环修改时 checklist 是否正确回退
   - 中断恢复时是否正确展示全部 6 阶段

---

## 11. 边界与约束

- 不新增数据库或复杂状态机，复用现有 `progress.md` + `context.md`。
- 不修改子 skill 的脚本实现，只在 SKILL.md 层增加 Progress 规则。
- 版本号按仓库惯例更新：修改 `gin-wechat-article-core/VERSION` 和 `更新日志.md`。
- 禁止在 Progress checklist 中编造步骤状态，必须基于 `progress.md` 实际状态渲染。
