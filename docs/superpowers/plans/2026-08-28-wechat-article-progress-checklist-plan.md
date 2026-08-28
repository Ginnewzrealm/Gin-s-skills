# 微信公众号写作技能组 Progress checklist 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为微信公众号写作 8 个技能增加统一的 Progress checklist 展示层，解决跳跃步骤和阶段不清的问题。

**架构：** `gin-wechat-article-core` 维护宏观 6 阶段仪表盘，7 个子 skill 维护本环节 micro-checklist；新增 `progress_reporter.py` 统一渲染 checklist 格式；复用现有 `progress.md` + `stage_validator.py` 状态机。

**技术栈：** Python 3，Markdown，git

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `gin-wechat-article-core/scripts/progress_reporter.py` | 新增。统一渲染宏观/微观 Progress checklist。 |
| `gin-wechat-article-core/tests/test_progress_reporter.py` | 新增。单元测试 progress_reporter 的输出格式和阶段映射。 |
| `gin-wechat-article-core/SKILL.md` | 修改。增加 Progress checklist 规则、6 阶段映射、调用子 skill 约束、会话恢复规则。 |
| `gin-wechat-article-clarify/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-angle/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-outline/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-writer/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-polish/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-title/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-quality/SKILL.md` | 修改。增加 micro-checklist 和调用方式说明。 |
| `gin-wechat-article-core/scripts/stage_validator.py` | 修改。阶段转换时调用 progress_reporter 输出宏观 checklist（可选但推荐）。 |
| `gin-wechat-article-core/VERSION` | 修改。更新版本号。 |
| `gin-wechat-article-core/更新日志.md` | 修改。记录本次变更。 |

---

## 任务 1：创建 `progress_reporter.py` 及单元测试

**文件：**
- 创建：`gin-wechat-article-core/scripts/progress_reporter.py`
- 创建：`gin-wechat-article-core/tests/test_progress_reporter.py`

### 步骤 1：编写失败的测试

在 `gin-wechat-article-core/tests/test_progress_reporter.py` 中写入：

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from progress_reporter import render_macro, render_micro, STAGE_TO_PHASE


def test_stage_to_phase_has_all_stages():
    expected = {
        "init", "clarify", "template_loaded", "angle_diagnosed", "role_boundary",
        "angle_matched", "outline_generated", "outline_selected", "outline_confirmed",
        "draft_written", "draft_revised", "polished", "titled", "title_confirmed",
        "quality_checked", "quality_failed", "finalized", "markdown_output", "publish_decision",
    }
    assert set(STAGE_TO_PHASE.keys()) == expected


def test_render_macro_shows_current_phase():
    result = render_macro(
        current_stage="outline_generated",
        completed_stages=["init", "clarify", "template_loaded", "angle_diagnosed", "role_boundary"],
        pending_stages=["outline_selected", "outline_confirmed", "draft_written", "draft_revised", "polished", "titled", "title_confirmed", "quality_checked", "finalized", "markdown_output", "publish_decision"],
        current_step="展示候选大纲",
        steps=[
            {"name": "读取 context.md 与 reference_briefs", "tags": ["自动"], "status": "done"},
            {"name": "为可用角度生成候选大纲", "tags": ["自动"], "status": "done"},
            {"name": "自检排序并标注风险点", "tags": ["自动"], "status": "done"},
            {"name": "展示候选大纲", "tags": ["需确认"], "status": "current"},
            {"name": "用户选择/修改大纲", "tags": ["硬闸门", "可回环"], "status": "pending"},
        ],
    )
    assert "阶段 3/6：大纲生成与确认" in result
    assert "展示候选大纲" in result
    assert "← 当前" in result
    assert "- [x]" in result
    assert "- [ ]" in result


def test_render_micro_with_phase_locator():
    result = render_micro(
        phase_name="阶段 3/6：大纲生成与确认",
        steps=[
            {"name": "读取 context.md 与 reference_briefs", "tags": ["自动"], "status": "pending"},
        ],
        current_step="读取 context.md 与 reference_briefs",
        show_phase_locator=True,
    )
    assert "当前处于公众号长文写作的阶段 3/6：大纲生成与确认" in result
    assert "读取 context.md 与 reference_briefs" in result
```

### 步骤 2：运行测试验证失败

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-wechat-article-core
python3 -m pytest tests/test_progress_reporter.py -v
```

