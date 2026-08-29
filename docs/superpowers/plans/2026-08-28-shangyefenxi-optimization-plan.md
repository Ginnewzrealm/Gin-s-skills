# shangyefenxi 融入 Progress Checklist + hv-analysis 桥接规范优化方案

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `/Users/fubo/Downloads/AI技能进度条设计指南.md` 中的 Progress Checklist 设计模式融入 `shangyefenxi_skill`，同时修正 SKILL.md 中横纵分析依赖技能名称（`商机知识库管理` → `hv-analysis`），并新增符合 `/Users/fubo/Downloads/技能桥接模式技术规范.md` v2.0 的桥接约定文件。

**架构：** 在 `SKILL.md` 路由器层增加统一 Progress 规则与场景定位句；在报告模式和咨询问答模式入口插入 micro-checklist；用 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]` 标签标注步骤属性；把现有 `G1/G2/G3` 阶段闸门产物核验整合进 checklist；新增 `references/hv-analysis-bridge.md` 描述与 `hv-analysis` 技能的调用契约。

**技术栈：** Markdown 技能文档 + YAML frontmatter，无新增脚本，无需依赖。

---

## 涉及文件

| 文件 | 当前职责 | 改动内容 |
|------|---------|---------|
| `shangyefenxi_skill/SKILL.md` | 路由器、两种模式 SOP、证据纪律、进度播报规则 | 新增 `## Progress Checklist 使用规则`；修正所有「商机知识库管理」为 `hv-analysis`；报告模式 SOP 改写成 micro-checklist；咨询问答模式增加 micro-checklist；更新进度播报规则与版本日志 |
| `shangyefenxi_skill/references/broadcast_spec.md` | 节点播报话术示例 | 将节点播报与 checklist 步骤对齐，补充硬闸门/可回环场景话术 |
| `shangyefenxi_skill/references/hv-analysis-bridge.md` | 不存在 | 新建桥接约定文件，遵循技能桥接规范 v2.0 五章格式 |
| `shangyefenxi_skill/CHANGELOG.md` | 技能变更记录 | 顶部追加 v1.14.0 优化条目 |

---

### 任务 1：在 `SKILL.md` 增加统一 Progress 规则

**文件：**
- 修改：`shangyefenxi_skill/SKILL.md`

- [ ] **步骤 1：在「两种工作模式」之后新增 `## Progress Checklist 使用规则` 章节**

在 `## 两种工作模式` 和 `## 路径确认（每次触发必做）` 之间插入以下内容：

```markdown
## Progress Checklist 使用规则

本技能含 2 种工作模式：报告模式、咨询问答模式。每次触发本技能时，先判断用户意图属于哪个模式，然后**立即输出场景定位句 + 本模式 micro-checklist**。

### 场景定位句

进入任意模式时，先说一句：

```markdown
当前场景：shangyefenxi — [报告模式 / 咨询问答模式]
```

例如：
- 出完整报告 → `当前场景：shangyefenxi — 报告模式`
- 问答讨论 → `当前场景：shangyefenxi — 咨询问答模式`

### micro-checklist 标签

| 标签 | 含义 |
|------|------|
| `[自动]` | AI / 脚本自动读取资料、搜索、生成，无需用户实时输入 |
| `[需确认]` | 需要用户查看并确认，但非强制阻塞 |
| `[硬闸门]` | 用户不确认则不能继续下一步 |
| `[可回环]` | 用户可要求回退到前面步骤重做 |

### 展示时机

1. **流程开始时**：输出场景定位句 + 完整 micro-checklist，高亮当前步骤。
2. **进入硬闸门时**：再次展示 checklist，并追加 `当前阻塞：等待你确认 XXXX。`
3. **完成时**：将最后一步标记为 `[✓]`，输出关键结果（交付清单、未验证项数）。
4. **会话中断恢复时**：读取 `{商机}/跟踪/运行日志.md` 后，重新输出完整 checklist + 当前阻塞提示。

### 禁止

- 不要跳过正向复述/反向确认硬闸门
- 不要在没有横纵分析报告时进入分析
- 不要在用户说"重来"或"回退"时不重置 checklist 状态
- 不要代填飞书表格的「最终决策」字段
```

- [ ] **步骤 2：commit**

