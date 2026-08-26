---
name: xie-jian-li
description: 中文求职技能组（Router + 9 个子功能），基于持久化职业知识库生成 JD 定制求职材料。功能：(1) 职业知识库访谈录入与增量更新（grilling 一问一答，追加不覆盖）；(2) JD 匹配度分析与红标检测；(3) JD 定制简历（加载知识库→ATS预检→JD分类→事实挑选→X-Y-Z改写→溯源校验→字段结构组装→结构校验→HTML渲染，默认 HTML 可选 Markdown）；(4) 求职信（标准/推荐人/转行/应届四模板，300-500字）与 BOSS直聘打招呼语（boss 模板，50-100字，上限120）；(5) STAR 面试故事库；(6) 面试问题清单（有 JD 针对性出题）；(7) 高管简历；(8) 冷邮件（不联网调研）；(9) 网申文字题答案；(10) ATS 诊断。当用户说写简历/简历定制/投简历、分析岗位/匹配度/值得投吗、写求职信/cover letter、BOSS直聘打招呼/打招呼语/招聘App私聊话术、STAR故事/面试故事、准备面试/面试问题/面经、高管简历/VP简历/总监简历、冷邮件/联系猎头、填网申/申请表、ATS检查/过机审、换工作/新项目/更新知识库/整理经历、录入技能/技能清单/我会哪些技能、技能详细描述/深挖技能/能力描述时使用。支持 JD 以文字/链接/截图/PDF/Word 形式提供。不适用于：英文简历专项优化、代投简历/代发邮件、编造不存在的经历。
---

# xie-jian-li：中文简历求职技能组

本技能是 Router：识别意图 → 触发反馈 → 知识库检查 → 路由到对应子功能。严格执行「知识库有的事实才能上简历」，不编造经历。

> 当前版本：v1.7.1（2026-08-26）· 变更记录见技能目录「更新日志.md」

## 运行流程（每次触发必走）

1. **意图识别 + 触发反馈**：识别输入类型——纯文字直接匹配；链接先抓取页面；截图/照片用 OCR/Vision 提取；PDF/Word 先提取文字。提取的 JD 先展示确认（「我读到了这个 JD，你看对吗？」），提取失败请用户手动粘贴。匹配成功后给用户一句触发反馈（说明将执行什么）。
2. **知识库检查**：读取技能目录 `config.yaml` 的 `kb_path`：
   - 无 config 或 kb_path 为空 → 走「初始化引导」
   - kb_path 下 `原始事实/`、`自动生成/` 结构不完整 → 提示路径可能变更，询问：重新初始化 / 修改 kb_path / 暂不处理
   - 结构完整 → 按路由目标执行
   - 例外：用户明确要求「初始化/整理经历」时直接进访谈
3. **执行子功能**（见路由表）
4. **汇总与校验**：确认产物文件真实生成，告知路径 + 1-2 句下一步建议；执行失败时告知具体环节和原因 + 建议（重试/跳过/手动），不假装成功。
5. **意图无法匹配**：友好告知能力范围 + 功能清单，引导重新描述；连续 3 次不匹配则停止回环，建议查看技能说明或改用其他工具。

## 路由表

| 用户意图（关键词） | 子功能 | 说明 |
|------------------|--------|------|
| 换工作 / 新项目 / 新经历 / 更新知识库 | 增量更新 | 先过知识库检查，再一问一答追加 |
| 录入技能 / 技能清单 / 我会哪些技能 | 技能清单维护 | 必读 `references/skills-inventory-standard.md`；确认后写入 |
| 技能详细描述 / 深挖技能 / 能力描述太单薄 | 技能深挖 | 必读 `references/skill-mining-playbook.md`；支架式提问，产物确认后存 skill_details.md |
| 初始化 / 整理经历 / 重建知识库 | KB 访谈 | 可跳过检查直接进 |
| 分析岗位 / 匹配度 / 值得投吗（附JD） | JD 分析 | 报告末尾主动询问是否衔接简历管线 |
| 写简历 / 简历定制 / 投简历（附JD） | 简历管线 | 核心管线，见下文 |
| 写求职信 / cover letter | 求职信 | 先问模板（标准/推荐人/转行/应届），300-500 字 |
| BOSS直聘打招呼 / 打招呼语 / 招聘App私聊话术 | 求职信（boss 模板） | 免问模板，直接 `--template boss`，50-100 字（上限 120），强调岗位匹配 + 公司动态钩子 + 提问式结尾 |
| STAR故事 / 面试故事 | STAR 故事库 | 落盘 面试素材/（持久） |
| 准备面试 / 面试问题 / 面经 | 面试清单 | STAR 缺失时先生成故事库 |
| 高管简历 / C-level / VP / 总监简历 | 高管简历 | 高管六段结构 |
| 冷邮件 / 联系猎头 / 联系HR | 冷邮件 | 仅用用户信息+知识库，不联网调研 |
| 填网申 / 申请表 / application form | 网申答案 | 逐题生成，不与简历重复 |
| ATS检查 / 过机审 / ATS优化 | ATS 诊断 | 脚本输出报告 |

