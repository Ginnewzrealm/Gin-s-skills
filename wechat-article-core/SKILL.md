---
name: wechat-article-core
description: 当用户需要写公众号长文、整理素材成文、润色文章、优化标题、文章结构优化、去 AI 味、检查文章质量、扩写、改写、选题讨论、情绪钩子设计、长文排版等公众号相关写作需求时触发
---

# 公众号长文写作（主编排）

本 skill 是公众号长文写作的主编排入口。正文写作采用统一风格：

> **一个有见识的普通人在讲述他亲身的所见、所闻、经历和感受。**

不区分"标准模式"或"卡兹克模式"，只有这一种写作风格。

核心方法论文件（由 init 阶段读取并提取为 `reference_briefs`，供下游子 skill 引用）：

- `references/writing-style.md`：风格指南
- `references/emotion-trigger-system.md`：情绪触发系统
- `references/angle-library.md`：切入角度库
- `references/hook-design.md`：开头钩子设计
- `references/content-principles-dbs.md`：dbskill 内容原则摘录
- `references/quality-checklist.md`：四层质量检查清单
- `references/expansion-methodology.md`：公众号长文扩写方法论
- `references/ai-flavor-guide.md`：AI 味治理指南
- `references/writing-checklist.md`：写作检查清单（内容债/语言债诊断）

## 触发条件

- 用户说"我想写公众号文章"
- 用户说"帮我写篇文章"
- 用户提供写作素材/主题
- 用户说"继续写文章"

## 入口流程

1. 读取 `wechat-article-core/VERSION`，输出触发反馈；主 skill 生成或读取 `article_id`；执行版本自检（读取本 skill 目录下 `.last-update-check`，距今超过 30 天则对比远程 origin HEAD，确认落后时在当前任务完成后提示用户更新，不自动执行）。
2. **主 skill 读取 `config.yaml`，解析三个路径与可选依赖配置。**
3. **调用 `scripts/init_checker.py` 进行路径初始化检查：**
   - 如果 `config.yaml` 中 `paths.*.value` 未配置，询问用户确认或修改三个路径。
   - 验证路径可用性，自动创建缺失的输出目录和模板目录。
   - 将确认后的路径写回 `config.yaml`。
   - `init_checker.py` 返回解析后的路径字典，由主 skill 写入 `context.md.paths`。
4. **调用 `scripts/style_selector.py` 进行风格选择与素材读取：**
   - 主 skill 将 `context.md.paths.input_dir` 和 `materials.recursive` 传入 `style_selector.scan_materials()`。
   - 完整读取所有 `.md` 素材，生成 `materials_full.md` 保存到 `output_dir/<article_id>/materials/`。
   - 主 skill 调用 `template_loader.list_all_templates(...)` 获取可用风格，
     再调用 `style_selector.recommend_styles(topic, materials_summary["summary_text"], templates)` 生成推荐列表。
   - 主 skill 展示 **Top 3 推荐模板**，按推荐度从高到低排列（1 为最推荐，2 次之，3 再次之），每个模板必须给出匹配理由。
   - **等待用户从 Top 3 中明确选择一个**；若用户不满意，可要求重新推荐或手动指定其他模板。
   - **用户手动指定模板时**，主 skill 调用 `style_selector.validate_template_id(template_id, templates)` 进行白名单校验；不在白名单内的模板禁止选用。
   - **用户确认选择后**，主 skill 将 `selected_template` 写入 `context.md`，并设置 `selected_template.confirmed = true`。
   - 主 skill 读取以下参考文件，提取核心要点，生成 `reference_briefs` 并写入 `context.md`：
     - 大纲/角度类：`wechat-article-core/references/angle-library.md`、`hook-design.md`、`content-outline-framework.md`
     - 内容/情绪类：`content-principles-dbs.md`、`emotion-trigger-system.md`
     - 写作/润色类：`writing-style.md`、`writing-checklist.md`、`expansion-methodology.md`、`ai-flavor-guide.md`
     - 质量检查类：`quality-checklist.md`
     - 标题类：`references/bigpeng/title-formulas.md`、`references/bigpeng/topic-templates.md`、`references/bigpeng/title-corpus.md`、`references/bigpeng/qa-checklist.md`
