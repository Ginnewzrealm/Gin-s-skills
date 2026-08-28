# gin-workout-planner 融入 Progress Checklist 优化方案

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `/Users/fubo/Downloads/AI技能进度条设计指南.md` 中的 Progress Checklist 设计模式融入 `gin-workout-planner`（健身助手）技能，解决多场景路由下用户不清楚当前阶段、硬闸门状态不透明的问题。

**架构：** 在 `SKILL.md` 路由器层增加统一 Progress 规则与场景定位句；在每个场景的 `references/*.md` 子文件头部插入该场景的 micro-checklist；使用 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]` 标签标注步骤属性；保持现有输出检查表（训练计划七关、日记八板块）不变，Progress Checklist 只负责**执行阶段可视化**。

**技术栈：** Markdown 技能文档 + YAML frontmatter，无新增脚本，无需依赖。

---

## 涉及文件

| 文件 | 当前职责 | 改动内容 |
|------|---------|---------|
| `gin-workout-planner/SKILL.md` | 路由器、场景路由表、反馈规则 | 新增 `## Progress` 章节；在场景路由表后说明每个场景进入时先输出 micro-checklist；更新反馈规则与版本日志 |
| `gin-workout-planner/references/plan-output.md` | 训练计划生成流程与模板 | 在执行流程前插入 Progress checklist |
| `gin-workout-planner/references/diary-output.md` | 训练日记生成流程与模板 | 在执行流程前插入 Progress checklist |
| `gin-workout-planner/references/action-doc-writing-guide.md` | 动作库更新流程 | 在执行流程前插入 Progress checklist |
| `gin-workout-planner/references/rules.md` | 动作状态与阶段管理规则 | 在状态/阶段变更流程前插入 Progress checklist |
| `gin-workout-planner/references/training-focus.md` | 侧重点/弱项设定流程 | 在设定流程前插入 Progress checklist |
| `gin-workout-planner/references/volume-params.md` | 训练目标/水平参数 | 在目标/水平更改流程前插入 Progress checklist |
| `gin-workout-planner/更新日志/更新日志.md` | 技能变更记录 | 顶部追加本次改动条目 |

---

### 任务 1：在 `SKILL.md` 增加统一 Progress 规则

**文件：**
- 修改：`gin-workout-planner/SKILL.md`

- [ ] **步骤 1：在场景路由表后新增 `## Progress` 章节**

在 `## 场景路由表` 和 `## 用户反馈（必须执行）` 之间插入以下内容：

```markdown
## Progress Checklist 使用规则

本技能包含 7 个场景 + 初始化。每次触发本技能时，先根据用户意图判断场景，然后**立即输出场景定位句 + 本场景 micro-checklist**。

### 场景定位句

进入任意场景时，先说一句：

```markdown
当前场景：健身助手 — [场景中文名]
```

例如：
- 制定训练计划 → `当前场景：健身助手 — 制定训练计划`
- 写训练日记 → `当前场景：健身助手 — 训练日记`
- 添加动作 → `当前场景：健身助手 — 动作库更新`

### micro-checklist 标签

| 标签 | 含义 |
|------|------|
| `[自动]` | AI / 脚本自动读取知识库、生成内容，无需用户实时输入 |
| `[需确认]` | 需要用户查看并确认，但非强制阻塞 |
| `[硬闸门]` | 用户不确认则不能继续下一步 |
| `[可回环]` | 用户可要求回退到前面步骤重做 |

### 展示时机

1. **流程开始时**：输出场景定位句 + 完整 micro-checklist，高亮当前步骤。
2. **进入硬闸门时**：再次展示 checklist，并追加 `当前阻塞：等待你确认 XXXX。`
3. **完成时**：将最后一步标记为 `[✓]`，输出关键结果（改了哪些文件、做了什么）。
4. **会话中断恢复时**：重新输出完整 checklist + 当前阻塞提示。

### 禁止

- 不要跳过硬闸门自动写入训记、更新动作库或写入 `训练侧重点.md`
- 不要在没有输出完整 micro-checklist 的情况下直接开始编排计划/写日记
- 不要在用户说"重来"或"回退"时不重置 checklist 状态
```

- [ ] **步骤 2：更新 `## 用户反馈（必须执行）` 第 2 条**

将原文：

```markdown
- 只在三个时机说：**流程开始、耗时步骤中段、完成时**；单步小事不刷反馈
```

改为：