## 子功能执行要点

### KB 访谈与增量更新（N5/N6）

- 访谈风格、六类量化策略、退出/重入、冲突对话流程：读 `references/interview-methodology.md`
- 全部写入经 `scripts/kb_interview.py`（追加不覆盖，自动重生成 facts.yaml、版本+1、记 changelog）
- `append-work` 退出码 2 = 同公司冲突：暂停写入，新旧并排展示，用户裁决后再写
- 目录结构：`scripts/kb_interview.py init --kb <路径>` 自动创建，规范见 `references/knowledge-structure.md`
- **基本信息/工作/项目/技能/优势录入**：全部通过 `scripts/kb_interview.py` 追加写入（`append-work`、`append-project`、`append-skill`、`append-advantage`），追加不覆盖；写入后自动重生成 `facts.yaml`、版本+1、记 `changelog`
- **技能清单确认门禁**：技能的定义（通用能力/专属能力两段）、命名格式、条目写法（专属=熟练度+佐证；通用=证据强度+场景）与确认流程，必读 `references/skills-inventory-standard.md`。所有技能（用户自报 + AI 从经历推断）必须先整批展示给用户确认，确认的条目才用 `append-skill`（通用能力加 `--type general`）逐条写入；未确认不落盘。简历与求职材料只准使用 skills.md 中已确认的技能。查看清单用 `list-skills`
- **优势录入**：个人优势/岗位胜任条目用 `append-advantage --text '...'` 写入 `原始事实/advantages.md`，展示层自动置顶为「岗位胜任」
- **技能深挖**：为核心技能写详细描述前信息不足时，按 `references/skill-mining-playbook.md` 支架式提问（把创作题变成选择题/填空题/改错题，不抛开放式大问题），核心技能挖全 STAR-Plus 五维、其余从简；产物经用户确认后写入 `原始事实/skill_details.md` 并运行 `facts_parser.py` 重建
- **STAR 行为证据挖掘**：在 KB 访谈/增量更新对话中，当用户说出具体工作经历、项目经历、技能使用场景或优势时，Agent 应语义触发 → 暂停主线 → 按 `references/tacit-mining-methodology.md` 用 CDM/对比/Laddering/反事实/隐喻轮换追问 5-8 轮 → Teachback 确认 → 写入 `原始事实/behavioral_evidence/` → 返回主线

#### skill_details 与 behavioral_evidence 的协作规则

| 产物 | 生成时机 | 内容格式 | 给谁用 |
|---|---|---|---|
| `skill_details.md` | 用户主动要求「深挖某技能」时，用 `skill-mining-playbook.md` 支架式提问 | 五维块：情境/行动/结果/沉淀 | 简历岗位胜任、面试 STAR 故事 |
| `behavioral_evidence/*.md` | KB 访谈主线中语义触发时，用 tacit-mining 方法 | STAR + Key Insight + Boundary + 原话 | 工作/项目/技能/优势的事实佐证 |

**协作流程**：
1. 若某条 `behavioral_evidence` 明显对应一个技能（如「商务谈判签下 3000 万」），可用 `scripts/mining/evidence_to_skill_detail.py --skill 商务谈判` 转换成 `skill_details.md` 草稿。
2. `scripts/mining/skill_validator.py --skill 商务谈判` 会同时统计 `behavioral_evidence/` 和 `skill_details.md` 中的证据数量。
3. 写入 `skills.md` 前，若建议熟练度低于用户自报档位，必须提示降级或继续挖掘，不得直接按用户自报写入。

### JD 分析（N8）

