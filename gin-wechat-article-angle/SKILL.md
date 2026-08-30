---
name: gin-wechat-article-angle
description: 根据需求记录和模板规则，提取素材信号，匹配切入角度和情绪触发点。
---

# 素材诊断

## 输入

- 需求记录
- 模板规则
- `context.md.narrative_protocol`（新增）
- `context.md.materials_summary.materials_path` 指向的 `materials_full.md`（新增）
- `context.md.requirements.speaker_position`（新增）
- `context.md.reference_briefs.angle_library`
- `context.md.reference_briefs.emotion_trigger_system`
- `context.md.reference_briefs.content_principles`

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

## 动作

1. **提取素材信号**：从需求记录中识别以下信号：
   - 痛点
   - 反常识
   - 数字
   - 故事
   - 身份
   - 教程

2. **匹配切入角度**：按 `reference_briefs.angle_library` 中的规则，返回 1-2 个可用角度。

3. **映射情绪触发点**：按 `reference_briefs.emotion_trigger_system` 和 `reference_briefs.angle_library` 的映射表，返回主/次情绪触发点。

## 输出

- 素材诊断报告
- 可用角度列表，每项包含：
  - `id`
  - `name`
  - `description`
  - `narrative_fit`：与 narrative_protocol 的匹配度说明
  - `material_support`：素材支撑点列表
  - 主/次情绪触发点
- 推荐情绪触发点

## 被跳过检测

如果主 skill 调用本 skill 时，发现 `context.md` 中以下任一条件不满足，说明本 skill 可能被跳过，应返回错误并暂停流程：

1. `narrative_protocol` 不存在或为空
2. `materials_summary.materials_path` 不存在或 `materials_full.md` 文件不存在
3. `requirements` 不存在或为空

**返回错误格式**：

```text
❌ 前置条件缺失，无法执行素材诊断（gin-wechat-article-angle）。
原因：context.md 中缺少 {具体字段}
操作：请先完成模板加载（template_loaded）和素材读取，再调用本 skill。
影响：本 skill 未执行，未生成 angle_candidates 和 diagnosis_report。
```

**输出文件证据**：

本 skill 执行完成后，必须在 `output_dir/<article_id>/reports/` 目录下生成 `diagnosis_report.md`，并在 `context.md` 中写入：

- `angle_candidates`：可用角度列表
- `diagnosis_report`：诊断报告摘要
- `selected_angle`：推荐角度
- `emotion_trigger` / `secondary_trigger`：情绪触发点

主 skill 进入 `role_boundary` 前，应检查上述字段和文件是否存在。

- `scripts/angle_matcher.py`：根据需求记录和模板规则，按 `reference_briefs.angle_library` 中的规则匹配切入角度和情绪触发点，输出结构化的素材诊断报告。