```bash
git add shangyefenxi_skill/SKILL.md
git commit -m "docs(shangyefenxi): 增加 Progress Checklist 使用规则

- 新增场景定位句与 micro-checklist 标签说明
- 明确展示时机与禁止项
- 为报告模式和咨询问答模式统一进度可视化"
```

---

### 任务 2：修正横纵分析依赖技能名称为 `hv-analysis`

**文件：**
- 修改：`shangyefenxi_skill/SKILL.md`

- [ ] **步骤 1：全局替换「商机知识库管理」为 `hv-analysis（横纵分析法深度研究）`**

需要修改的位置：

1. 第 6 行 description 中的硬前提说明：

```markdown
硬前提：目标商机的 分析/ 文件夹中须有横纵分析报告；缺失时拒绝执行，并建议用户先用「hv-analysis（横纵分析法深度研究）」技能完成横纵分析。
```

2. 前置硬门槛拒绝通知：

```markdown
  > ⚠️ 这个商机的「分析」文件夹里还没有横纵分析报告。商业可行性分析需要事实基础，没有它，后面的分析就是凭空编。
  > 👉 建议先用「hv-analysis（横纵分析法深度研究）」技能完成横纵分析，把报告放进 `{编号}_{商机名称}/分析/` 之后，再回来找我。
```

3. 目录结构约定中采集规则段落（已有「横纵分析报告」描述，无需改动术语，只需确保上下文一致）。

4. 「绝对不要做的事」第 12 条：

```markdown
- 不要在没有横纵分析报告时硬做分析——前置硬门槛，拒绝执行并引导用户先用「hv-analysis（横纵分析法深度研究）」技能完成横纵分析。
```

- [ ] **步骤 2：commit**

```bash
git add shangyefenxi_skill/SKILL.md
git commit -m "docs(shangyefenxi): 修正横纵分析依赖技能名称为 hv-analysis

- 将「商机知识库管理」统一改为「hv-analysis（横纵分析法深度研究）」
- 同步更新 description、硬门槛提示、绝对禁止项"
```

---

### 任务 3：报告模式 SOP 改写成 micro-checklist

**文件：**
- 修改：`shangyefenxi_skill/SKILL.md`

- [ ] **步骤 1：在 `## 报告模式 SOP` 标题后插入 macro checklist**

在 `## 报告模式 SOP` 标题之后、「### 阶段闸门（防跳跃，硬规则）」之前插入：

```markdown
### 场景进度

当前场景：shangyefenxi — 报告模式

Progress:
- [ ] Step 1 路径确认与配置读取 [自动]
- [ ] Step 2 横纵分析报告硬门槛检查 [硬闸门]
- [ ] Step 3 资料采集与 5 问归一 [自动]
- [ ] Step 4 正向复述确认 [硬闸门] [可回环]  ← 当前
- [ ] Step 5 反向确认 [硬闸门] [可回环]
- [ ] Step 6 外部研究与行为观察（3+1 轮搜索） [自动]
- [ ] Step 7 来源检查与关键事实卡片 [自动]
- [ ] Step 8 商业分析管线（三要素/画像/套路/壁垒） [自动]
- [ ] Step 9 报告写前必读模板 [自动]
- [ ] Step 10 报告撰写与交叉一致性校验 [自动]
- [ ] Step 11 格式校验 [自动]
- [ ] Step 12 飞书双轨写入 [需确认] [硬闸门]
- [ ] Step 13 汇报交付 [自动]

禁止：
- 不要跳过正向复述/反向确认硬闸门
- 不要在没有横纵分析报告时进入分析
- 不要代填飞书表格的「最终决策」字段
- 不要粘贴报告全文到聊天窗口
```

- [ ] **步骤 2：在阶段一「正向复述」步骤后增加硬闸门阻塞提示**

在阶段一第 4 步末尾（`必须等用户确认后才能继续。`）后追加：

```markdown
   **本步骤为硬闸门。若用户未确认，输出：**
   `当前阻塞：等待你确认我对项目的理解是否正确。你可以回复「确认/继续」，或回复「修改/重来」回退到 Step 3。`
```

- [ ] **步骤 3：在阶段一「反向确认」步骤后增加硬闸门阻塞提示**

在第 5 步末尾（`澄清最多 2 轮...`）后追加：

```markdown
   **本步骤为硬闸门。若用户未确认，输出：**
   `当前阻塞：等待你确认项目边界。你可以回复「确认/继续」，或回复「修改/重来」回退到 Step 4。`
```

