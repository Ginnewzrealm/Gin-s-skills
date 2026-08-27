# gin-wechat-article-core 优化设计文档

- **日期**：2026-08-25
- **范围**：已安装于 `~/.claude/skills/agents-bridge/skills/` 的微信公众号长文写作技能簇
- **策略**：路线 A —— 保留多 skill 编排，精简阶段，强化核心节点
- **状态**：已获用户认可，待实现

---

## 一、当前全技能簇问题清单

### 1. gin-wechat-article-core（主编排层）

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 1.1 | 素材读取截断 | `scripts/style_selector.py:96` | `summarize_materials(files, max_chars=1200)` 只读前 1200 字符 | 长素材丢失，angle/outline/writer 基于不完整信息判断 |
| 1.2 | 扫描默认递归 | `scripts/style_selector.py:25` | `scan_materials(input_dir, max_depth=1)` 默认扫 1 层子目录 | 可能读到无关文件，污染素材 |
| 1.3 | 模板叙事规则未结构化 | `scripts/template_loader.py` | 只加载原始 YAML 字段，没有提取 `narrative_protocol` | outline/writer 只能"参考"模板，无法强制执行 |
| 1.4 | 缺少人-AI 分工确认 | `SKILL.md` 阶段表 | 没有显式 stage 让用户确认分工 | 用户不清楚 AI 能做什么、自己必须做什么 |
| 1.5 | 流程节点过多 | `SKILL.md` 阶段表 | `polish_confirmed` 作为必经人工节点 | 增加不必要的确认成本 |
| 1.6 | 上下文缺少 narrative_protocol | `SKILL.md` 上下文协议 | context.md 字段中没有 narrative_protocol | 子 skill 无法读取结构化叙事规则 |
| 1.7 | materials_summary 非结构化 | `SKILL.md` 上下文协议 | `materials_summary` 是字符串 | 子 skill 无法精确索引素材 |
| 1.8 | 缺少输出目录结构 | `SKILL.md` | 没有定义 `<article_id>/` 下的目录组织 | 产物混乱，调试困难 |
| 1.9 | 缺少流程持久化 | `SKILL.md` | 没有 progress.md / blocked.md | 会话截断后难以恢复 |
| 1.10 | 缺少版本自检 | `SKILL.md` | 没有检查本地 skill 是否落后于远程 | 用户可能长期运行旧版本 |

### 2. gin-wechat-article-outline

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 2.1 | 大纲不按 narrative_protocol 生成 | `SKILL.md:37` | "复用风格文件中的 `结构参考` 列表格式" | 只复用格式，不强制按模板叙事结构填充 |
| 2.2 | 缺少素材映射 | `SKILL.md` 输出章节 | sections 只有 section/purpose，没有 materials_ref/human_needed | writer 无法判断每个 section 素材支撑情况 |
| 2.3 | 没有消费扩写方法论 | `SKILL.md` 输入章节 | 没有读取 expansion-methodology.md | 大纲生成时不会按内容骨架和材料优先原则规划 |
| 2.4 | 输入缺少 narrative_protocol | `SKILL.md` 输入章节 | 只读取模板规则 | 无法按模板结构生成大纲 |

### 3. gin-wechat-article-writer

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 3.1 | 缺少 narrative_protocol 输入 | `SKILL.md` 输入章节 | 没有 `context.md.narrative_protocol` | 无法按模板结构强制写作 |
| 3.2 | 缺少扩写方法论 | `SKILL.md` 第三步 | 只有卡兹克风格规则，没有通用中文写作纪律 | 风格对但结构散、AI 味重 |
| 3.3 | 人-AI 分工重复 | `SKILL.md` 第二步 | 详细写 AI 擅长/暴露 | 和 role_boundary 重复 |
| 3.4 | 自带四层自检，和 quality 重复 | `SKILL.md` 第四步 | 自己跑 L1-L4 检查 | 职责和 gin-wechat-article-quality 重叠 |
| 3.5 | 输出 frontmatter 缺少风格来源 | `SKILL.md` 输出章节 | 没有保留 narrative_protocol.derived_from | 质量检查无法追溯风格来源 |
| 3.6 | 没有素材映射消费 | `SKILL.md` | 没有按 outline.materials_ref 执行 | 需要重新判断每个 section 素材 |

### 4. gin-wechat-article-quality

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 4.1 | 不读取 narrative_protocol.forbidden_zone | `SKILL.md` 输入章节 | 输入只有通用 references | 无法检查模板专属禁区 |
| 4.2 | 检查标准与 writer 不统一 | `SKILL.md` L1-L4 | 用的是卡兹克自己的四层体系 | 和扩写方法论脱节 |
| 4.3 | 没有内容债/语言债诊断 | `SKILL.md` | 没有区分内容问题和语言问题 | 用户不知道哪些是缺素材、哪些只是表述问题 |
| 4.4 | 缺少扩写方法论输入 | `SKILL.md` 输入章节 | 没有读取 expansion-methodology.md | 检查时缺少系统方法支撑 |