5. 调用 `scripts/dep_checker.py` 检查可选依赖状态（baoyu 技能 + WPS skill），
   由主 skill 写入 `context.md.optional_deps`。
6. 创建或读取 `output_dir/<article_id>/context.md`；若同目录下 `progress.md` 存在，则读取并恢复 `stage` 与关键决策，按 `blocked.md` 继续等待用户确认；否则按初始 stage 启动新流程。
7. **调用 `scripts/stage_validator.py` 决定并校验下一步：**
   - 主 skill 调用 `stage_validator.decide_next_stage(progress.md)` 获取当前 stage。
   - 每次推进到下一个 stage 前，调用 `stage_validator.validate_next_step()` 校验阶段转换、必要字段、模板白名单和 narrative_protocol 完整性。
   - 校验失败时，主 skill 停留在当前 stage，展示错误信息并等待用户处理。
8. 根据当前 `stage` 调用对应子技能（后续流程在已选风格语境下进行）。

每个 AI 输出节点（大纲候选、正文初稿、润色稿、标题候选、自检报告）之后均设置人工审阅节点，用户可确认、修改或要求重生成。

## 阶段定义

| stage | 下一步动作 | 调用的子技能 | 类型 |
|-------|-----------|-------------|------|
| init | 路径初始化检查 + 风格选择 | init_checker.py + style_selector.py（主 skill 内部） | AI |
| clarify | 需求澄清 | wechat-article-clarify | 人工 |
| template_loaded | 加载模板 + 生成 narrative_protocol | template_loader.py（主 skill 内部加载） | AI |
| angle_diagnosed | 素材诊断 | wechat-article-angle | AI |
| role_boundary | 人-AI 协作契约书确认 | （主 skill 内部） | 人工 |
| angle_matched | 生成候选大纲 | wechat-article-outline | AI |
| outline_generated | 选择/修改大纲 | （人工） | 人工 |
| outline_selected | 确认开始写正文 | （人工） | 人工 |
| outline_confirmed | 分段写正文 | khazix-writer | AI |
| draft_written | 二次改写正文 | （人工） | 人工 |
| draft_revised | 小标题优化 + 润色 | wechat-article-polish | AI |
| polished | 审阅润色稿 → 提炼标题候选 | （人工审阅）+ wechat-article-title(article) | 人工+AI |
| titled | 选择/修改标题 | （人工） | 人工 |
| title_confirmed | 质量自检 | wechat-article-quality | AI |
| quality_failed | 返回润色 | wechat-article-polish | AI（循环） |
| quality_checked | 终审定稿 | （人工） | 人工 |
| finalized | 输出 Markdown | （主 skill 内部） | AI |
| markdown_output | 发布/保存决策 | （人工） | 人工 |
| publish_decision | 保存/推送 | wps-skill / baoyu-post-to-wechat | AI/外部 |

## 阶段路由与硬闸门

核心 BLOCKING 节点必须满足以下条件才能推进：