`python3 scripts/jd_analyzer.py --jd <jd文件> --kb <路径>`，打分算法与红标标准读 `references/jd-analysis-methodology.md`。脚本粗筛后必须人工复评同义词与语义覆盖。

### 简历管线（N9，核心）

管线内部自行处理全部交互与循环，每步给进度反馈：

1. **加载知识库**：`cli.py summary` 展示摘要给用户
2. **ATS 预检**：`ats_checker.py --jd <jd>`（不传 --resume 即预检），报告 gap
3. **JD 分类**：`jd_classifier.py --jd <jd>` → 技术/销售/运营/产品/管理，**展示给用户确认**，不确认则重分
4. **跨行业检测**：分类结果 career_switch_hint=true 时询问是否启用转行模式
5. **事实挑选**：`fact_selector.py --jd <jd> --json-out picked.json`（转行加 --career-switch），展示选中事实
6. **改写**：`bullet_rewriter.py --selected picked.json --out bullets.json` 产出硬事实层 → Claude 在此基础上润色表达（三层控制：硬事实自动校验、表达风格不校验、灰区 {?} 用户确认）。写作规范读 `references/resume-writing-methodology.md` 与 `references/writing-formulas.md`；板块字段结构（核心职责/关键业绩/专业能力/荣誉奖项、项目描述/职责与行动/成果与影响、岗位胜任、技能）必须读 `references/resume-section-standard.md`
7. **溯源校验**：`provenance_verifier.py --bullets bullets.json`；退出码 2 = 有拦截 → 引导用户补事实/修正/删除 → 重写 → 再校，不得跳过
8. **初稿确认**：按 `references/resume-section-standard.md` 的字段结构组装 resume.json 展示给用户，用户要求修改则返回第 6 步
9. **结构校验**：`resume_structure_check.py --resume resume.json`；退出码 2 = 字段不达标 → 修正后重新组装再校，不得跳过
10. **渲染**：`html_renderer.py --resume resume.json`（默认 HTML；用户要求 Markdown 时用 `markdown_renderer.py`）

### 其余子功能

| 子功能 | 命令 / 方式 | 参考文档 |
|--------|-----------|---------|
| 求职信 / 打招呼语 | `cover_letter_renderer.py --jd <jd> --template <模板>` 出骨架 → Claude 填成稿 → `--check <成稿> --template <模板>` 校字数（boss 50-100/上限 120，其余 300-500） | `references/cover-letter-templates.md` |
| STAR 故事库 | `star_story_generator.py` 出骨架 → Claude 对话补全 A/R → 三版本 | `references/star-story-bank.md` |
| 面试清单 | `interview_prep_generator.py [--jd <jd>]`（退出码 3 = 先生成 STAR） | — |
| 高管简历 | `executive_resume_renderer.py` 出骨架 → Claude 补 Executive Profile | — |
| 冷邮件 | LLM 直接生成：提取 1-2 个亮点、200-300 字、五种开头策略（直接式/价值式/请教式/共同点式/推荐式）、同事语气、明确下一步 | — |
| 网申答案 | LLM 直接生成：识别问题类型（动机/经历/情景/优缺点/薪资/其他/开放），每题 1-3 句，事实来自知识库 | — |
| ATS 诊断 | `ats_checker.py --jd <jd> --resume <简历>` | `references/ats-checklist.md` |

## 边界（必须遵守）

- 不编造经历：知识库没有的事实不上简历；溯源拦截项不得自动放行
- 不联网调研目标公司；不代投简历、不代发邮件、不登录招聘平台
- 知识库追加写入不覆盖；删除/修改需用户明确指示
- 知识库路径只写技能目录 config.yaml，不改全局配置
- 「生成物/」可清理；「面试素材/」与「原始事实/」是持久资产，不得删除

## 版本管理（修改技能时必须执行）

- 每次升级、修改、优化本技能的任何文件（模板/脚本/文档/SKILL.md），完成前必须运行：
  `python3 scripts/version_bump.py --type <major|minor|patch> --note "变更摘要"`
- 脚本自动完成三件事：递增 SKILL.md 顶部版本号、更新版本日期、在「更新日志.md」顶部追加一条记录（日期 + 版本号 + 变更内容）
- 版本号规则：major = 架构/流程变更；minor = 新功能/新字段/新脚本；patch = 修复与样式优化
- 版本号只增不减；禁止手工编辑版本行和更新日志的历史条目
