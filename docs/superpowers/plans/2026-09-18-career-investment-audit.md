# career-investment-audit 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 Gin-s-skills 仓库新增一个职业机会投资审计 Skill，把岗位投入、预期回报、成就点、证据缺口和面试验证问题串成可回填的两阶段流程。

**架构：** 新 Skill 负责职业机会的初审与复审；现有 `achievement-point-coach` 继续负责成就点的事前澄清和事后核验，新 Skill 只复用其判定维度，不复制其内容。Skill 通过事实/推测/待验证信息分层，先生成问题，再依据面试答案更新结论。

**技术栈：** Markdown Skill 文档、JSON 评测用例、Python 结构检查脚本（仅用于测试，不引入运行时依赖）。

---

### 任务 1：编写失败的结构测试与评测用例

**文件：**
- 创建：`career-investment-audit/tests/test_skill_structure.py`
- 创建：`career-investment-audit/evals/evals.json`

- [x] **步骤 1：编写失败的结构测试**

测试必须检查：YAML frontmatter 含 `name` 和 `description`；正文包含两阶段流程、事实/推测区分、面试问题生成、成就点证据维度、固定报告字段；正文少于 500 行。

- [x] **步骤 2：运行测试验证失败**

运行：`python3 -m pytest career-investment-audit/tests/test_skill_structure.py -q`

预期：因 `career-investment-audit/SKILL.md` 尚不存在而失败。

- [x] **步骤 3：编写 4 个评测提示**

覆盖：信息不足的岗位初审；高薪但成就点不可携带的岗位；补充面试答案后的复审。每个用例都写明预期行为，但不写模型答案断言。

### 任务 2：实现核心 Skill

**文件：**
- 创建：`career-investment-audit/SKILL.md`

- [x] **步骤 1：写入 frontmatter 和触发条件**

技能名使用 `career-investment-audit`，描述覆盖岗位、JD、Offer、面试记录、职业选择、投入产出、成就点和验证问题等触发词。

- [x] **步骤 2：实现初审流程**

定义最小输入、可选输入和用户目标；将信息分为已知事实、用户解释、AI 推测和待验证项；评估时间/精力/机会成本以及现金流、能力、作品、认知、品牌、人脉和风险。

- [x] **步骤 3：实现面试问题生成**

按“决策影响 × 当前不确定性”排序生成问题，每轮最多 5 个高价值问题，并说明每个问题会验证哪个变量。涵盖工作强度、权限、绩效、成果归属、证据可携带性、团队稳定性和合同风险。

- [x] **步骤 4：实现复审与成就点判定**

收到面试答案或新证据后更新事实，不覆盖旧判断；把回报标记为机会、承诺、形成或兑现；按可核验性、可分离性、可复用性、可兑现性和个人贡献确定度评估成就点。

- [x] **步骤 5：定义固定输出模板和边界**

输出初审报告或复审报告，包含结论、投入、回报、成就点、证据缺口、风险、置信度和下一步。禁止把推测写成事实、把分数当客观真理或把移民/法律/财税结论硬编码。

### 任务 3：接入仓库目录与验证

**文件：**
- 修改：`README.md`
- 修改：`career-investment-audit/tests/test_skill_structure.py`

- [x] **步骤 1：在 README Skill 清单中加入新 Skill**

说明其职责为“职业机会投入—产出审计：面试前识别信息缺口，面试后评估现金回报、成就点、可携带资产和风险”。

- [x] **步骤 2：运行结构测试与 YAML/Markdown 检查**

运行：`python3 -m pytest career-investment-audit/tests/test_skill_structure.py -q`

预期：全部结构断言通过。

- [x] **步骤 3：运行仓库现有测试**

运行：`bash run_all_tests.sh`

预期：现有技能测试无新增失败；若仓库已有失败，记录原始失败目录，不修改无关文件。

### 任务 4：审查、提交并推送

**文件：**
- 检查：`career-investment-audit/SKILL.md`
- 检查：`career-investment-audit/evals/evals.json`
- 检查：`README.md`

- [x] **步骤 1：执行规格审查**

核对设计中的两阶段流程、面试提问、成就点证据分层和不确定性表达是否逐项落地。

- [x] **步骤 2：执行代码/文档质量审查**

检查 frontmatter、触发描述、篇幅、引用路径、无关范围和未验证承诺。

- [ ] **步骤 3：提交变更**

运行：`git add career-investment-audit README.md docs/superpowers/plans/2026-09-18-career-investment-audit.md && git commit -m "feat: add career investment audit skill"`

- [ ] **步骤 4：推送分支**

运行：`git push -u origin codex/career-investment-audit`

交付 GitHub 分支链接和新增 Skill 文件链接；不自动合并到 `main`。