| stage | 进入前提 | 必须存在的字段/文件 | 用户确认要求 | 未满足时行为 | 推进后 stage |
|-------|---------|------------------|------------|-----------|------------|
| init | 新流程或 `progress.md` 不存在 | `paths` 已配置 | `selected_template.confirmed = true` | 停留在 init 等待用户选择并确认模板 | clarify |
| clarify | 新流程或 `progress.md.stage = clarify` | `context.md` 已创建 | `requirements` 已写入且用户确认 | 重复展示需求确认卡，停留在 clarify | template_loaded |
| template_loaded | `clarify` 已完成 | `requirements` 已写入；`selected_template.confirmed = true`；`reference_briefs` 已写入 | 无（AI 自动节点） | 重新加载模板并生成 `narrative_protocol` | angle_diagnosed |
| angle_diagnosed | `template_loaded` 已完成 | `narrative_protocol` 已生成 | 无（AI 自动节点） | 重新运行 `wechat-article-angle` | role_boundary |
| role_boundary | `angle_diagnosed` 已完成 | `angle_candidates`、`diagnosis_report` | `collaboration_charter.confirmed = true` | 重复展示契约书，停留在 role_boundary | angle_matched |
| outline_generated | `angle_matched` 已完成 | `outline_candidates` | `selected_outline` 已写入 | 重复展示大纲候选，停留在 outline_generated | outline_selected |
| outline_selected | `outline_generated` 已完成 | `selected_outline` | 用户明确确认"开始写正文" | 停留在大纲确认节点，提示用户确认或修改大纲 | outline_confirmed |
| outline_confirmed | `outline_selected` 已完成 | `selected_outline` 且 `outline_confirmed = true` | 无（AI 自动节点） | 校验 section 覆盖完整性，缺失时返回 outline_generated | draft_written |
| draft_written | `outline_confirmed` 已完成 | `article_draft.md` | `draft_revised = true` 且 `draft_revised_path` 非空 | 提示用户先二次改写，停留在 draft_written | draft_revised |
| draft_revised | `draft_written` 已完成 | `draft_revised_path` | 无（AI 自动节点） | 重新运行 `wechat-article-polish` | polished |
| polished | `draft_revised` 已完成 | `polished_draft_path` | 人工审阅润色稿通过 | 停留在 polished 等待审阅润色稿 | titled |
| titled | `polished` 已完成 | `title_candidates` | `selected_title` 已写入 | 重复展示标题候选，停留在 titled | title_confirmed |
| quality_checked | `title_confirmed` 已完成 | `quality_report` | 用户终审定稿确认 | 重复展示质量报告，停留在 quality_checked | finalized |

### stage 说明

- `init`：由主 skill 内部调用 `init_checker.py` 完成三路径初始化，并调用 `style_selector.py` 完成风格选择，结果写入 `context.md`。
- `template_loaded`：主 skill 检查 `selected_template.confirmed == true`，然后加载对应 YAML 模板，并调用 `template_loader.extract_narrative_protocol()` 生成 `narrative_protocol`。若未确认，停留在 `init` 阶段等待用户确认。
- `angle_diagnosed`：由 `wechat-article-angle` 完成素材诊断并推荐角度。
- `role_boundary`：阻塞式人工节点，用户确认协作契约书后才能进入 `angle_matched`。
- `outline_selected`：用户从 `outline_candidates` 中选定一个大纲。选定后**必须额外确认一次"开始写正文"**，才能进入 `outline_confirmed`。
- `outline_confirmed`：由主 skill 调用 `template_loader.validate_sections_coverage()` 校验大纲是否完整覆盖 `narrative_protocol.sections`。校验通过后进入 `draft_written`。
- `draft_revised`：用户在正文初稿二次改写后进入，由 AI 执行小标题优化 + 润色。
- `polished`：用户先人工审阅润色稿，通过后由 AI 提炼标题候选（该步骤已合并到 `polished` 内完成「人工审阅 + AI 提炼」两步）。
- `quality_failed`：`wechat-article-quality` 评分低于 70 或出现 hard-fail 时进入，返回 `wechat-article-polish` 重新润色，循环直到质量达标。
- `finalized`：用户在终审定稿后进入，由 AI 生成最终 Markdown。

## 流程闭环规则（强制）

为保证文章输出有结构、有小标题、有质量把关，主 skill 必须按以下规则调度，**任何情况下都不允许跳过或替换核心子 skill**：

1. **核心子 skill 调用链不可变更**
   - `outline_selected` 阶段必须调用 `khazix-writer` 写正文初稿。
   - `draft_revised` 阶段必须调用 `wechat-article-polish` 做润色和小标题优化。
   - `title_confirmed` 阶段必须调用 `wechat-article-quality` 做质量自检。
   - **禁止用 `human-writing` 或其他任何写作 skill 替代 `khazix-writer` 或 `wechat-article-polish`。**

