---
name: gin-wechat-article-outline
description: 当需要根据公众号长文的角度和情绪触发点生成候选大纲和开头钩子时触发
---

# 生成候选大纲+开头

## 输入

- 需求记录
- 模板规则
- `context.md.narrative_protocol`（新增）
- `context.md.materials_summary.materials_path` 指向的 `materials_full.md`（新增）
- `context.md.reference_briefs.expansion_methodology`
- `context.md.reference_briefs.hook_design`
- `context.md.reference_briefs.outline_framework`
- `context.md.reference_briefs.content_principles`

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

## 动作

1. 读取 `context.md`、其 `materials_summary.materials_path` 指向的 `materials_full.md`，以及 `context.md.reference_briefs` 下的四个核心要点摘要。
2. 为每个素材支撑度≥60%的角度生成一个大纲+开头。
3. 每个候选必须标注：
   - 核心立场（thesis）：一句锐利、明确、可被记住的判断
   - 副观点（supporting_points）：2-3 个互补角度
   - 说服策略（persuasion_strategies）：数据/故事/权威/类比/社会认同的组合
   - 情绪目标（emotion_goal）：主要触发的感受
   - 情绪曲线（emotion_arc）：如 低落→好奇→反转→高潮
   - 计划金句（key_quotes）：至少一句脱离上下文可传播的记忆锚点
   - 结尾互动（closing_hook）：提问/填句/争议/投票等
   - 切入角度（A1-A6 / B1-B2 / C1）
   - 主情绪触发点
   - 次情绪触发点
   - 认知落差说明（读者能获得什么新视角）
   - **推荐排序（1-N，1 为最推荐）**
   - **推荐理由（一句话）**
   - **适用场景（适合什么类型用户/传播目标）**
   - **风险点（素材不足或可能写散的预警）**
4. 章节结构（sections）必须严格按 `narrative_protocol.sections` 的顺序、职责和约束生成。
   - `name` 对应 narrative_protocol 的 section name
   - `purpose` 从 narrative_protocol 复制
   - `must_include` 从 narrative_protocol 复制
   - `forbidden` 从 narrative_protocol 复制
   - `content` 根据素材和需求填充
   - `materials_ref` 标注本 section 有哪些素材支撑
   - `human_needed` 标注哪些必须用户补充真实经历
   - `word_count_estimate` 预估本 section 字数
5. 按推荐排序输出，通常 2-5 个，默认 3-4 个。
6. 每个候选按客观检查清单评分并排序。
7. 数量不足时提示用户补充素材。
8. 用户要求重生成时，使用不同角度组合避免重复。

## 被跳过检测

如果主 skill 调用本 skill 时，发现 `context.md` 中以下任一条件不满足，说明前置子 skill 可能未执行，本 skill 应返回错误并暂停流程：

1. `narrative_protocol` 不存在或为空
2. `angle_candidates` 不存在或为空
3. `diagnosis_report` 不存在或为空
4. `materials_summary.materials_path` 不存在或 `materials_full.md` 文件不存在

**返回错误格式**：

```text
❌ 前置条件缺失，无法生成候选大纲（gin-wechat-article-outline）。
原因：context.md 中缺少 {具体字段}
操作：请先完成素材诊断（gin-wechat-article-angle）和人-AI 协作契约书确认（role_boundary），再调用本 skill。
影响：本 skill 未执行，未生成 outline_candidates。
```

**输出文件证据**：

本 skill 执行完成后，必须在 `output_dir/<article_id>/outlines/` 目录下生成 `outline_candidates.md`，并在 `context.md` 中写入：

- `outline_candidates`：候选大纲列表
- `selected_outline`：用户选定的大纲（在 outline_selected 阶段写入）

主 skill 进入 `draft_written` 前，应检查上述字段和文件是否存在。
- 每份候选附带：核心立场、副观点、说服策略、情绪目标、情绪曲线、计划金句、结尾互动、章节结构、切入角度、主/次情绪触发点、认知落差说明、排序、推荐理由、适用场景、风险点。
- 最终写入 `context.md` 的 `outline_candidates` 列表，每项至少包含：
  - `rank`
  - `angle`
  - `thesis`
  - `supporting_points`
  - `persuasion_strategies`
  - `emotion_goal`
  - `emotion_arc`
  - `key_quotes`
  - `closing_hook`
- `sections`
  - `name`
  - `purpose`
  - `must_include`
  - `forbidden`
  - `content`
  - `materials_ref`（新增）
  - `human_needed`（新增）
  - `word_count_estimate`（新增）
  - `title`
  - `reason`
  - `scenario`
  - `risk`