### 5. gin-wechat-article-polish

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 5.1 | 缺少 narrative_protocol 输入 | `SKILL.md` 输入章节 | 没有读取 narrative_protocol | 润色时可能偏离模板叙事约束 |
| 5.2 | 缺少扩写方法论输入 | `SKILL.md` 输入章节 | 没有读取 expansion-methodology.md | 去 AI 味时缺少系统方法 |

### 6. gin-wechat-article-title

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 6.1 | 没有利用 narrative_protocol | `SKILL.md` | 只读模板规则和情绪触发点 | 标题可能不符合模板的开头规则 |

### 7. gin-wechat-article-angle

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 7.1 | 基于截断素材做诊断 | `SKILL.md` 输入 | 读 `materials_summary` 字符串 | 长素材角度判断不准确 |
| 7.2 | 没有利用 narrative_protocol | `SKILL.md` | 只读模板规则 | 推荐角度时不知道模板叙事结构 |

### 8. gin-wechat-article-clarify

| 编号 | 问题 | 位置 | 表现 | 影响 |
|------|------|------|------|------|
| 8.1 | 缺少写前问题模板 | `SKILL.md` | 只问 5 个基础问题 | 没有挖掘"谁在说、为什么现在说"等关键信息 |

---

## 二、解决方案总览

### 2.1 素材层改造

#### 2.1.1 完整读取

- `style_selector.py` 移除 `max_chars=1200`
- 完整读取 `.md` 文件
- 生成 `materials_full.md` 持久化到 `output_dir/<article_id>/materials/`
- `materials_summary` 改为结构化 dict

#### 2.1.2 递归可配置

- `config.yaml` 增加 `materials.recursive: false`
- `scan_materials()` 增加 `recursive` 参数，默认不递归

### 2.2 风格层改造

#### 2.2.1 提取 narrative_protocol

- `template_loader.py` 增加 `extract_narrative_protocol()`
- 从 YAML 模板提取：
  - `结构参考` → sections
  - `怎么开头` → global_rules.opening
  - `怎么推进` → global_rules.progression
  - `怎么处理意外/转折` → global_rules.twist
  - `怎么"掏知识"` → global_rules.knowledge
  - `怎么处理读者` → global_rules.reader
  - `怎么结尾` → global_rules.ending
  - `情绪基调` → tone
  - `禁区` → forbidden_zone

#### 2.2.2 新增扩写方法论知识库（拆分为 3 个文件）

| 文件 | 内容 | 消费方 |
|------|------|--------|
| `gin-wechat-article-core/references/expansion-methodology.md` | 核心原则、材料优先、说话位置、内容骨架、中文句法纪律 | `gin-wechat-article-outline`、`gin-wechat-article-writer` |
| `gin-wechat-article-core/references/ai-flavor-guide.md` | 四层 AI 味模型、六种 AI 味诊断、24 种 AI 写作模式 | `gin-wechat-article-quality`、`gin-wechat-article-polish` |
| `gin-wechat-article-core/references/writing-checklist.md` | 通用禁用项、文采增强四机制、内容债/语言债诊断 | `gin-wechat-article-writer`、`gin-wechat-article-quality`、`gin-wechat-article-polish` |

拆分理由：避免单个 skill 读到无关内容，降低上下文噪音。

### 2.3 流程层改造

#### 2.3.1 新增 role_boundary

- 位置：`angle_diagnosed` 之后，`angle_matched` 之前
- 类型：阻塞式人工节点
- 输出：《人-AI 协作契约书》
- 写入 `context.md.collaboration_charter`

#### 2.3.2 删除 polish_confirmed

- 把 `polished` 和 `polish_confirmed` 合并
- 用户在 `polished` 节点审阅润色稿后直接进 `titled`

#### 2.3.3 输出目录结构化

```
output_dir/
└── <article_id>/
    ├── context.md
    ├── article.md
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

#### 2.3.4 流程持久化

- `progress.md`：当前 stage、关键决策、风险点
- `blocked.md`：等待用户确认或补充的项

#### 2.3.5 版本自检

- `.last-update-check` 每 30 天检查一次远程更新
- 本地落后时提示用户更新，不自动执行

### 2.4 子 skill 改造

| 子 skill | 新增输入 | 移除/调整 | 新增输出/行为 |
|---------|---------|----------|--------------|
| gin-wechat-article-clarify | 需求确认问题模板（含说话位置三问） | 不再收集素材内容 | requirements 增加 `speaker_position`，增加素材完整性确认 |
| gin-wechat-article-angle | `materials_full.md`、`narrative_protocol` | 不再依赖截断的字符串 summary | angle_candidates 增加与 narrative_protocol 的适配说明 |
| gin-wechat-article-outline | `narrative_protocol`、`expansion-methodology.md`、`materials_full.md` | sections 不按 narrative_protocol 生成的问题 | sections 增加 `materials_ref` 和 `human_needed` |
| gin-wechat-article-writer | `narrative_protocol`、`expansion-methodology.md`、`writing-checklist.md`、`writing-style.md`（精简版）、`outline.sections[].materials_ref` | 删除 AI 角色边界、删除四层自检、删除卡兹克个人风格绑定 | 按 section 规则扩写，只做轻量禁区扫描，标注 `ai_filled` / `needs_human_experience`，frontmatter 保留 `narrative_protocol_derived_from` |
| gin-wechat-article-polish | `narrative_protocol`、`ai-flavor-guide.md`、`writing-checklist.md` | 无 | 润色时遵守 narrative_protocol 的 tone 和 forbidden_zone |
| gin-wechat-article-title | `narrative_protocol.global_rules.opening` | 无 | 标题生成符合模板开头规则 |
| gin-wechat-article-quality | `narrative_protocol.forbidden_zone`、`ai-flavor-guide.md`、`writing-checklist.md`（完整版） | 调整 L1-L4 与方法论对齐 | 增加内容债/语言债诊断、模板专属禁区检查，统一负责完整四层质检 |

---

## 三、新流程

```text
init
  ↓