2. **stage 必须顺序推进，不允许跳过**
   完整链路为：
   ```
   init → clarify → template_loaded → angle_diagnosed → role_boundary → angle_matched
   → outline_generated → outline_selected → outline_confirmed → draft_written → draft_revised
   → polished → titled → title_confirmed → quality_checked
   → finalized → markdown_output → publish_decision
   ```
   - 每个 AI/人工节点结束后，主 skill 必须更新 `context.md.stage` 到下一阶段。
   - 主 skill 每次启动时，先调用 `stage_validator.decide_next_stage(progress.md)` 恢复当前阶段，再调用 `stage_validator.validate_next_step()` 校验下一步合法性。
   - 不允许跳过任何 stage 或核心子 skill。

3. **核心子 skill 缺失时停止，不自动 fallback**
   - 如果 `khazix-writer`、`wechat-article-polish`、`wechat-article-outline`、`wechat-article-quality` 任一核心子 skill 缺失或调用失败，主 skill 应明确提示用户并**暂停流程**，等待用户处理。
   - 只有可选外部 skill（插图、封面、WPS、发布等）缺失时才允许 fallback 为保存 Markdown。

4. **用户二次改写是必经人工节点**
   - `khazix-writer` 输出初稿后，必须进入 `draft_written` 人工节点，由用户确认或修改。
   - 用户确认后，主 skill 将 `draft_revised` 置为 `true` 并保存到 `draft_revised_path`，再进入 `wechat-article-polish`。
   - 禁止用 AI 自动代替用户完成二次改写。

5. **role_boundary 是阻塞式人工节点**
   - 用户必须确认 `collaboration_charter` 后，才能进入 `angle_matched`。
   - 未确认时，主 skill 停留在 `role_boundary` 阶段，重复展示契约书等待用户回复。

6. **输出目录结构化**：所有产物按 `output_dir/<article_id>/` 组织，详见「输出目录结构」章节。

7. **流程持久化**：主 skill 维护 `progress.md` 与 `blocked.md`，会话启动时先读取 `progress.md` 恢复状态，详见「长流程持久化文件」章节。

8. **版本自检**：每 30 天检查一次远程仓库是否有更新，详见「版本自检」章节。

## role_boundary 阶段（人-AI 协作契约书）

### 位置

`angle_diagnosed` 之后，`angle_matched` 之前。

### 类型

阻塞式人工节点。用户未确认前，不进入大纲生成。

### 输出

主 skill 输出《人-AI 协作契约书》，包含：

- **AI 负责做**：推荐角度、生成大纲、找证据/类比、按角度扩写、结构优化、质量自检。
- **必须由你来做**：第一手经历、核心角度拍板、情绪节点、关键金句、二次改写、终审定稿。
- **当前需要你确认**：素材是否足够、是否有真实经验、是否严格遵循模板结构、缺真实经历时如何处理。

用户确认后，主 skill 将 `collaboration_charter.confirmed` 置为 `true` 并写入 `context.md`。

## 可选依赖调用规范

调用外部技能前，先检查 `context.md` 中的 `optional_deps`：

- `installed`：直接调用对应 skill。
- `missing`：提示一次"XX 未安装，是否跳过？"，不阻塞。

外部 skill ID：
- 文章插图：`jimliu/baoyu-skills@baoyu-image-gen`
- 封面图：`jimliu/baoyu-skills@baoyu-cover-image`
- Markdown 转 HTML：`jimliu/baoyu-skills@baoyu-markdown-to-html`
- 发布到公众号：`jimliu/baoyu-skills@baoyu-post-to-wechat`
- 保存到本地 Word：`wps-skill`
  - 路径由环境变量 `WECHAT_ARTICLE_WPS_SKILL_PATH` 控制
  - 默认路径：`~/.agents/skills/wps`
  - 未安装时不阻塞，fallback 为保存 `.md` 文件

## 上下文协议

所有子技能通过 `context.md` 共享状态：