- [ ] **步骤 4：在阶段四「飞书双轨写入」步骤后增加硬闸门提示**

在阶段四第 5 步末尾（`失败降级手动粘贴不卡死。`）后追加：

```markdown
   **本步骤涉及写入飞书和表格。执行写入前输出：**
   `当前阻塞：等待你确认写入飞书。你可以回复「确认/继续」，或回复「修改/重来」回退到 Step 10。`
```

- [ ] **步骤 5：commit**

```bash
git add shangyefenxi_skill/SKILL.md
git commit -m "docs(shangyefenxi): 报告模式 SOP 改写成 micro-checklist

- 插入 13 步 macro checklist
- 标注硬闸门与可回环步骤
- 在正向复述、反向确认、飞书写入处增加阻塞提示"
```

---

### 任务 4：咨询问答模式增加 micro-checklist

**文件：**
- 修改：`shangyefenxi_skill/SKILL.md`

- [ ] **步骤 1：在 `## 咨询问答模式` 标题后插入 micro-checklist**

在 `## 咨询问答模式` 标题之后、「### 流程` 之前插入：

```markdown
### 场景进度

当前场景：shangyefenxi — 咨询问答模式

Progress:
- [ ] Step 1 路径确认 [自动]
- [ ] Step 2 横纵分析报告硬门槛检查 [硬闸门]
- [ ] Step 3 读取跟踪档案 + 可行性报告 + 横纵报告 [自动]
- [ ] Step 4 对话式分析 [需确认]  ← 当前
- [ ] Step 5 更新跟踪档案 [硬闸门]
- [ ] Step 6（可选）决策回填飞书表格 [硬闸门]

禁止：
- 不要在没有横纵分析报告时进行问答分析
- 不要把推测写成事实
- 不要代填飞书表格的「最终决策」字段
```

- [ ] **步骤 2：在咨询问答流程「决策回填」步骤增加硬闸门提示**

在流程第 7 步末尾（`技能绝不代填。`）后追加：

```markdown
   **本步骤为硬闸门。只有在用户本人明确说出最终决策或 MVP 验证结果时才执行回填；回填前输出：**
   `当前阻塞：等待你确认回填内容。你将「XXXX」写入飞书表格字段 9/12/14，确认吗？`
```

- [ ] **步骤 3：commit**

```bash
git add shangyefenxi_skill/SKILL.md
git commit -m "docs(shangyefenxi): 咨询问答模式增加 Progress Checklist

- 插入 6 步 micro-checklist
- 标注读取资料为自动、更新档案与决策回填为硬闸门
- 增加决策回填阻塞提示"
```

---

### 任务 5：新增 `references/hv-analysis-bridge.md`

**文件：**
- 创建：`shangyefenxi_skill/references/hv-analysis-bridge.md`

- [ ] **步骤 1：创建桥接约定文件**

文件内容：

```markdown
# hv-analysis（横纵分析法深度研究）调用约定（桥接，不直连接口）

> 何时读我：进入报告模式或咨询问答模式前，检查横纵分析报告时；初始化做依赖检测时，必须先读本文件。
> 前提：用户环境中已安装「hv-analysis」技能。未安装则拒绝执行并引导安装，不要尝试替代其完成横纵研究。

## 一、职责边界（禁止越界）

- **hv-analysis 技能负责**：
  - 联网收集研究对象的纵向（发展历程）与横向（竞品对比）信息
  - 按横纵分析法产出 Markdown 格式的深度研究报告
  - 将报告保存到用户指定的路径
- **本技能（shangyefenxi）负责**：
  - 检测 `{编号}_{商机名称}/分析/` 目录下是否存在文件名含「横纵」的研究报告
  - 读取报告内容作为商业可行性分析的事实基础
  - 输出商业可行性分析报告，不代劳横纵研究本身
- **本技能明确不执行**：
  - 不直接替用户发起横纵研究
  - 不修改 hv-analysis 技能产出的报告原文
  - 不在报告缺失时编造事实或绕过门槛

## 二、依赖检测

进入本技能任何模式前，执行以下检测：

1. 定位本次商机文件夹 `{编号}_{商机名称}/`
2. 检查 `{编号}_{商机名称}/分析/` 目录是否存在文件名含「横纵」的 Markdown 文件
3. **存在** → 门槛通过，继续执行
4. **不存在** → 拒绝执行，向用户发送硬门槛通知并建议调用 `hv-analysis` 技能完成横纵分析

hv-analysis 技能是否已安装由用户环境决定；本技能不检测其安装状态，只检测产物是否存在。

## 三、输入参数

本技能从文件系统读取，不直接向 hv-analysis 技能传参。

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| 商机编号 | string | 是 | 两位数字，如 `01` |
| 商机名称 | string | 是 | 商机简称，用于文件夹命名 |
| 分析目录 | string | 是 | `{root}/{编号}_{商机名称}/分析/` |

## 四、输出结果

| 字段名 | 类型 | 存在条件 | 说明 |
|--------|------|----------|------|
| 横纵分析报告路径 | string | 检测通过时 | 本地 Markdown 文件绝对路径 |
| 横纵分析报告内容 | string | 检测通过时 | 已读取的报告正文 |
| 缺失原因 | string | 检测不通过时 | 告知用户缺少横纵分析报告 |

## 五、异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| 横纵分析报告缺失 | **拒绝执行**，发送硬门槛通知：`「分析」文件夹里还没有横纵分析报告。建议先用 hv-analysis 技能完成横纵分析，把报告放进 {编号}_{商机名称}/分析/ 后再回来。` |
| 报告文件存在但读取失败 | 提示用户检查文件权限或格式，不编造事实 |
| 用户要求补充横纵研究 | 引导用户使用 hv-analysis 技能，本技能不代劳 |
| 报告中关键事实缺失 | 标「❓ 待验证」继续，不得写成事实 |
```