```markdown
- 在四个时机说：**场景进入（输出 micro-checklist）、流程开始、耗时步骤中段、完成时**；单步小事不刷反馈
- 进入硬闸门时必须说：`当前阻塞：等待你确认 XXXX，你可以回复"确认/OK/继续"，或回复"修改/重来"回退。`
```

- [ ] **步骤 3：commit**

```bash
git add gin-workout-planner/SKILL.md
git commit -m "docs(gin-workout-planner): 增加 Progress Checklist 使用规则

- 新增场景定位句与 micro-checklist 标签说明
- 明确展示时机与禁止项
- 更新用户反馈规则，增加硬闸门阻塞提示"
```

---

### 任务 2：训练计划场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/plan-output.md`

- [ ] **步骤 1：在 `## 执行流程（场景一）` 前插入 Progress checklist**

在 `## 执行流程（场景一）` 标题后、流程编号 `1.` 之前插入：

```markdown
### 场景进度

当前场景：健身助手 — 制定训练计划

Progress:
- [ ] Step 1 确认训练部位与目标 [硬闸门] [可回环]  ← 当前
- [ ] Step 2 读取动作索引并筛选激活动作 [自动]
- [ ] Step 3 匹配热身动作与读取历史数据 [自动]
- [ ] Step 4 近期冲突检测与声明 [自动]
- [ ] Step 5 确认训练目标/水平/阶段/侧重点 [硬闸门] [可回环]
- [ ] Step 6 确认是否使用高级训练技术 [需确认] [可回环]
- [ ] Step 7 按规则编排动作与排序 [自动]
- [ ] Step 8 定组数/次数/负荷/休息 [自动]
- [ ] Step 9 生成并输出检查表 + 计划正文 [自动]
- [ ] Step 10 用户确认计划 [硬闸门] [可回环]
- [ ] Step 11（可选）写入训记 [硬闸门]

禁止：
- 不要跳过用户确认直接写入训记
- 不要在动作库激活动作不足时编造动作
- 不要在近期冲突未声明的情况下发送计划
```

- [ ] **步骤 2：在流程第 5 步后增加硬闸门提示**

在原文第 5 步末尾（`本段确认缺失 = 检查表 ⓪ 流程关 NO-GO，禁止发送计划`）后追加：

```markdown
   **本步骤为硬闸门。若用户未确认目标/阶段/侧重点，输出：**
   `当前阻塞：等待你确认训练目标、水平和侧重点。你可以回复"确认/继续"，或回复"修改"回退到 Step 1。`
```

- [ ] **步骤 3：在流程第 6 步后增加可回环提示**

在原文第 6 步末尾（`用户看过不满意或拒绝 → 回退标准组，不追问不劝说`）后追加：

```markdown
   **本步骤为可回环。用户说"不用高级技术"或"回退标准组" → 将 Step 6 标记为 [✓]，高亮 Step 7，按标准组继续。**
```

- [ ] **步骤 4：commit**

```bash
git add gin-workout-planner/references/plan-output.md
git commit -m "docs(plan-output): 训练计划场景增加 Progress Checklist

- 插入 11 步 micro-checklist
- 标注硬闸门与可回环步骤
- 增加目标确认和高级技术选择的阻塞/回环提示"
```

---

### 任务 3：训练日记场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/diary-output.md`

- [ ] **步骤 1：在 `## 执行流程（场景二）` 前插入 Progress checklist**

在 `## 执行流程（场景二）` 标题后、流程编号 `1.` 之前插入：

```markdown
### 场景进度

当前场景：健身助手 — 训练日记

Progress:
- [ ] Step 1 获取训记训练数据 [自动]
- [ ] Step 2 获取训记饮食数据 [自动]
- [ ] Step 3 解析训练记录并核对格式 [自动]
- [ ] Step 4 读取最近同部位日记用于对比 [自动]
- [ ] Step 5 生成训练日记八个板块 [自动]  ← 当前
- [ ] Step 6 展示日记给用户确认 [需确认]
- [ ] Step 7 保存日记文件 [硬闸门]
- [ ] Step 8 执行数据回流并输出回执 [硬闸门]

禁止：
- 不要在日记八板块不齐全时发送
- 不要跳过数据回流直接结束
- 训记饮食数据获取失败不阻塞训练日记主体
```

- [ ] **步骤 2：在流程第 6 步（展示日记）位置增加确认提示**

在流程编号 `5.` 和 `6.` 之间插入：