```markdown
---
article_id: <uuid>
stage: outline_generated
paths:                                # init_checker.py 写入
  input_dir: /home/user/Documents/素材
  output_dir: /home/user/Documents/稿子
  user_templates_dir: /home/user/wechat-article-templates
selected_template:                    # style_selector.py 写入
  id: social-slice
  name: 社会切片叙事型
  path: knowledge/templates/social-slice.yaml
  match_score: 5
  match_reason: 匹配信号命中 2 条
  confirmed: false                    # 用户确认后设为 true
materials_summary:
  fully_loaded: true
  recursive: false
  total_files: 3
  total_chars: 12580
  files:
    - name: 采访记录.md
      chars: 5420
      path: /home/user/Documents/素材/采访记录.md
  summary_text: "..."
  materials_path: /home/user/wechat-article-output/<article_id>/materials/materials_full.md

narrative_protocol:                 # 由 template_loader.extract_narrative_protocol() 生成，字段值来自所选模板（示例取自 social-slice）
  derived_from: social-slice
  fully_loaded: true                # 模板 100% 阅读：true 表示结构参考完整可用
  completeness_errors: []           # 完整读取失败时列出具体错误
  sections:
    - name: 现在
      purpose: 用一个具体画面把人物推出来
      length: 150-300
      must_include:
        - 具体时间/场景
        - 人物动作
        - 反常或矛盾
  global_rules:
    opening: 从具体人物具体时刻开始
    progression: 每写一段只推进一层
  tone: 克制、平视、有温度
  forbidden_zone:                   # 该清单由模板 YAML 的 forbidden_zone 字段解析而来
    - 第一人称"我""我们"
    - "随着AI时代的到来"

reference_briefs:                     # 由主 skill 在 init 阶段读取参考文件并提取核心要点
  expansion_methodology: "..."
  hook_design: "..."
  outline_framework: "..."
  content_principles: "..."
  angle_library: "..."
  emotion_trigger_system: "..."
  writing_style: "..."
  writing_checklist: "..."
  ai_flavor_guide: "..."
  quality_checklist: "..."
  bigpeng_title_formulas: "..."
  bigpeng_topic_templates: "..."
  bigpeng_title_corpus: "..."
  bigpeng_qa_checklist: "..."

collaboration_charter:
  ai_owned:
    - 推荐角度
    - 生成大纲
  human_required:
    - 第一手经历
    - 核心角度拍板
  user_preference:
    materials_sufficient: true        # 素材是否足够
    has_real_experience: true         # 是否有第一手真实经历
    strict_template: true
    missing_experience_handling: 占位符
  confirmed: false
template: social-slice
requirements:                         # wechat-article-clarify 写入
  topic: ""
  target_reader: ""
  core_points: []
  word_count: 2500
  materials: []
  speaker_position:
    who: ""
    credential: ""
    trigger: ""
selected_angle: A1
emotion_trigger: 找共鸣
secondary_trigger: 当嘴替
article_type: social-slice              # 文章类型，从 selected_template.id 映射
emotion_tone: "克制、平视、有温度"      # 情绪基调，从 selected_template 情绪基调提取
angle_candidates: []                  # wechat-article-angle 写入
diagnosis_report: {}                  # wechat-article-angle 写入
word_count: 2500
outline_candidates:                   # wechat-article-outline 写入
  - rank: 1
    angle: A1
    title: "..."
    thesis: "..."
    supporting_points:
      - "..."
      - "..."
    persuasion_strategies:
      - "数据驱动"
      - "故事驱动"
    emotion_goal: "找共鸣"
    emotion_arc: "低落 → 好奇 → 反转 → 高潮"
    key_quotes:
      - "..."
    closing_hook: "提问"
    sections:
      - section: "..."
        purpose: "..."
    reason: "..."
    scenario: "..."
    risk: "..."
selected_outline: <uuid or index>
draft_path: article_draft.md          # khazix-writer 写入
draft_revised: false
draft_revised_path: article_draft_revised.md  # 用户二次改写后保存路径
polished_draft_path: polished_draft.md  # wechat-article-polish 写入
title_candidates:                     # wechat-article-title 写入
  - rank: 1
    formula: 数字清单
    title: "..."
    emotion_trigger: "找共鸣"
    core_conflict: "..."
    reason: "..."
    scenario: "..."
    risk: "..."
selected_title: ""
quality_report: {}                    # wechat-article-quality 写入
fixed_text: ""                        # wechat-article-quality 自动修复后的文本
finalized: false
final_markdown_path: article.md       # 终稿 Markdown 路径
publish_choice: ""                    # 用户选择的发布去向（wps / wechat / markdown / html）
publish_status: pending               # pending / success / failed
optional_deps:
  baoyu-image-gen: installed
  baoyu-cover-image: missing
  baoyu-markdown-to-html: installed
  baoyu-post-to-wechat: missing
  wps-skill: missing
version: 0.3.5
---
```