- [ ] **步骤 2：在 `SKILL.md` 规范文件表中登记新文件**

在 `SKILL.md` 的「规范文件（`references/`）」表格中新增一行：

```markdown
| 检测/读取横纵分析报告 | `references/hv-analysis-bridge.md` |
```

- [ ] **步骤 3：commit**

```bash
git add shangyefenxi_skill/SKILL.md shangyefenxi_skill/references/hv-analysis-bridge.md
git commit -m "docs(shangyefenxi): 新增 hv-analysis 桥接约定

- 按技能桥接模式技术规范 v2.0 五章格式创建 references/hv-analysis-bridge.md
- 明确 hv-analysis 负责产出横纵报告，本技能负责检测和读取
- 在 SKILL.md 规范文件表中登记桥接文件"
```

---

### 任务 6：更新 `references/broadcast_spec.md` 与 checklist 对齐

**文件：**
- 修改：`shangyefenxi_skill/references/broadcast_spec.md`

- [ ] **步骤 1：在报告模式节点表中补充硬闸门/可回环场景播报**

在「关键节点播报（报告模式）」表格中追加以下行：

```markdown
| 进入硬闸门 | `🚧 当前阻塞：等待你确认 XXXX。你可以回复「确认/继续」，或回复「修改/重来」回退。` |
| 正向复述等待确认 | `📝 我对项目的理解是这样：{复述摘要}。确认无误请回复「继续」，需要修改请直接说。` |
| 反向确认等待确认 | `🧭 我判定不属于本项目范畴的是：{边界清单}。有遗漏或不对请纠正。` |
| 用户要求回退 | `↩️ 收到，回退到 Step N，我们重新来。` |
| 完成交付 | `🎉 全部完成，本次运行已结束！交付：本地报告 {路径}｜飞书文档 {链接}｜飞书表格已更新。另有 N 项待验证。` |
```

- [ ] **步骤 2：在咨询问答模式节点中补充关键节点**

在「关键节点播报（咨询问答模式）」下追加：

```markdown
- 进入问答：`💬 已进入咨询问答模式，我会基于跟踪档案、可行性报告和横纵分析来回答。`
- 空转词识别：`⚠️ 「XXXX」在这句话里是空转词——你具体想获得什么？`
- 决策回填确认：`🚧 当前阻塞：等待你确认把「XXXX」写入飞书表格字段 9/12/14。确认吗？`
```

- [ ] **步骤 3：commit**

```bash
git add shangyefenxi_skill/references/broadcast_spec.md
git commit -m "docs(broadcast): 播报话术与 Progress Checklist 对齐

- 补充硬闸门、正向复述、反向确认、回退、完成交付话术
- 补充咨询问答模式的空转词识别与决策回填确认话术"
```

---

### 任务 7：更新 `CHANGELOG.md`

**文件：**
- 修改：`shangyefenxi_skill/CHANGELOG.md`