clarify → 人工确认
  ↓
template_loaded（加载模板 + 生成 narrative_protocol）
  ↓
angle_diagnosed（素材诊断）
  ↓
role_boundary → 人工确认（阻塞）
  ↓
angle_matched
  ↓
outline_generated → 人工确认
  ↓
outline_selected
  ↓
draft_written（gin-wechat-article-writer 出初稿）
  ↓
draft_revised → 人工改写
  ↓
polished
  ↓
titled
  ↓
title_confirmed → 人工确认
  ↓
quality_checked
  ↓
finalized → 人工确认
  ↓
markdown_output → publish_decision
```

**与原流程对比：**

| 原流程 | 新流程 | 说明 |
|--------|--------|------|
| init | init | 不变 |
| clarify | clarify | 增加写前说话位置问题 |
| template_loaded | template_loaded | 增加生成 narrative_protocol |
| angle_diagnosed | angle_diagnosed | 基于完整素材和 narrative_protocol 诊断 |
| angle_matched | **role_boundary** | 新增阻塞式人-AI 分工确认 |
| outline_generated | angle_matched | 原 angle_matched 下移 |
| outline_selected | outline_generated | 原 outline_generated 下移 |
| draft_written | outline_selected | 下移 |
| draft_revised | draft_written | 下移 |
| polished | draft_revised | 下移 |
| polish_confirmed | **polished** | 删除 polish_confirmed 节点 |
| titled | titled | 增加 narrative_protocol.opening 输入 |
| title_confirmed | title_confirmed | 不变 |
| quality_checked | quality_checked | 增加 narrative_protocol.forbidden_zone 输入 |
| finalized | finalized | 不变 |
| markdown_output | markdown_output | 增加二次确认 |
| publish_decision | publish_decision | 不变 |

---

## 四、关键设计

### 4.1 素材全读

#### 约束

- 素材默认只处理 `.md` 文件。
- 默认不递归子目录，避免读到无关文件。
- 是否递归作为配置项。
- PDF、语音等非文本文件先列出路径，后续接入专门 skill 处理。

#### 修改 `style_selector.py`

1. 移除 `summarize_materials()` 中的 `max_chars=1200` 限制。
2. `scan_materials()` 增加 `recursive` 参数，默认 `False`。
3. 完整读取 `input_dir` 下所有 `.md` 文件。
4. 生成 `materials_full.md`，保存到 `output_dir/<article_id>/materials/`。
5. `materials_summary` 改为结构化 dict，包含文件索引、字数、路径，不再截断正文。

#### 新增 context.md 字段

```yaml
materials_summary:
  fully_loaded: true
  recursive: false
  total_files: 3
  total_chars: 12580
  files:
    - name: 采访记录.md
      chars: 5420
      path: output/<article_id>/materials/采访记录.md
    - name: 数据笔记.md
      chars: 3160
      path: output/<article_id>/materials/数据笔记.md
    - name: 个人经历.md
      chars: 4000
      path: output/<article_id>/materials/个人经历.md
  summary_text: "..."  # 拼接后的全量文本，供需要快速消费的子 skill 使用
  materials_path: output/<article_id>/materials/materials_full.md
```

#### config.yaml 新增配置

```yaml
materials:
  recursive: false
  extensions:
    - ".md"
    - ".txt"
    - ".url"
