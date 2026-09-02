---
name: gin-wechat-article-polish
description: 润色正文，去除 AI 味，增强活人感。
---

# 润色/去 AI 味

## 输入

- `context.md.draft_revised_path`：人二次改写后的正文文件路径（`draft_revised` 阶段产物）。
  - 若 `draft_revised` 为 true 但 `draft_revised_path` 为空，则回退读取 `context.md.draft_path`。
- `context.md.selected_outline`：选定大纲
- `context.md.selected_template`：模板规则
- `context.md.narrative_protocol`（新增）
- `context.md.reference_briefs.ai_flavor_guide`
- `context.md.reference_briefs.writing_checklist`
- `context.md.reference_briefs.writing_style`
- `context.md.reference_briefs.content_principles`
- `context.md.reference_briefs.emotion_trigger_system`
- `context.md.reference_briefs.quality_checklist`（问题清单，可选）

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

## 动作

1. 读取 `draft_revised_path` 指向的文件内容。
2. 调用 `gin-wechat-article-title(mode=subheading)` 优化章节小标题。
3. 按 `reference_briefs.content_principles` 做高层检查：文字洁癖、表达效率、认知落差。
4. 按 `narrative_protocol.tone` 和 `narrative_protocol.forbidden_zone` 调整语气，确保润色后不偏离模板约束。
5. 按 `reference_briefs.ai_flavor_guide` **第〇节使用原则**去除 AI 腔：处理顺序自下而上（经验层→结构层→句式层→词汇层），**全篇合计只选 3-5 种手法**（24 种模式与口语化词组是菜单不是 checklist），改完用六种诊断复检——命中"清理后发扁"则退回 1-2 处留白，补命名/意象/节奏。随后按 `reference_briefs.writing_checklist` 和 `reference_briefs.writing_style` 校准；**特别检查主语承前省略**：同一段落内连续相同主语的句子，从第二句起省略主语，只在主语切换、需要强调或省略会歧义时保留。
6. 增强口语化表达。
7. 确保扣主线节奏。
8. 确保有至少一个"可讨论点"（情绪缺口）。
9. 检查并替换禁区词和禁区标点。
10. 如果收到 `gin-wechat-article-quality` 的问题清单（由 `quality_failed` 阶段循环传入），优先修复清单中的 hard-fail 项。

## 输出

- 带小标题的润色稿，保存到 `context.md.polished_draft_path`（默认 `polished_draft.md`），作为「人审阅润色稿」节点的输入。

## 边界

- 不改变大纲结构和核心观点。
- 不重新提炼标题。
- 不生成封面/插图。
- 去 AI 腔只动表达层（措辞、句式、段落节奏、结构衔接），不改动核心观点与事实。
- 若 AI 腔已渗入观点与结构、表达层改动救不回来 → 不硬磨，返回 core「需重写」信号（触发 writer 阶段按原大纲重写），禁止在烂底子上反复润色。