```markdown
5b. 【需确认】将生成的日记完整版展示给用户。用户说"保存/OK/确认"后进入 Step 7；
    用户说"修改/重来" → 回环到 Step 5 重新生成。
```

- [ ] **步骤 3：commit**

```bash
git add gin-workout-planner/references/diary-output.md
git commit -m "docs(diary-output): 训练日记场景增加 Progress Checklist

- 插入 8 步 micro-checklist
- 标注数据获取为自动、保存与回流为硬闸门
- 增加日记展示确认步骤"
```

---

### 任务 4：动作库更新场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/action-doc-writing-guide.md`

- [ ] **步骤 1：读取该文件开头，确认插入位置**

- [ ] **步骤 2：在文件执行流程开始前插入 Progress checklist**

在文件的第一个 `## ` 标题后插入：

```markdown
## 场景进度

当前场景：健身助手 — 动作库更新

Progress:
- [ ] Step 1 接收动作教程/文字来源 [自动]
- [ ] Step 2 解析动作信息（名称/器械/目标肌肉/动作过程） [自动]
- [ ] Step 3 同名判定：是否已存在同名动作 [自动]
- [ ] Step 4 按模板撰写动作文档 [自动]
- [ ] Step 5 采集发力感知提示 [自动]
- [ ] Step 6 展示新动作文档给用户确认 [需确认]  ← 当前
- [ ] Step 7 写入动作库并更新索引 [硬闸门]

禁止：
- 不要跳过用户确认直接写入动作库
- 不要在没有同名判定的情况下覆盖已有动作
```

- [ ] **步骤 3：commit**

```bash
git add gin-workout-planner/references/action-doc-writing-guide.md
git commit -m "docs(action-doc): 动作库更新场景增加 Progress Checklist

- 插入 7 步 micro-checklist
- 标注写入动作库为硬闸门"
```

---

### 任务 5：动作状态与阶段管理场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/rules.md`

- [ ] **步骤 1：找到 `rules.md` 中关于动作状态/阶段管理的章节**

通常是第 6 节。在该章节开头插入：

```markdown
### 场景进度

当前场景：健身助手 — 动作状态与阶段管理

Progress:
- [ ] Step 1 读取动作索引和目标动作文档 [自动]
- [ ] Step 2 确认变更类型（冷冻/激活/阶段切换/换健身房） [自动]
- [ ] Step 3 执行规则校验（如学习期→渐进期条件） [自动]
- [ ] Step 4 展示变更影响给用户确认 [需确认]  ← 当前
- [ ] Step 5 更新索引/文档 frontmatter [硬闸门]

禁止：
- 不要未确认就修改动作索引
- 不要跳过阶段切换条件检查
```

- [ ] **步骤 2：commit**

```bash
git add gin-workout-planner/references/rules.md
git commit -m "docs(rules): 动作状态管理场景增加 Progress Checklist

- 插入 5 步 micro-checklist
- 标注更新索引为硬闸门"
```

---

### 任务 6：侧重点/弱项设定场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/training-focus.md`

- [ ] **步骤 1：在该文件执行流程/写入逻辑前插入 Progress checklist**

在第一个 `## ` 标题后插入：

```markdown
## 场景进度

当前场景：健身助手 — 侧重点/弱项设定

Progress:
- [ ] Step 1 读取当前 `训练侧重点.md` [自动]
- [ ] Step 2 解析用户新意图（加强/维持/避开/多做/少做） [自动]
- [ ] Step 3 生成更新后的侧重点文本 [自动]
- [ ] Step 4 展示变更给用户确认 [需确认]  ← 当前
- [ ] Step 5 写入 `训练侧重点.md` [硬闸门]

禁止：
- 不要只在对话里记住不落盘
- 不要未确认就覆盖 `训练侧重点.md`
```

- [ ] **步骤 2：commit**

```bash
git add gin-workout-planner/references/training-focus.md
git commit -m "docs(training-focus): 侧重点设定场景增加 Progress Checklist

- 插入 5 步 micro-checklist
- 标注写入训练侧重点.md 为硬闸门"
```

---

### 任务 7：目标/水平更改场景增加 micro-checklist

**文件：**
- 修改：`gin-workout-planner/references/volume-params.md`

- [ ] **步骤 1：找到目标/水平更改相关流程**

在 `volume-params.md` 开头或 `training_goal` / `training_level` 相关章节前插入：