```

### 4.2 narrative_protocol（叙事协议）

#### 目的

把 YAML 模板的叙事规则从「参考资料」升级为「强制执行协议」，确保大纲和正文都按模板的叙事结构生成。

#### 生成位置

`template_loaded` 阶段，由 `template_loader.py` 从选中的 YAML 模板中提取。

#### 来源

从 YAML 模板的以下字段提取：

| YAML 字段 | narrative_protocol 字段 |
|----------|------------------------|
| `meta.id` | `derived_from` |
| `结构参考` | `sections` |
| `怎么开头` | `global_rules.opening` |
| `怎么推进` | `global_rules.progression` |
| `怎么处理意外/转折` | `global_rules.twist` |
| `怎么"掏知识"` | `global_rules.knowledge` |
| `怎么处理读者` | `global_rules.reader` |
| `怎么结尾` | `global_rules.ending` |
| `情绪基调` | `tone` |
| `禁区` | `forbidden_zone` |

#### 结构

```yaml
narrative_protocol:
  derived_from: social-slice
  sections:
    - name: 现在
      purpose: 用一个具体画面把人物推出来
      length: 150-300
      must_include:
        - 具体时间/场景
        - 人物动作
        - 反常或矛盾
      forbidden:
        - 第一人称
        - 宏观背景起手
    - name: 之前
      purpose: 这个人是怎么走到这一步的
      length: 300-500
      must_include:
        - 学历或经历
        - 关键选择
    - name: 转折
      purpose: 改变轨迹的那个时刻
      length: 300-500
      must_include:
        - 具体事件
        - 他的反应
    - name: 现在进行时
      purpose: 他正在面对什么
      length: 300-500
      must_include:
        - 适应或挣扎的细节
        - 具体动作
    - name: 余声
      purpose: 回到一个画面，不做总结
      length: 150-250
      must_include:
        - 状态画面
        - 留白感
  global_rules:
    opening: 从具体人物具体时刻开始
    progression: 每写一段只推进一层
    twist: 转折来自人物处境本身的矛盾
    knowledge: 知识嵌入叙事，不是科普
    reader: 读者站在旁边一起看这个人
    ending: 状态画面/留白/回环呼应
  tone: 克制、平视、有温度
  forbidden_zone:
    - 第一人称"我""我们"
    - "随着AI时代的到来"
    - "你知道吗""相信大家都"
    - "首先...其次...最后""综上所述"
    - 作者情绪判断
    - 二元对立结论
    - 励志鸡汤
    - 简历式信息堆砌
    - 心理分析术语
    - 宏观叙事
    - 直接向读者提问
    - 对人物的道德评判
```

#### 写入 context.md

`narrative_protocol` 作为一级字段写入 `context.md`，供后续子 skill 读取。

### 4.3 改 gin-wechat-article-clarify

#### 新增问题

将原来的"可用素材收集"改为"素材完整性确认"，新增说话位置三问：

1. **主题确认**：文章要讨论什么？
2. **目标读者**：给谁看？（身份标签）
3. **核心观点/立场**：你最想表达什么判断？
4. **字数要求**：预计多长？
5. **说话位置**：
   - 谁在说这件事？（亲历者 / 调查者 / 观察者 / 研究者）
   - 他凭什么知道这些事？（亲历 / 查证 / 推测）
   - 他为什么现在想说这件事？（触发点是什么）
6. **素材完整性确认**：
   - 已提供的结构化素材是否足够支撑这个选题？
   - 还缺什么关键信息？（只确认缺口，不收集素材内容）

> **说明**：由于上游已有专门整理素材的 skill，`gin-wechat-article-clarify` 不再重复收集素材内容，只确认素材是否齐全、需求是否明确。

#### 新增输出字段

```yaml
requirements:
  topic: ""
  target_reader: ""
  core_points: []
  word_count: 2500
  materials: []
  speaker_position:
    who: ""        # 叙述者身份
    credential: "" # 凭什么知道
    trigger: ""    # 为什么现在说
  notes: ""
```

### 4.4 改 gin-wechat-article-angle

#### 输入增加

- `materials_full.md`（或完整 `materials_summary`）
- `context.md.narrative_protocol`
- `context.md.requirements.speaker_position`

#### 输出增强

`angle_candidates` 增加字段：

```yaml
angle_candidates:
  - id: A1
    name: ""
    description: ""
    narrative_fit: ""  # 与 narrative_protocol 的匹配度说明
    material_support:  # 素材支撑点
      - file: 采访记录.md
        excerpt: "..."
    risk: ""
```

### 4.5 改 gin-wechat-article-outline

#### 输入增加

- `context.md.narrative_protocol`
- `gin-wechat-article-core/references/expansion-methodology.md`
- `materials_full.md`

#### 输出要求

`outline_candidates[].sections` 必须按 `narrative_protocol.sections` 的顺序和职责生成。

每个 section 必须包含：

```yaml
sections:
  - name: "现在"
    purpose: "用一个具体画面把人物推出来"
    must_include:
      - 具体时间/场景
      - 人物动作
      - 反常或矛盾
    forbidden:
      - 第一人称
      - 宏观背景起手
    content: "..."           # 本 section 要写的内容方向
    materials_ref:           # 素材支撑
      - file: 采访记录.md
        excerpt: "..."
        used_as: "场景描写"
    human_needed:            # 必须用户补充的真实经历
      - 当时具体动作
      - 真实对话原话
    word_count_estimate: 250  # 预估字数