关键字段说明：

- `stage`：当前所处阶段，人工节点等待用户输入时停留在对应 stage。
- `paths`：由 `init_checker.py` 写入并持久化的三个路径（输入目录、输出目录、用户模板目录）。
- `selected_template`：由 `style_selector.py` 写入，记录用户选定的风格模板及匹配理由。用户确认后 `confirmed` 置为 `true`，未确认时禁止生成 `narrative_protocol`。
- `materials_summary`：由 `style_selector.py` 写入，记录素材完整读取结果（`fully_loaded`、`recursive`、`total_files`、`total_chars`、`files`、`summary_text`、`materials_path`）。
- `narrative_protocol`：由 `template_loader.extract_narrative_protocol()` 基于 `selected_template` 生成，包含 `derived_from`、`sections`、`global_rules`、`tone`、`forbidden_zone`，供 `khazix-writer` / `wechat-article-polish` 等写作子 skill 引用。
- `reference_briefs`：由主 skill 在 init 阶段读取所有参考文件（角度库、钩子设计、内容原则、情绪触发、写作风格、扩写方法论、AI 味治理、质量检查清单、标题公式/案例/QA 等）并提取核心要点，供下游所有子 skill 引用。
- `collaboration_charter`：人-AI 协作契约书，包含 `ai_owned`、`human_required`、`user_preference`、`confirmed`，在 `role_boundary` 阶段由用户确认后置 `confirmed: true`。
- `requirements`：需求澄清结果，包含主题、目标读者、核心观点、字数、素材、说话人定位（`speaker_position.who` / `credential` / `trigger`）等。
- `selected_angle` / `emotion_trigger` / `secondary_trigger`：由 wechat-article-angle 选定并写入。
- `article_type`：文章类型，从 `selected_template.id` 映射，供 wechat-article-quality 做 frontmatter 检查。
- `emotion_tone`：情绪基调，从风格模板 `情绪基调` 提取的关键词，供 wechat-article-quality 做 frontmatter 检查。
- `angle_candidates`：wechat-article-angle 生成的可用角度列表。
- `diagnosis_report`：素材诊断报告。
- `outline_candidates`：排序后的大纲候选列表，每项包含 thesis、supporting_points、persuasion_strategies、emotion_goal、emotion_arc、key_quotes、closing_hook、sections 等。
- `selected_outline`：用户选定的大纲。
- `draft_path`：正文初稿文件路径（默认 `article_draft.md`）。
- `draft_revised`：正文是否已完成二次改写。
- `draft_revised_path`：用户二次改写后的正文保存路径（默认 `article_draft_revised.md`）。
- `polished_draft_path`：润色后正文文件路径（默认 `polished_draft.md`）。
- `title_candidates`：排序后的标题候选列表，每项包含 emotion_trigger、core_conflict 等。
- `selected_title`：用户选定的最终标题。
- `quality_report`：四层自检报告，供终审定稿使用。
- `fixed_text`：自检自动修复后的文本（如有）。
- `finalized`：是否已终审定稿。
- `final_markdown_path`：最终生成的 Markdown 文件路径（默认 `article.md`）。
- `publish_choice`：用户选择的最终去向（`wps` / `wechat` / `markdown` / `html`）。
- `publish_status`：发布/保存状态（`pending` / `success` / `failed`）。
- `optional_deps`：可选外部 skill 的安装状态。

## 发布/保存决策

