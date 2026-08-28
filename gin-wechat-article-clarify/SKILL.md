---
name: gin-wechat-article-clarify
description: 当用户需要澄清公众号文章需求、整理写作素材时使用。输出结构化的需求记录。
---

# 需求澄清

## 输入

- 用户原始想法
- 主题/素材
- `context.md` 中已写入的 `selected_template`（由主 skill 在触发本技能前完成风格选择，无需再次询问）

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

## 动作

> **前提**：上游已有专门整理素材的 skill，输入为结构化 Markdown 素材文档，本 skill 不再重复收集素材内容，只确认素材是否足够以及缺口在哪里。

通过结构化访谈确认：
1. 主题：文章要讨论什么？
2. 目标读者：给谁看？（身份标签）
3. 核心观点/立场：你最想表达什么判断？
4. 字数要求：预计多长？
5. 说话位置：
   - 谁在说这件事？（亲历者 / 调查者 / 观察者 / 研究者）
   - 他凭什么知道这些事？（亲历 / 查证 / 推测）
   - 他为什么现在想说这件事？（触发点是什么）
6. 进行素材完整性确认，将结果写入 `requirements.materials_sufficient` 和 `requirements.materials_gap`：
   - 若 `materials_summary.total_chars` 为 0 或用户未提供任何素材，标记 `materials_sufficient = false`，`materials_gap` 列出需要补充的素材类型。
   - 若已有素材可支撑核心观点，标记 `materials_sufficient = true`，`materials_gap` 可为空列表。

**注意**：风格模板已在 `init` 阶段由 `style_selector.py` 选定并写入 `context.md.selected_template`，
本技能不再询问模板名。若用户对预选的模板有异议，可在访谈中反馈，由主 skill 决定是否重新选择。

## 输出

- 需求记录（写入 context.md 的 `requirements` 字段）
- 需求记录结构：
  - `topic`
  - `target_reader`
  - `core_points`
  - `word_count`
  - `materials`
  - `materials_sufficient`
  - `materials_gap`
  - `speaker_position`
    - `who`：叙述者身份
    - `credential`：凭什么知道
    - `trigger`：为什么现在说
  - `notes`（可选）

**不输出**：风格模板名（模板选择不是本 skill 的职责）。

## 边界

- 不开始写作。
- 不判断选题好坏（交给 gin-wechat-article-angle）。
- **默认必须执行需求确认**。只有用户明确说"跳过确认""直接生成""--quick"等时，才允许直接输出需求记录。AI 不得自行判断"输入已经足够"。