```

#### 原 Step 3 修改

原文：

> 章节结构（sections）复用风格文件中的 `结构参考` 列表格式。

改为：

> 章节结构（sections）必须严格按 `narrative_protocol.sections` 的顺序、职责和约束生成。每个 section 的名称、purpose、must_include、forbidden 从 narrative_protocol 复制，content 根据素材填充，并标注 `materials_ref` 和 `human_needed`。

### 4.6 改 gin-wechat-article-writer

#### 定位调整

`gin-wechat-article-writer` 不再绑定卡兹克个人风格。风格由 YAML 模板和 `references/writing-style.md` 共同控制，本 skill 只负责按 narrative_protocol 和通用扩写纪律执行扩写。

#### 输入增加

- `context.md.narrative_protocol`
- `gin-wechat-article-core/references/expansion-methodology.md`（精简执行版）
- `gin-wechat-article-core/references/writing-checklist.md`（精简执行版）
- `gin-wechat-article-core/references/writing-style.md`（通用活人感写作原则）
- `outline.sections[].materials_ref`
- `outline.sections[].human_needed`

#### 删除内容

1. **删除第二步"明确 AI 的角色边界"**
   - 理由：`role_boundary` 阶段已统一处理
   - 保留：执行层面的标注规则（`ai_filled`、`needs_human_experience`）

2. **删除第四步"四层自检体系"**
   - 理由：完整质量检查是 `gin-wechat-article-quality` 的职责
   - 保留：输出前轻量禁区扫描（只检查明显 hard-fail，不替代完整质检）

3. **删除卡兹克个人风格层**
   - 删除：核心价值观 4 条、卡兹克专属口语化词组、具体情绪标点用法、人物画像法、文化升维、亲自下场等绑定个人的风格表达
   - 迁移：通用活人感原则（节奏感、具体细节、灰度判断、对立面理解、情绪从动作出等）迁移到 `references/writing-style.md`
   - 保留：文章原型分类、结构模板、节奏控制、疑问句节奏、英雄之旅等通用叙事技巧作为扩写纪律的补充说明

#### 新增"扩写纪律"小节

```markdown
## 第三步：按 narrative_protocol 扩写正文

### 3.0 扩写纪律（执行时必须遵守）

每个 section 写作前，先回答：

1. **说话位置**
   - 本 section 谁在说话？凭什么知道？
   - 读者读完上一段会问什么？

2. **材料检查**
   - outline 里标注的 `materials_ref` 是否都已覆盖？
   - `must_include` 中哪些有素材？哪些缺？
   - 缺的只能：标注 `【需用户补充】` / 用已确认事实代替 / 缩短本 section

3. **推进检查**
   - 本段是否新增了至少一件事实、动作、例子或判断？
   - 下一段是否接住了本段留下的问题？
   - 没有同一观点换说法重复

4. **句法纪律**
   - 主干先行
   - 主语不重复
   - 抽象动作换成具体动作
   - 每个判断有细节托着
   - 情绪从动作里出来
   - 每段只完成一件事
   - 新段落增加新东西

5. **风格约束**
   - 遵守 `narrative_protocol.tone`
   - 遵守 `narrative_protocol.forbidden_zone`
   - 参考 `references/writing-style.md` 中的通用活人感原则

6. **禁区检查**
   - 无 narrative_protocol.forbidden_zone 中的条目
   - 无 writing-checklist.md 中的通用禁用项

7. **AI 味快速自检**
   - 不是太完整 / 太顺滑 / 太抽象 / 太客观 / 太会总结
```

#### 输出增强

frontmatter 增加：

```yaml
narrative_protocol_derived_from: social-slice
```

正文段落标注：

- `<!-- ai_filled -->`：AI 基于素材填充的段落
- `<!-- needs_human_experience -->`：需要用户补充真实经历的段落

### 4.7 改 gin-wechat-article-quality

#### 新增输入

- `context.md.narrative_protocol.forbidden_zone`
- `gin-wechat-article-core/references/ai-flavor-guide.md`（完整验收版）
- `gin-wechat-article-core/references/writing-checklist.md`（完整验收版）
- `gin-wechat-article-core/references/writing-style.md`（完整版）
- `context.md.narrative_protocol.derived_from`

#### 职责定位

`gin-wechat-article-quality` 是整个流程中**唯一负责完整四层质量检查**的节点。`gin-wechat-article-writer` 只输出前轻量禁区扫描，不替代 quality 的职责。

#### L1 检查增强

在原有通用禁用词检查基础上，增加模板专属禁区检查。命中 `forbidden_zone` 视为 hard-fail。

#### 引入内容债/语言债诊断

```markdown
### 内容债 vs 语言债诊断

**内容债**：
- 缺事实、无真实例子
- 无观点
- 受众不清
- 判断无支撑

**语言债**：
- AI 套话
- 结构过分整齐
- 连接词过多
- 被动语态
- 升华式结尾
- 过度顺滑

