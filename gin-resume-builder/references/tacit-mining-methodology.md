---
name: tacit-mining-for-career
description: gin-resume-builder 的 STAR 隐性知识挖掘方法论，改编自 tacit-mining。
type: reference
---

# gin-resume-builder —— STAR 隐性知识挖掘方法论

> 基于 tacit-mining（Polanyi + CDM/Laddering/Repertory Grid）改编，用于职业经历挖掘。
>
> "We know more than we can tell." — Michael Polanyi

## 1. 核心原则

- **不问抽象标准，问具体行为**：不问"你的优势是什么"，问"那次你做了什么"。
- **每次只挖一个域、一件事**：深比广重要。
- **结构化归档**：所有挖出的事实必须变成 STAR 碎片写入知识库。
- **用户可跳过**：用户说"记不清/跳过/不想聊"时，记录为 fuzzy，不纠缠。

## 2. 挖掘域

| 域 | 说明 | 素材来源 | 典型产物 |
|---|---|---|---|
| `work_experience` | 工作经历中的关键判断与决策 | `work_history.md` + 当前对话 | 工作 STAR 碎片 |
| `project_experience` | 项目经历中的关键决策与难点 | `projects.md` + 当前对话 | 项目 STAR 碎片 |
| `skill_mastery` | 技能熟练度的行为支撑 | `skills.md` + 当前对话 | 技能佐证碎片 |
| `advantage_evidence` | 个人优势/岗位胜任的事实佐证 | `advantages.md` + 当前对话 | 优势佐证碎片 |

## 3. 语义触发条件

当用户话语满足以下 **2 个以上** 要素时，暂停主线，进入挖掘：

| 要素 | 示例 |
|---|---|
| 具体情境 | "当时只有两个人，时间只有两周" |
| 可观察行动 | "我把团队拆成了三个小组" |
| 可验证结果 | "月活从 80 万做到 110 万" |
| 判断标准/价值观 | "我觉得不能只看短期数据" |

**判断公式**：`[主体] 在 [具体情境] 中，做出了 [可观察的行动]，导致 [可验证的结果]`。满足 2 项即触发。

## 4. 方法库

### A. 关键事件锚定（CDM）

> 从用户提到的具体事件切入，重建当时情境、决策与判断。

触发语料示例：
- "我主导了商户分层，月活从 80 万做到 110 万"
- "那次上线前我们临时改了方案"

追问模板：
- "当时最大的压力或意外是什么？"
- "你第一反应注意到了哪个细节？"
- "有没有哪个时刻你意识到老方法行不通？"
- "当时如果让另一个人来做，他最可能忽略什么？"

产出：`Background` + `Task` + `Action` 初稿。

### B. 对比逼近（Repertory Grid）

> 用 A vs B 的选择暴露用户没明说的区分维度。

追问模板：
- "同样是增长项目，A 项目和 B 项目哪个性质更像？和第三个差在哪？"
- "如果当时没做商户分层，而是直接发红包补贴，结果会差在哪？"
- "你说的'更稳'具体是什么意思？能给个反例吗？"

产出：`Key Insight` + `Boundary` 初稿。

### C. Laddering

> 从具体做法一层层爬到价值观/判断标准。

追问模板：
- 属性层："你刚才说'拆成三个小组'，为什么是这个粒度？"
- 后果层："这个粒度对结果有什么影响？"
- 价值层："为什么这件事对你来说重要？"

约束：用户卡住时不再问"为什么"，而是拉回具体事件。

### D. 反事实探测

> 每次只变一个变量，测试用户判断规则的边界。

追问模板：
- "如果时间不是两周而是两个月，你还会选这个方案吗？"
- "如果团队不是 2 个人而是 10 个人，做法会怎么变？"
- "如果当时领导没支持，你打算怎么推进？"

产出：`Boundary` + `Key Insight` 修正。

### E. 隐喻捕捉