- [ ] **步骤 1：在文件顶部追加新条目**

```markdown
## v1.14.0 ｜ 2026-08-28

**Progress Checklist 统一化 + hv-analysis 桥接规范**

- ✨ **新增 Progress Checklist 使用规则**：统一场景定位句、标签说明、展示时机与禁止项
- ✨ **报告模式 13 步 micro-checklist**：覆盖路径确认→横纵门槛→资料采集→双向确认→外部研究→分析管线→报告撰写→飞书写入→汇报交付
- ✨ **咨询问答模式 6 步 micro-checklist**：覆盖路径确认→横纵门槛→读取三类依据→对话分析→更新档案→决策回填
- 🔧 **现有阶段闸门 G1/G2/G3 与 checklist 整合**：产物核验作为过闸门前必须完成的检查项
- 🔧 **修正横纵分析依赖技能名称**：SKILL.md 中「商机知识库管理」统一改为「hv-analysis（横纵分析法深度研究）」
- ✨ **新增 `references/hv-analysis-bridge.md`**：按技能桥接模式技术规范 v2.0 五章格式，明确 hv-analysis 产出报告、本技能检测读取的职责边界
- 🔧 **`references/broadcast_spec.md` 与 checklist 对齐**：补充硬闸门、回退、完成交付、决策回填等场景播报话术
```

- [ ] **步骤 2：commit**

```bash
git add shangyefenxi_skill/CHANGELOG.md
git commit -m "chore(shangyefenxi): 更新日志记录 v1.14.0 优化

- 新增 Progress Checklist 与 hv-analysis 桥接规范条目
- 记录报告模式/咨询问答模式 micro-checklist"
```

---

### 任务 8：验证文档一致性与渲染

**文件：**
- 涉及：`shangyefenxi_skill/SKILL.md`、`shangyefenxi_skill/references/*.md`、`shangyefenxi_skill/CHANGELOG.md`

- [ ] **步骤 1：全局搜索旧术语和旧场景定位句**

```bash
cd shangyefenxi_skill
grep -R "商机知识库管理" .
grep -R "当前场景：shangyefenxi" SKILL.md references/
grep -R "jianshen-zhushou" . || true
grep -R "^Progress:" SKILL.md references/
```

- [ ] **步骤 2：检查每个 micro-checklist 是否包含标签**

确认报告模式和咨询问答模式的 checklist 中每个步骤都至少有一个 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]` 标签。

- [ ] **步骤 3：检查硬闸门后是否有阻塞提示**

确认正向复述、反向确认、飞书写入、决策回填这 4 个硬闸门位置都有类似 `当前阻塞：等待你确认 XXXX` 的提示。

- [ ] **步骤 4：验证 `hv-analysis-bridge.md` 五章齐全**

```bash
grep -E "^## [一二三四五]、" shangyefenxi_skill/references/hv-analysis-bridge.md
```

预期输出包含：一、职责边界 / 二、依赖检测 / 三、输入参数 / 四、输出结果 / 五、异常处理

- [ ] **步骤 5：commit**

```bash
git add -A
git commit -m "chore(shangyefenxi): Progress Checklist 一致性检查

- 确认「商机知识库管理」已清零
- 确认所有场景定位句统一为 shangyefenxi
- 确认硬闸门均有阻塞提示
- 确认 hv-analysis-bridge.md 五章齐全"
```

---

## 自检

**1. 规格覆盖度：**
- ✅ SKILL.md 统一 Progress 规则
- ✅ 报告模式 13 步 micro-checklist
- ✅ 咨询问答模式 6 步 micro-checklist
- ✅ 硬闸门 / 可回环标签
- ✅ 阻塞提示话术
- ✅ hv-analysis 桥接文件（五章格式）
- ✅ SKILL.md 中「商机知识库管理」清零
- ✅ broadcast_spec.md 对齐
- ✅ CHANGELOG 更新
- ✅ 一致性检查

**2. 占位符扫描：**
- 无 "TODO"、"待定"、"后续实现"
- 每个步骤都有具体插入位置和文案

**3. 类型一致性：**
- 统一使用 "当前场景：shangyefenxi — [模式名]"
- 统一使用 `Progress:` 标题
- 统一使用 `- [ ] Step N 动作 [标签]` 格式
- 桥接文件统一使用规范五章格式

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-08-28-shangyefenxi-optimization-plan.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
