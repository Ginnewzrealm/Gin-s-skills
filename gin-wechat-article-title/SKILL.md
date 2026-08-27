---
name: gin-wechat-article-title
description: 根据正文提炼文章标题，或优化章节小标题。支持 mode=article 和 mode=subheading。
---

# 标题优化

## 输入

- 正文
- 模板规则
- `context.md.narrative_protocol.global_rules.opening`（新增）
- 情绪触发点
- mode 参数（article/subheading）
- `context.md.reference_briefs.bigpeng_title_formulas`
- `context.md.reference_briefs.bigpeng_topic_templates`
- `context.md.reference_briefs.bigpeng_title_corpus`
- `context.md.reference_briefs.bigpeng_qa_checklist`

## 动作

### mode=article

1. 从正文提取亮点：
   - 最大冲突句
   - 最有张力数字
   - 最反常识观点
   - 最具体场景
   - 最强情绪点
2. 套用 `reference_briefs.bigpeng_title_formulas` 中的标题公式库生成 **3-6 个候选**，默认 5 个。
3. 每个候选必须标注：
   - 标题文本
   - 所用公式（BigPeng 7 型公式之一）
   - 主情绪触发点
   - 核心卖点/冲突
   - **推荐排序（1-N）**
   - **推荐理由**
   - **适用场景**
   - **风险点**
4. 用 `reference_briefs.bigpeng_qa_checklist` 逐项检查，剔除 hard-fail 项。
5. 标题必须符合作品模板的开头规则（如 `narrative_protocol.global_rules.opening` 要求从具体人物切入，则标题不应是宏大叙事式）。
6. 按推荐排序输出，避免同义改写。

### mode=subheading

1. 根据章节角色和正文内容生成小标题。
2. 每个章节输出 1 主 + 2 备选。
3. 小标题需符合：
   - 字数 6-12 字
   - 是认知台阶
   - 与模板 subheadings.style 一致
   - 保持章节递进关系
   - 不出现"首先/其次/最后/总结/结语"
   - **不出现"第一章/第二章/第三章"或"第一/第二/第三"等章节编号**
   - 能从对应段落找到支撑
4. 用 `qa-checklist.md` 中小标题检查项复核。

> 注：mode=subheading 是 AI 内部步骤，与润色合并执行，不单独向用户展示。输出的小标题将嵌入润色稿中，在「人审阅润色稿」节点统一由用户审阅。

## 输出

- 标题候选 / 小标题方案

## 边界

- 不改变正文内容。
- 标题必须能从正文找到支撑。