> 仅在用户说出"感觉""像""味道""手感""重""轻"等词时激活。

追问模板：
- "你说这个方案'很重'，具体指什么？像什么？"
- "'有网感'对你来说是什么感觉？看到好机会时身体有反应吗？"

产出：用更精确的语言替换隐喻，写入 `Key Insight`。

## 5. 每轮结构与写入硬闸门

```
[提问] → 用户回答 → [可选追问 1-2 次] → [整理成可读 STAR] → 写入待确认区 `[自动]` → 用户确认 `[硬闸门]` → [调用 confirm-evidence 存碎片] → 审计反馈 → 下一轮
```

**整理格式（必须展示给用户看）**：

```
**主题**：商户分层运营，月活 80 万→110 万
- 背景：2024 年 Q2 商户增长停滞，大中商户流失率上升
- 任务：把月活商户从 80 万提升到 100 万
- 行动：按 GMV+活跃度重新分 5 层；对头部商户配 1v1 客户经理；对腰部商户做自动化权益触达
- 结果：3 个月内月活商户从 80 万提升到 110 万，流失率下降 18%
- 关键判断：商户分层不能只看 GMV，活跃度才是预警指标
- 边界条件：头部商户必须人工介入，自动化只适合腰部及以下
```

**用户确认话术**：

> "以上是我整理出来的经历要点。确认写入知识库吗？回复 OK 即保存，或告诉我哪里需要改。"

**纪律**：
- 未获得用户明确回复 OK / 写入 / 保存前，**禁止**调用 `confirm-evidence`。
- 用户确认前，整理稿必须先写入 `原始事实/待确认/`，生成可预览文件，禁止只存在于聊天上下文。
- 用户要求修改时，先修改整理稿并重新 `stage-evidence`（覆盖或生成新预览），再展示确认。
- 用户说「记不清/跳过/不想聊」时，记录为 `fuzzy`，不写入；已生成的预览文件应调用 `reject-evidence` 删除。

## 6. 节奏与纪律

- 每轮只问一个问题，等用户回答。
- 不连续用同一种方法超过 2 轮。
- 默认 5-8 轮一组，不超过 8 轮。
- 用户说"记不清/跳过"时，记录为 `fuzzy`。
- 用户说"不想聊这个"时，立即换方向。
- 用户情绪上来时，顺着情绪走，最容易出真东西。

## 7. 输出格式

碎片文件路径：`kb_path/原始事实/behavioral_evidence/be_{domain}_{序号}.md`

```markdown
---
name: be_work_001
description: 商户分层运营，月活商户 80 万→110 万
type: evidence
domain: work_experience
source: 美团-高级产品经理-2024.06-至今
confidence: confirmed
created: 2026-08-21
---

## 背景（Background）
2024 年 Q2 商户增长停滞，大中商户流失率上升。

## 任务（Task）
把月活商户从 80 万提升到 100 万。

## 行动（Action）
- 把商户按 GMV+活跃度重新分 5 层
- 对头部商户配 1v1 客户经理
- 对腰部商户做自动化权益触达

## 结果（Result）
3 个月内月活商户从 80 万提升到 110 万，流失率下降 18%。

## 关键判断（Key Insight）
商户分层不能只看 GMV，活跃度才是预警指标。

## 边界条件（Boundary）
头部商户必须人工介入，自动化只适合腰部及以下。

## 原话（Verbatim）
> "当时发现只看 GMV 会漏掉一批高活跃但小体量的商户。"
```

索引文件路径：`kb_path/原始事实/behavioral_evidence/map.md`

```markdown
# 行为证据地图

> 自动维护，禁止手动编辑。

## work_experience
- [商户分层运营 80 万→110 万](be_work_001.md) — 美团 [confirmed]

## project_experience
（暂无）

## skill_mastery
（暂无）

## advantage_evidence
（暂无）
```

## 8. 确认式写入命令

### 步骤 1：写入待确认区