修复策略：
- 内容债 → 标注【需补素材】，不硬编
- 语言债 → 按规则改写
```

#### 四层检查与扩写方法论对齐

| 层级 | 对应方法论 | 检查重点 |
|------|-----------|---------|
| L1 | 通用禁用项 + narrative_protocol.forbidden_zone | hard rules |
| L2 | 句法纪律 + 风格一致性 | 节奏、口语化、标点 |
| L3 | 内容骨架 + 文采增强四机制 | 情境、判断、证据、方法、下一步 |
| L4 | 四层 AI 味模型 + 六种 AI 味诊断 | 经验层、活人感 |

### 4.8 改 gin-wechat-article-polish

#### 输入增加

- `context.md.narrative_protocol`
- `gin-wechat-article-core/references/ai-flavor-guide.md`
- `gin-wechat-article-core/references/writing-checklist.md`
- `gin-wechat-article-core/references/writing-style.md`

#### 润色规则

- 小标题优化时遵守 `narrative_protocol.sections` 的 purpose
- 去 AI 味时优先处理 `expansion-methodology.md` 中的高信号模式
- 保持 `narrative_protocol.tone`

### 4.9 改 gin-wechat-article-title

#### 输入增加

- `context.md.narrative_protocol.global_rules.opening`

#### 标题生成规则

- 标题必须符合作品模板的开头规则（如 social-slice 要求从具体人物切入）
- 标题情绪触发点与 `emotion_trigger` 一致

### 4.10 role_boundary（人-AI 协作契约书）

#### 位置

`angle_diagnosed` 之后，`angle_matched` 之前。

#### 阶段类型

阻塞式人工节点。用户不确认，流程不推进。

#### 输出《人-AI 协作契约书》

```markdown
## 本次写作的人-AI 协作契约书

### AI 负责做
- 基于已完整读取的素材推荐切入角度
- 根据选定的风格模板生成候选大纲
- 为观点找证据、类比、背景知识
- 按确定的角度和大纲扩写正文
- 优化结构、节奏、小标题
- 执行四层质量自检

### 必须由你来做
- 提供第一手观察、真实经历、具体对话
- 拍板最终用哪个核心角度
- 确定情绪节点（哪些段落要让读者感受到什么）
- 确认或改写关键金句/钩子
- 在初稿基础上二次改写，加入你的声音
- 终审定稿

### 当前需要你确认
- [ ] 已完整读取的素材是否足够支撑这个选题？
- [ ] 这个选题是否有你的真实经验或判断？
- [ ] 你希望我（AI）在大纲中严格遵循模板结构，还是可以灵活调整？
- [ ] 遇到缺真实经历的段落，我应该：写占位符 / 停下来问你 / 跳过不写？
```

#### 写入 context.md

```yaml
collaboration_charter:
  ai_owned:
    - 推荐角度
    - 生成大纲
    - 找证据/类比
    - 按角度扩写
    - 结构优化
    - 质量自检
  human_required:
    - 第一手经历
    - 核心角度拍板
    - 情绪节点
    - 关键金句
    - 二次改写
    - 终审定稿
  user_preference:
    strict_template: true
    missing_experience_handling: 占位符
  confirmed: false
  confirmed_at: ""
```

### 4.11 借鉴 baoyu：输出目录结构化

```
output_dir/
└── <article_id>/
    ├── context.md
    ├── article.md
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

### 4.12 借鉴花叔：文件持久化与版本自检

#### 文件持久化

持久化文件放在 `output_dir/<article_id>/` 根目录，与用户最终产物同处一个目录，方便跨会话恢复：

```
output_dir/
└── <article_id>/
    ├── context.md
    ├── article.md
    ├── progress.md        # 当前 stage、关键决策、风险点
    ├── blocked.md         # 等待用户确认的内容
    ├── materials/
    │   └── materials_full.md
    ...
```

- `progress.md`：当前 stage、关键决策、风险点
- `blocked.md`：等待用户确认或补充的项

#### 版本自检

- `gin-wechat-article-core` 目录下增加 `.last-update-check`
- 每 30 天检查一次远程仓库是否有更新
- 本地落后时提示用户更新，不自动执行

### 4.13 新增扩写方法论知识库（3 个文件）

#### 位置与职责

| 文件 | 内容 | 消费方 |
|------|------|--------|
| `gin-wechat-article-core/references/expansion-methodology.md` | 核心原则、材料优先、说话位置、内容骨架、中文句法纪律 | `gin-wechat-article-outline`、`gin-wechat-article-writer` |
| `gin-wechat-article-core/references/ai-flavor-guide.md` | 四层 AI 味模型、六种 AI 味诊断、24 种 AI 写作模式 | `gin-wechat-article-quality`、`gin-wechat-article-polish` |
| `gin-wechat-article-core/references/writing-checklist.md` | 通用禁用项、文采增强四机制、内容债/语言债诊断 | `gin-wechat-article-writer`、`gin-wechat-article-quality`、`gin-wechat-article-polish` |

#### expansion-methodology.md 内容结构

```markdown
# 公众号长文扩写方法论

## 一、核心原则
- 材料优先
- 说话位置
- 读者问题推进

## 二、写前定调（说话位置法）
### 2.1 谁在说
### 2.2 凭什么知道
### 2.3 为什么现在说

## 三、内容骨架
- 情境
- 判断
- 证据
- 方法/区分
- 下一步/后果/开放问题

## 四、中文句法纪律
- 主干先行
- 主语不重复
- 抽象动作具体化
- 判断有细节托着
- 后句接前问
- 情绪从动作出
- 每段只一事
- 新段增新东西
- 长短交替
```

#### ai-flavor-guide.md 内容结构