**预期：** 3 个测试全部 FAIL，报错 `ModuleNotFoundError: No module named 'progress_reporter'`。

### 步骤 3：编写最少实现代码

在 `gin-wechat-article-core/scripts/progress_reporter.py` 中写入：

```python
"""统一渲染微信公众号写作技能组的 Progress checklist。"""

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

PHASE_NAMES = {
    1: "阶段 1/6：初始化与需求澄清",
    2: "阶段 2/6：素材诊断与角度选择",
    3: "阶段 3/6：大纲生成与确认",
    4: "阶段 4/6：正文写作与人工改写",
    5: "阶段 5/6：润色、小标题与标题优化",
    6: "阶段 6/6：质量检查与终审定稿",
}


def _phase_title_from_stage(stage: str) -> str:
    phase_num = STAGE_TO_PHASE.get(stage, 0)
    return PHASE_NAMES.get(phase_num, f"阶段 ?/6：未知阶段")


def _render_step(step: dict, is_current: bool) -> str:
    status = step.get("status", "pending")
    checkbox = "[x]" if status == "done" else "[ ]"
    tags = " ".join(f"[{tag}]" for tag in step.get("tags", []))
    current_marker = "  ← 当前" if is_current else ""
    return f"- {checkbox} Step {step.get('seq', '')} {step['name']} {tags}{current_marker}"


def render_macro(
    current_stage: str,
    completed_stages: list[str],
    pending_stages: list[str],
    current_step: str | None = None,
    steps: list[dict] | None = None,
) -> str:
    lines = ["📝 公众号长文写作进度", ""]

    current_phase_num = STAGE_TO_PHASE.get(current_stage, 0)

    for phase_num in range(1, 7):
        phase_title = PHASE_NAMES[phase_num]
        if phase_num < current_phase_num:
            lines.append(f"{phase_title} [x]")
        elif phase_num == current_phase_num:
            lines.append(f"{phase_title}")
            if steps:
                for idx, step in enumerate(steps, start=1):
                    step_with_seq = {**step, "seq": idx}
                    is_current = step["name"] == current_step
                    lines.append("  " + _render_step(step_with_seq, is_current))
        else:
            lines.append(f"{phase_title} [待开始]")

    return "\n".join(lines)


def render_micro(
    phase_name: str,
    steps: list[dict],
    current_step: str,
    show_phase_locator: bool = False,
) -> str:
    lines = []
    if show_phase_locator:
        lines.append(f"当前处于公众号长文写作的{phase_name}。")
        lines.append("")

    lines.append(phase_name)
    lines.append("Progress:")

    for idx, step in enumerate(steps, start=1):
        step_with_seq = {**step, "seq": idx}
        is_current = step["name"] == current_step
        lines.append(_render_step(step_with_seq, is_current))

    return "\n".join(lines)
```

### 步骤 4：运行测试验证通过

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-wechat-article-core
python3 -m pytest tests/test_progress_reporter.py -v
```

**预期：** 3 个测试全部 PASS。

### 步骤 5：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-core/scripts/progress_reporter.py gin-wechat-article-core/tests/test_progress_reporter.py
git commit -m "feat(wechat-article-core): 增加 progress_reporter 统一渲染 Progress checklist"
```

---

## 任务 2：修改 `gin-wechat-article-core/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-core/SKILL.md`

### 步骤 1：在"入口流程"之前插入"进度条使用规则"章节

在 `gin-wechat-article-core/SKILL.md` 的 `# 公众号长文写作（主编排）` 之后、`## 触发条件` 之前插入：