`markdown_output` 阶段完成后，进入 `publish_decision`，由用户选择最终去向。
主 skill 将用户选择写入 `context.md.publish_choice`，执行后更新 `context.md.publish_status`（`pending` / `success` / `failed`）和 `context.md.final_markdown_path`。

| 选项 | 条件 | 动作 | 缺失 fallback |
|---|---|---|---|
| 保存到本地 Word | `wps-skill: installed` | 调用 WPS skill 生成 `.docx` | `wps-skill: missing` 时保存 `.md` |
| 保存到本地 Markdown | 任何情况 | 直接写入 `article.md` | 无 |
| 推送到公众号草稿箱 | `baoyu-post-to-wechat: installed` | 调用 baoyu 发布 skill | `baoyu-post-to-wechat: missing` 时保存 `.md` + HTML 到输出目录 |
| 保存为本地 HTML | `baoyu-markdown-to-html: installed` | 调用 baoyu 转换 skill 生成 `.html` | `baoyu-markdown-to-html: missing` 时仅保存 `.md` |
| 仅展示结果 | 任何情况 | 输出 Markdown，不保存 | 无 |

**缺失依赖时的统一 fallback 行为：**

- 任何外部 skill 缺失时，都不阻塞核心流程。
- 如果用户选择了一项缺失外部 skill 的选项，主 skill 应提示一次，然后 fallback 为保存 Markdown 到 `context.md.paths.output_dir`。
- `final_markdown_path` 始终指向最终保存的 Markdown 文件（无论是否成功调用外部 skill）。

---

## 触发反馈

- **首次触发**：`✅ 公众号长文写作写作中……`
- **阶段切换**：`当前步骤：{current_stage} → {next_stage}`
- **长时间未推进**：自上次 stage 变化后，经过 5 次用户消息仍未推进时，提示当前 stage 和下一步预期。

## 输出

- 核心交付物：`article.md`（带 frontmatter）
- 可选交付物：插图、封面、HTML、发布结果

## 辅助脚本

本 skill 目录下 `scripts/` 中的脚本用于支持主编排流程中的确定性操作。
脚本的调用契约：**主 skill 负责读取 `config.yaml` 并解析路径/依赖配置，将解析结果作为参数传入脚本；脚本返回结构化结果，由主 skill 写入 `context.md`。**

- `scripts/init_checker.py`：检查 `config.yaml` 中的三个路径配置，与用户确认后写回 `config.yaml`，并返回解析后的路径字典。主 skill 将其写入 `context.md.paths`。
- `scripts/style_selector.py`：接收输入目录路径和可用模板列表，扫描素材并基于 `match_signals` 推荐最匹配的风格。主 skill 将结果写入 `context.md.selected_template` 和 `context.md.materials_summary`。
- `scripts/dep_checker.py`：读取 `config.yaml` 的 `optional_dependencies`，检查可选外部 skill 的安装状态并返回。主 skill 将其写入 `context.md.optional_deps`。
- `scripts/template_loader.py`：接收默认模板目录和用户模板目录，加载/合并 YAML 模板规则，供主 skill 和其他子技能使用。

## 输出目录结构

```
output_dir/
└── <article_id>/
    ├── context.md
    ├── article.md
    ├── progress.md        # 当前 stage、关键决策、风险点
    ├── blocked.md         # 等待用户确认的内容
    ├── materials/
    │   └── materials_full.md
    ├── drafts/
    │   ├── article_draft.md
    │   ├── article_draft_revised.md
    │   └── polished_draft.md
    ├── outlines/
    │   └── outline_candidates.md
    ├── titles/
    │   └── title_candidates.md
    └── reports/
        └── quality_report.md
```

## 长流程持久化文件

- `progress.md`：当前 stage、已完成的关键决策、风险点
- `blocked.md`：等待用户确认或补充的项
- `materials_full.md`：已完整读取的素材

## 版本自检

本 skill 目录下维护 `.last-update-check` 文件，记录最近一次检查远程仓库的日期。

- 文件存在且距今不足 30 天：跳过自检
- 文件不存在或超过 30 天：对比本地 commit 与远程 origin HEAD
- 确认落后时，在当前任务完成后提示用户更新，不自动执行