```markdown
# AI 味治理指南

## 一、四层 AI 味模型
- 词汇层
- 句式层
- 结构层
- 经验层

## 二、六种 AI 味诊断
1. 太完整
2. 太顺滑
3. 太抽象
4. 太客观
5. 太会总结
6. 清理后发扁

## 三、24 种 AI 写作模式
...
```

#### writing-checklist.md 内容结构

```markdown
# 写作检查清单

## 一、通用禁用项
- 翻案腔
- 三句以上同构排比
- 动词名词化
- 商业黑话
- 模型抒情词
- 模糊归因
- 口号式结尾

## 二、文采增强四机制
1. 命名处境
2. 让不可见可见
3. 给句子一个容器
4. 落回动作或证据

## 三、内容债 vs 语言债
- 内容债：缺事实、无观点、判断无支撑
- 语言债：套话、机械结构、过度顺滑
```

---

### 4.14 更新 `references/writing-style.md`

#### 定位

`references/writing-style.md` 从卡兹克个人风格指南改为**通用活人感写作原则**。具体风格由 YAML 模板控制，本文件只保留跨模板通用的基础原则。

#### 保留内容

```markdown
# 活人感写作通用原则

## 一、叙述者位置
- 明确谁在说话
- 说明凭什么知道
- 交代为什么现在说

## 二、材料优先
- 用具体事实、动作、数字、原话支撑判断
- 不编造用户未提供的个人经历

## 三、表达原则
- 讲人话，不用套话
- 敢下判断但保留灰度
- 先理解对立面，再给出视角
- 情绪从动作和事实里自然出来
- 长短句交替，制造节奏
- 每段只完成一件事
- 新段落必须增加新东西

## 四、通用禁区
- 教科书开头
- 翻案腔
- 模糊归因
- 口号式结尾
- 动词名词化
- 商业黑话
```

#### 删除内容

- 卡兹克个人核心价值观 4 条
- 卡兹克专属口语化词组（如"太特么赤鸡了"、"不是哥们"）
- 具体情绪标点用法（如"。。。"、"???"、"= ="）
- 人物画像法、文化升维、亲自下场等绑定个人的表达

#### 消费方

- `gin-wechat-article-writer`：参考通用活人感原则，但不绑定具体个人风格
- `gin-wechat-article-polish`：润色时参考
- `gin-wechat-article-quality`：检查通用风格一致性

---

## 五、修改文件清单

| 文件 | 改动内容 |
|------|---------|
| `gin-wechat-article-core/SKILL.md` | 更新流程，新增 `role_boundary`，删除 `polish_confirmed`，新增 `narrative_protocol` 和 `materials_summary` 字段说明，定义输出目录结构，增加持久化和版本自检 |
| `gin-wechat-article-core/scripts/style_selector.py` | 移除 `max_chars=1200`，完整读取 `.md`，生成 `materials_full.md`，`scan_materials()` 增加 `recursive` 参数 |
| `gin-wechat-article-core/scripts/template_loader.py` | 新增 `extract_narrative_protocol()` 函数 |
| `gin-wechat-article-core/config.yaml` | 新增 `materials.recursive` 和 `materials.extensions` 配置 |
| `gin-wechat-article-core/references/expansion-methodology.md` | 新增：核心原则、材料优先、说话位置、内容骨架、中文句法纪律 |
| `gin-wechat-article-core/references/ai-flavor-guide.md` | 新增：四层 AI 味模型、六种诊断、24 种 AI 写作模式 |
| `gin-wechat-article-core/references/writing-checklist.md` | 新增：通用禁用项、文采增强四机制、内容债/语言债诊断 |
| `gin-wechat-article-core/references/writing-style.md` | 更新/新增：通用活人感写作原则（去卡兹克个人绑定） |
| `gin-wechat-article-clarify/SKILL.md` | 调整为需求确认 + 素材完整性确认，增加说话位置三问 |
| `gin-wechat-article-angle/SKILL.md` | 输入增加完整素材和 `narrative_protocol`，输出增加 `narrative_fit` 和 `material_support` |
| `gin-wechat-article-outline/SKILL.md` | 输入增加 `narrative_protocol`、`expansion-methodology.md`、完整素材；输出 sections 必须按协议生成，并增加 `materials_ref` 和 `human_needed` |
| `gin-wechat-article-writer/SKILL.md` | 输入增加 `narrative_protocol`、`expansion-methodology.md`、`writing-checklist.md`、`writing-style.md`（精简版）、`outline.sections[].materials_ref`；删除 AI 角色边界、四层自检、卡兹克个人风格绑定；新增"扩写纪律"小节；frontmatter 保留 `narrative_protocol_derived_from` |
| `gin-wechat-article-polish/SKILL.md` | 输入增加 `narrative_protocol`、`ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md` |
| `gin-wechat-article-title/SKILL.md` | 输入增加 `narrative_protocol.global_rules.opening` |
| `gin-wechat-article-quality/SKILL.md` | 读取 `narrative_protocol.forbidden_zone`、`ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md`（完整版），增加内容债/语言债诊断，四层检查与方法论对齐 |
| `gin-wechat-article-core/references/failure-handbook.md` | 新增失败降级表（可选） |