```markdown
## 进度条使用规则

每次触发本 skill、每次 stage 跳转、每次会话恢复时，必须向用户展示 Progress checklist，并在执行过程中动态更新：

1. 进入新 stage 后，先展示当前宏观 6 阶段仪表盘。
2. 调用子 skill 前，由 core 展示宏观仪表盘；子 skill 只展示本环节 micro-checklist。
3. 每完成一步，将该步骤标记为 `[x]`，并高亮下一步为 `← 当前`。
4. 如果需要等待用户输入，输出 `当前阻塞：...`。
5. 会话中断后恢复时，先输出当前完整 6 阶段进度状态，再继续。

checklist 步骤标签：

| 标签 | 含义 |
|------|------|
| `[自动]` | AI/脚本自动执行，无需用户输入 |
| `[需确认]` | 需要用户查看并确认，但非强制通过 |
| `[硬闸门]` | 用户不通过则无法继续下一步，必须明确说 OK / 批准 / 继续 |
| `[可回环]` | 用户提出修改时，返回前面步骤重做 |

宏观 6 阶段映射：

| 阶段 | 内部 stage | 关键硬闸门 |
|---|---|---|
| 阶段 1/6：初始化与需求澄清 | init, clarify | 需求记录确认 |
| 阶段 2/6：素材诊断与角度选择 | template_loaded, angle_diagnosed, role_boundary | 人-AI 协作契约书确认 |
| 阶段 3/6：大纲生成与确认 | angle_matched, outline_generated, outline_selected, outline_confirmed | 大纲选择 + 开始写正文确认 |
| 阶段 4/6：正文写作与人工改写 | draft_written, draft_revised | 人工二次改写确认 |
| 阶段 5/6：润色、小标题与标题优化 | polished, titled, title_confirmed | 标题确认 |
| 阶段 6/6：质量检查与终审定稿 | quality_checked, finalized, markdown_output, publish_decision | 终审定稿确认 |

子 skill 被 core 调用时，不重复展示完整 6 阶段宏观进度；被用户直接调用时，先输出阶段定位句 `当前处于公众号长文写作的阶段 X/6：XXX。`，再输出 micro-checklist。
```

### 步骤 2：在"阶段定义"表格中增加阶段标签列

将现有阶段定义表格扩展为 5 列：stage、下一步动作、调用的子技能、类型、进度标签。

例如：

```markdown
| stage | 下一步动作 | 调用的子技能 | 类型 | 进度标签 |
|-------|-----------|-------------|------|---------|
| init | 路径初始化检查 + 风格选择 | init_checker.py + style_selector.py（主 skill 内部） | AI | [自动] |
| clarify | 需求澄清 | gin-wechat-article-clarify | 人工 | [需确认] + [硬闸门] |
| template_loaded | 加载模板 + 生成 narrative_protocol | template_loader.py（主 skill 内部加载） | AI | [自动] |
| angle_diagnosed | 素材诊断 | gin-wechat-article-angle | AI | [自动] |
| role_boundary | 人-AI 协作契约书确认 | （主 skill 内部） | 人工 | [硬闸门] |
| angle_matched | 生成候选大纲 | gin-wechat-article-outline | AI | [自动] |
| outline_generated | 选择/修改大纲 | （人工） | 人工 | [硬闸门] [可回环] |
| outline_selected | 确认开始写正文 | （人工） | 人工 | [硬闸门] |
| outline_confirmed | 分段写正文 | gin-wechat-article-writer | AI | [自动] |
| draft_written | 二次改写正文 | （人工） | 人工 | [硬闸门] [可回环] |
| draft_revised | 小标题优化 + 润色 | gin-wechat-article-polish | AI | [自动] |
| polished | 审阅润色稿 → 提炼标题候选 | （人工审阅）+ gin-wechat-article-title(article) | 人工+AI | [需确认] |
| titled | 选择/修改标题 | （人工） | 人工 | [硬闸门] [可回环] |
| title_confirmed | 质量自检 | gin-wechat-article-quality | AI | [自动] |
| quality_failed | 返回润色 | gin-wechat-article-polish | AI（循环） | [可回环] |
| quality_checked | 终审定稿 | （人工） | 人工 | [硬闸门] |
| finalized | 输出 Markdown | （主 skill 内部） | AI | [自动] |
| markdown_output | 发布/保存决策 | （人工） | 人工 | [需确认] |
| publish_decision | 保存/推送 | wps-skill / baoyu-post-to-wechat | AI/外部 | [需确认] |
```

### 步骤 3：在"入口流程"第 6 步后增加恢复时输出规则

在"创建或读取 `output_dir/<article_id>/context.md`"段落之后增加：

```markdown
6.1. **会话恢复时**：若同目录下 `progress.md` 已存在，先调用 `progress_reporter.render_macro()` 输出完整 6 阶段进度状态（含当前步骤高亮），再继续后续流程。
```