深挖结束后，Agent 先把整理稿写入 `原始事实/待确认/`，不要直接写入正式证据库：

```bash
python3 scripts/kb_interview.py stage-evidence \
  --kb <知识库路径> \
  --domain work_experience \
  --source "美团-高级产品经理" \
  --description "商户分层运营，月活 80 万→110 万" \
  --background "2024 年 Q2 商户增长停滞" \
  --task "把月活商户从 80 万提升到 100 万" \
  --action "按 GMV+活跃度重新分 5 层" \
  --action "对头部商户配 1v1 客户经理" \
  --action "对腰部商户做自动化权益触达" \
  --result "3 个月内月活商户从 80 万提升到 110 万，流失率下降 18%" \
  --insight "商户分层不能只看 GMV，活跃度才是预警指标" \
  --boundary "头部商户必须人工介入，自动化只适合腰部及以下" \
  --verbatim "当时发现只看 GMV 会漏掉一批高活跃但小体量的商户。"
```

输出示例：

```
[预览] 已写入待确认区：原始事实/待确认/st_work_experience_001.md
请查看内容后回复 OK 以保存，或告诉我修改意见。
```

Agent 必须读取生成的 `.md` 文件，把内容展示给用户。

### 步骤 2：用户确认后迁移

用户回复 OK 后：

```bash
python3 scripts/kb_interview.py confirm-evidence \
  --kb <知识库路径> \
  --staged-id st_work_experience_001
```

输出示例：

```
[完成] 已写入知识库：原始事实/behavioral_evidence/be_work_experience_001.md
知识库版本：v42
```

### 步骤 3：审计

```bash
python3 scripts/kb_audit.py --kb <知识库路径>
```

输出示例：

```
知识库路径：/Users/.../kb
结构完整：是
  raw_files：5
  behavioral_evidence：3
  staged：0
  claims：2

审计通过
```

### 用户拒绝或修改

- 拒绝：`python3 scripts/kb_interview.py reject-evidence --kb <路径> --staged-id st_work_experience_001`
- 修改：Agent 修改后重新 `stage-evidence`（建议覆盖同一 `staged_id` 或生成新预览），再次展示确认。

### 直接写入（旧命令保留）

如果 Agent 已经在对话中获得了用户明确 OK，也可以一步写入：

```bash
python3 scripts/kb_interview.py save-evidence \
  --kb <知识库路径> \
  --domain work_experience \
  --source "美团-高级产品经理" \
  --description "..." \
  --background "..." --task "..." --action "..." --result "..." \
  --insight "..." --boundary "..." --confidence confirmed --verbatim "..."
```

## 9. 技能熟练度认定

"熟练"不是自评，必须基于 `behavioral_evidence/` 中的 STAR 数量：

| 熟练度 | 完整 STAR 数量 | 场景要求 |
|---|---|---|
| 熟练 | ≥3 个 | 至少 2 个不同场景 |
| 掌握 | 2 个 | 可同一场景 |
| 了解 | 1 个 | 有实际使用经历 |
| 待挖掘 | 0 个 | 不得写入 `skills.md` |

写入 `skills.md` 前，先用 `scripts/mining/skill_validator.py` 校验。

## 10. 下游消费

| 下游 | 消费方式 |
|---|---|
| 简历管线 | 事实挑选时优先关联行为证据碎片 |
| STAR 故事库 | 直接从碎片生成三版本故事 |
| 面试清单 | 针对碎片中的 Key Insight / Boundary 出题 |
| 技能清单 | 熟练度由碎片数量判定 |

## 11. 反模式（禁止）

1. 禁止问抽象问题："你的写作风格是什么？"
2. 禁止连珠炮：一次只问一个问题。
3. 禁止强行提炼：用户说不清就记 fuzzy。
4. 禁止解释方法论：用户不需要知道 CDM 和 Laddering。
5. 禁止一次挖超过 8 轮。
6. 禁止跨域跳跃：一次只挖一个域。