---

## 六、关键决策（已确认/待确认）

| 决策 | 结论 | 理由 |
|------|------|------|
| `polish_confirmed` 是否保留 | 去掉 | 路线 A 精简流程，终审定稿已足够把关 |
| `role_boundary` 是否阻塞 | 阻塞 | 确保用户在 AI 生成大纲前确认分工 |
| 素材读取是否递归 | 默认不递归，配置开启 | 避免读到无关文件 |
| `narrative_protocol` 来源 | YAML 模板的 `结构参考` + 其他叙事字段 | 复用现有字段，不改模板格式 |
| quality 是否读取模板禁区 | 是 | 否则风格一致性检查无效 |
| 扩写方法论放哪里 | 拆分为 3 个 references 文件 | 降低单个 skill 上下文噪音 |
| gin-wechat-article-writer 是否保留四层自检 | 否 | 统一由 gin-wechat-article-quality 负责 |
| gin-wechat-article-writer 是否保留 AI 角色边界说明 | 否 | 统一由 role_boundary 负责 |
| gin-wechat-article-writer 是否保留卡兹克个人风格绑定 | 否 | 风格由 YAML 模板和 writing-style.md 控制 |
| clarify 是否收集素材内容 | 否 | 上游已有素材整理 skill，clarify 只做完整性确认 |
| outline 是否输出素材映射 | 是 | 让 writer 不需要重新判断素材 |
| clarify 是否增加说话位置三问 | 是 | 从源头确定叙述者位置 |
| progress/blocked 放在哪里 | `output_dir/<article_id>/` 根目录 | 与文章产物同目录，方便恢复 |

---

## 七、实现阶段建议

### 第一阶段：基础改造

1. 改 `style_selector.py`：素材全读 + 递归开关。
2. 改 `config.yaml`：增加 materials 配置。
3. 改 `template_loader.py`：生成 `narrative_protocol`。
4. 新增 `references/expansion-methodology.md`、`references/ai-flavor-guide.md`、`references/writing-checklist.md`。
5. 更新 `references/writing-style.md`：改为通用活人感写作原则。
6. 更新 `gin-wechat-article-core/SKILL.md` 的 context.md 字段、流程、输出目录、持久化、版本自检。

### 第二阶段：上游子 skill 消费 narrative_protocol

1. 改 `gin-wechat-article-clarify`：从素材收集改为需求确认 + 素材完整性确认，增加说话位置三问。
2. 改 `gin-wechat-article-angle`：基于完整素材和 narrative_protocol 诊断。
3. 改 `gin-wechat-article-outline`：按 narrative_protocol 生成带素材映射的大纲。

### 第三阶段：下游子 skill 消费 narrative_protocol 和扩写方法论

1. 改 `gin-wechat-article-writer`：按 narrative_protocol 和通用扩写纪律写作，删除卡兹克个人风格绑定。
2. 改 `gin-wechat-article-polish`：按 narrative_protocol、ai-flavor-guide、writing-checklist、writing-style 润色。
3. 改 `gin-wechat-article-title`：按 narrative_protocol.opening 生成标题。
4. 改 `gin-wechat-article-quality`：读取模板禁区，按方法论验收。

### 第四阶段：新增 role_boundary

1. 在 `gin-wechat-article-core` 流程中插入 `role_boundary`。
2. 实现协作契约书输出和确认。
3. 写入 `context.md.collaboration_charter`。

---

## 八、验收标准

- [ ] `style_selector.py` 完整读取所有 `.md` 素材，不再截断。
- [ ] `materials_full.md` 生成在 `output_dir/<article_id>/materials/`。
- [ ] `materials_summary` 是结构化 dict，包含文件索引和路径。
- [ ] `context.md` 包含 `narrative_protocol` 字段。
- [ ] `context.md` 包含 `collaboration_charter` 字段。
- [ ] `gin-wechat-article-clarify` 输出 `requirements.speaker_position`。
- [ ] `gin-wechat-article-angle` 基于完整素材和 `narrative_protocol` 诊断。
- [ ] `gin-wechat-article-outline` 生成的大纲 sections 与 `narrative_protocol` 一一对应。
- [ ] `gin-wechat-article-outline` 的每个 section 包含 `materials_ref` 和 `human_needed`。
- [ ] `gin-wechat-article-writer` 正文段落能追溯到 `narrative_protocol` 的 section。
- [ ] `gin-wechat-article-writer` 输出中标注 `ai_filled` 和 `needs_human_experience`。
- [ ] `gin-wechat-article-quality` 能检测模板专属禁区。
- [ ] `gin-wechat-article-quality` 能做内容债/语言债诊断。
- [ ] `role_boundary` 阶段阻塞，用户确认后 `collaboration_charter.confirmed=true`。
- [ ] 输出目录按 `<article_id>` 结构化。
- [ ] `progress.md` 和 `blocked.md` 生成在 `output_dir/<article_id>/` 根目录。
- [ ] `progress.md` 和 `blocked.md` 在流程中维护。