### 步骤 4：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-core/SKILL.md
git commit -m "docs(wechat-article-core): 增加 Progress checklist 使用规则与阶段标签"
```

---

## 任务 3：修改 `gin-wechat-article-clarify/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-clarify/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 1/6：初始化与需求澄清
Progress:
- [ ] Step 1 读取已有素材与已选模板信息 [自动]
- [ ] Step 2 结构化访谈：确认主题/读者/核心观点/字数 [需确认]  ← 当前
- [ ] Step 3 确认说话位置与素材完整性 [需确认]
- [ ] Step 4 写入 requirements 到 context.md [自动]
- [ ] Step 5 用户确认需求记录 [硬闸门]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-clarify/SKILL.md
git commit -m "docs(wechat-article-clarify): 增加 Progress checklist"
```

---

## 任务 4：修改 `gin-wechat-article-angle/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-angle/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 2/6：素材诊断与角度选择
Progress:
- [ ] Step 1 读取 context.md 与 materials_full.md [自动]
- [ ] Step 2 提取素材信号（痛点/反常识/数字/故事/身份/教程） [自动]
- [ ] Step 3 匹配切入角度与情绪触发点 [自动]
- [ ] Step 4 输出素材诊断报告 [自动]
- [ ] Step 5 用户确认诊断结果或补充素材 [需确认]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-angle/SKILL.md
git commit -m "docs(wechat-article-angle): 增加 Progress checklist"
```

---

## 任务 5：修改 `gin-wechat-article-outline/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-outline/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 3/6：大纲生成与确认
Progress:
- [ ] Step 1 读取 context.md 与 reference_briefs [自动]
- [ ] Step 2 为可用角度生成候选大纲 [自动]
- [ ] Step 3 自检排序并标注风险点 [自动]
- [ ] Step 4 展示候选大纲 [需确认]
- [ ] Step 5 用户选择/修改大纲 [硬闸门] [可回环]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-outline/SKILL.md
git commit -m "docs(wechat-article-outline): 增加 Progress checklist"
```

---

## 任务 6：修改 `gin-wechat-article-writer/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-writer/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 4/6：正文写作与人工改写
Progress:
- [ ] Step 1 读取 selected_outline 与 narrative_protocol [自动]
- [ ] Step 2 按章节逐段生成正文 [自动]
- [ ] Step 3 标注需用户补充位置 [自动]
- [ ] Step 4 输出 article_draft.md [自动]
- [ ] Step 5 用户二次改写 [硬闸门] [可回环]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-writer/SKILL.md
git commit -m "docs(wechat-article-writer): 增加 Progress checklist"
```

---

## 任务 7：修改 `gin-wechat-article-polish/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-polish/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 5/6：润色、小标题与标题优化
Progress:
- [ ] Step 1 读取 draft_revised.md 与 reference_briefs [自动]
- [ ] Step 2 调用 title 子 skill 优化小标题 [自动]
- [ ] Step 3 按规则去 AI 味、增强口语化 [自动]
- [ ] Step 4 输出 polished_draft.md [自动]
- [ ] Step 5 用户审阅润色稿 [需确认]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-polish/SKILL.md
git commit -m "docs(wechat-article-polish): 增加 Progress checklist"
```

---

## 任务 8：修改 `gin-wechat-article-title/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-title/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

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

`mode=subheading` 由 `gin-wechat-article-polish` 内部调用，不单独向用户展示 checklist。
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-title/SKILL.md
git commit -m "docs(wechat-article-title): 增加 Progress checklist"
```

---

## 任务 9：修改 `gin-wechat-article-quality/SKILL.md`

**文件：**
- 修改：`gin-wechat-article-quality/SKILL.md`

### 步骤 1：在"输入"章节之后插入 Progress checklist

在 `## 输入` 之后、`## 动作` 之前插入：

```markdown
## Progress

本 skill 被 `gin-wechat-article-core` 调用时，不重复展示完整 6 阶段宏观进度，只展示本环节 micro-checklist。被用户直接调用时，先输出阶段定位句。

```markdown
阶段 6/6：质量检查与终审定稿
Progress:
- [ ] Step 1 读取最终标题与润色后正文 [自动]
- [ ] Step 2 执行 L1-L4 四层自检 [自动]
- [ ] Step 3 输出质量报告 [自动]
- [ ] Step 4 用户审阅质量报告 [需确认]
- [ ] Step 5 用户终审定稿确认 [硬闸门] [可回环]
```
```

