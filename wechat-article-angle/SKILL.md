---
name: wechat-article-angle
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

## 边界

- 只做诊断和匹配，不生成大纲。
- 如果素材不足，提示用户补充，不强行匹配。

## 辅助脚本

- `scripts/angle_matcher.py`：根据需求记录和模板规则，按 `reference_briefs.angle_library` 中的规则匹配切入角度和情绪触发点，输出结构化的素材诊断报告。