```markdown
## 场景进度

当前场景：健身助手 — 目标/水平更改

Progress:
- [ ] Step 1 读取当前 `_skill-config.json` 的 training_goal / training_level [自动]
- [ ] Step 2 确认用户新目标/水平 [硬闸门] [可回环]  ← 当前
- [ ] Step 3 更新 `_skill-config.json` [硬闸门]

禁止：
- 不要未确认就修改训练目标/水平
- 目标/水平变更后未生效前不继续生成计划
```

- [ ] **步骤 2：commit**

```bash
git add gin-workout-planner/references/volume-params.md
git commit -m "docs(volume-params): 目标/水平更改场景增加 Progress Checklist

- 插入 3 步 micro-checklist
- 标注确认与写入为硬闸门"
```

---

### 任务 8：初始化场景补充说明

**文件：**
- 修改：`gin-workout-planner/SKILL.md`

- [ ] **步骤 1：在 `## 场景路由表` 的初始化行后追加 micro-checklist 提示**

在路由表中对应"初始化健身知识库"的行后面，增加一列或备注：

```markdown
| "初始化健身知识库" / 首次使用 | 初始化 | `references/kb-structure.md`；Progress: 确认路径 [硬闸门] → 创建目录 [自动] → 创建配置文件 [硬闸门] → 完成 |
```

- [ ] **步骤 2：commit**

```bash
git add gin-workout-planner/SKILL.md
git commit -m "docs(skill): 初始化场景补充 Progress Checklist 提示

- 在路由表中标注初始化场景的进度步骤"
```

---

### 任务 9：更新日志

**文件：**
- 修改：`gin-workout-planner/更新日志/更新日志.md`

- [ ] **步骤 1：在文件顶部追加新条目**

```markdown
## 2026-08-28

**v1.25.1**
- feat: 全技能融入 Progress Checklist 设计模式
  - SKILL.md 新增统一 Progress 规则、场景定位句、标签说明与禁止项
  - 训练计划/训练日记/动作库更新/动作状态管理/侧重点设定/目标水平更改 6 个场景增加 micro-checklist
  - 明确标注硬闸门（用户确认后方可写入训记/动作库/侧重点/配置）与可回环步骤
  - 更新用户反馈规则，增加硬闸门阻塞提示话术
```

- [ ] **步骤 2：commit**

```bash
git add "gin-workout-planner/更新日志/更新日志.md"
git commit -m "chore(gin-workout-planner): 更新日志记录 Progress Checklist 优化

- 新增 v1.25.1 变更条目
- 记录 6 个场景 micro-checklist 与硬闸门标注"
```

---

### 任务 10：验证文档一致性与渲染

**文件：**
- 涉及：`gin-workout-planner/SKILL.md`、`gin-workout-planner/references/*.md`

- [ ] **步骤 1：全局搜索 Progress 相关关键词，确保命名一致**

```bash
cd gin-workout-planner
grep -R "Progress:" .
grep -R "当前场景：健身助手" .
```

- [ ] **步骤 2：检查每个 micro-checklist 是否包含标签**

确认 6 个场景的 checklist 中每个步骤都至少有一个 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]` 标签。

- [ ] **步骤 3：检查硬闸门后是否有阻塞提示**

确认训练计划、训练日记、动作库更新、侧重点设定、目标/水平更改这 5 个硬闸门位置都有类似 `当前阻塞：等待你确认 XXXX` 的提示。

- [ ] **步骤 4：commit**

```bash
git add -A
git commit -m "chore(gin-workout-planner): Progress Checklist 一致性检查

- 确认所有场景 micro-checklist 命名统一
- 确认硬闸门步骤均有阻塞提示
- 确认标签使用规范"
```

---

## 自检

**1. 规格覆盖度：**
- ✅ SKILL.md 统一 Progress 规则
- ✅ 6 个主要场景 micro-checklist
- ✅ 硬闸门 / 可回环标签
- ✅ 阻塞提示话术
- ✅ 更新日志
- ✅ 一致性检查

**2. 占位符扫描：**
- 无 "TODO"、"待定"、"后续实现"
- 每个步骤都有具体插入位置和文案

**3. 类型一致性：**
- 统一使用 "当前场景：健身助手 — [场景名]"
- 统一使用 `Progress:` 标题
- 统一使用 `- [ ] Step N 动作 [标签]` 格式

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-08-28-gin-workout-planner-progress-checklist.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