### 步骤 2：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-quality/SKILL.md
git commit -m "docs(wechat-article-quality): 增加 Progress checklist"
```

---

## 任务 10：修改 `stage_validator.py` 调用 `progress_reporter`

**文件：**
- 修改：`gin-wechat-article-core/scripts/stage_validator.py`

### 步骤 1：导入并调用 `progress_reporter.render_macro`

在 `stage_validator.py` 顶部增加导入：

```python
from progress_reporter import render_macro, STAGE_TO_PHASE
```

在决定当前 stage 并校验通过后的输出位置，增加：

```python
phase_steps = _get_phase_steps(current_stage)  # 根据当前 stage 返回本阶段步骤列表
checklist = render_macro(
    current_stage=current_stage,
    completed_stages=completed_stages,
    pending_stages=pending_stages,
    current_step=_get_current_step(current_stage, context),
    steps=phase_steps,
)
print(checklist)
```

> 注：具体插入位置需根据 `stage_validator.py` 现有函数结构决定，通常放在 `decide_next_stage()` 返回前或主调用方打印处。如果 `stage_validator.py` 是纯校验函数、不打印输出，则此步骤改为在 `gin-wechat-article-core/SKILL.md` 中规定：core 主逻辑在调用 `stage_validator` 后调用 `progress_reporter.render_macro()`。

### 步骤 2：运行脚本语法检查

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-wechat-article-core
python3 -m py_compile scripts/stage_validator.py
```

**预期：** 无语法错误。

### 步骤 3：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-core/scripts/stage_validator.py
git commit -m "feat(wechat-article-core): stage_validator 输出 Progress checklist"
```

---

## 任务 11：更新版本号和更新日志

**文件：**
- 修改：`gin-wechat-article-core/VERSION`
- 修改：`gin-wechat-article-core/更新日志.md`

### 步骤 1：读取当前版本

```bash
cat /Users/fubo/Downloads/Gin-s-skills-work/gin-wechat-article-core/VERSION
```

假设当前版本为 `v1.0.0`，本次变更为新增 Progress checklist 功能，按语义化版本升级为 `v1.1.0`。

### 步骤 2：修改 VERSION 文件

写入 `v1.1.0`。

### 步骤 3：修改更新日志

在 `gin-wechat-article-core/更新日志.md` 顶部追加：

```markdown
## v1.1.0（2026-08-28）

- feat: 为公众号长文写作主编排流程增加 Progress checklist（6 阶段宏观仪表盘 + 子 skill 微观 checklist）
- feat: 新增 `scripts/progress_reporter.py` 统一渲染 checklist
- feat: 7 个子 skill SKILL.md 增加 Progress checklist 展示规则
- feat: stage_validator 阶段转换时输出宏观 checklist
```

### 步骤 4：Commit

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git add gin-wechat-article-core/VERSION "gin-wechat-article-core/更新日志.md"
git commit -m "chore(wechat-article-core): bump version to v1.1.0"
```

---

## 任务 12：运行验证

### 步骤 1：运行单元测试

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-wechat-article-core
python3 -m pytest tests/test_progress_reporter.py -v
```

**预期：** 全部 PASS。

### 步骤 2：运行 skill 静态校验（如果存在）

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
python3 scripts/validate_skills.py
```

如果 `scripts/validate_skills.py` 不存在，则跳过此步骤。

### 步骤 3：检查 git 状态

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work
git status
```

**预期：** 工作区干净，所有变更已 commit。

### 步骤 4：Commit（如校验脚本产生变更）

如果有自动修复的变更，执行：

```bash
git add -A
git commit -m "chore(wechat-article): 通过 validate_skills 静态校验"
```

---

## 自检

### 规格覆盖度

| 规格需求 | 对应任务 |
|---|---|
| 新增 progress_reporter.py 统一渲染 | 任务 1 |
| core 增加 Progress 规则和 6 阶段映射 | 任务 2 |
| 7 个子 skill 增加 micro-checklist | 任务 3-9 |
| stage_validator 调用 progress_reporter | 任务 10 |
| 版本号和更新日志 | 任务 11 |
| 单元测试和静态校验 | 任务 1、12 |

### 占位符扫描

- 无"待定"、"TODO"、"后续实现"。
- 每个代码步骤都包含实际代码或命令。
- 版本号假设为 `v1.0.0`，实际执行时需读取当前 VERSION 文件按实升级。

### 类型一致性

- `progress_reporter.py` 中的 `STAGE_TO_PHASE`、`PHASE_NAMES`、函数签名在测试和实现中一致。
- 所有 SKILL.md 中引用的阶段名称和标签与设计文档一致。

---

## 执行交接

**计划已完成并保存到 `docs/superpowers/plans/2026-08-28-wechat-article-progress-checklist-plan.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
