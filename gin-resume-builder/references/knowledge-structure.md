# 知识库目录结构

> N3 初始化与结构校验时必读。初始化用 `scripts/kb_interview.py init --kb <路径>` 自动创建。

## 目录树

```
{知识库路径}/
├── 原始事实/                  # 唯一数据源（Single Source of Truth），追加写入不覆盖
│   ├── basic_info.md          # - 键: 值（姓名/电话/邮箱/城市/求职意向/教育背景）
│   ├── work_history.md        # ## 公司 | 职位 | 2020.01-2023.05 + bullet 列表
│   │                          #   特殊条目：## 职业空窗期 | 空窗期类型 | 起止时间，用于填充工作经历时间线断档
│   │                          #   空窗期类型示例：技能提升 / 家庭统筹 / 健康调整 / 自由职业 / 进修学习
│   ├── projects.md            # ## 项目名 | 角色 | 时间段 + bullet 列表
│   ├── skills.md              # 两段：## 通用能力（- 能力名（证据：强/中）｜场景：…）/ ## 专属能力（- 技能名（熟练度）｜佐证：…），规范见 references/skills-inventory-standard.md，确认后写入
│   ├── skill_details.md       # ## 技能名 + - 情境/行动/结果/沉淀 五维块（深挖产物，规范见 references/skill-mining-playbook.md）
│   ├── advantages.md          # - 优势条目
│   ├── internal_notes.md      # 用户私下备注（不上简历的信息，如离职真实原因）
│   ├── behavioral_evidence/   # 新增：STAR 行为证据碎片（自动维护，禁止手动编辑）
│   │   ├── map.md             # 行为证据索引
│   │   └── be_*.md            # 单个 STAR 证据碎片（规范见 references/tacit-mining-methodology.md）
│   └── claims/                # 主张（Claim）记录：每条经历 bullet 对应一条 claim（自动维护，禁止手动编辑）
│       ├── claims.json        # 汇总索引
│       └── claim_*.json       # 单个 claim 文件
│
├── 自动生成/                  # 脚本派生，禁止手动编辑
│   ├── facts.yaml             # facts_parser.py 生成（JSON 格式 YAML，可被 json.load 读取）
│   ├── meta.json              # {"version": N, "updated_at": "..."}，每次写入 +1
│   └── changelog.md           # 追加式变更日志
│
├── 面试素材/                  # 持久资产，不可清理
│   ├── star_stories.md        # star_story_generator.py 生成
│   └── question-bank.md       # interview_prep_generator.py 首次运行动态生成，增量积累
│
└── 生成物/                    # 可清理临时产物，删除不影响知识库
    ├── resumes/               # HTML/Markdown 简历
    ├── target_roles/          # JD 分析报告
    ├── cover_letters/         # 求职信
    ├── interview_prep/        # 面试问题清单
    ├── executive_resumes/     # 高管简历
    ├── cold_emails/           # 冷邮件
    ├── app_forms/             # 网申答案
    └── ats_reports/           # ATS 诊断报告
```

## 结构校验规则（N3 判定逻辑）

- `原始事实/` 与 `自动生成/` 均存在 → 结构完整（YES）
- 缺失任一 → 结构不完整（NO → N4 引导：重新初始化 / 修改 kb_path / 暂不处理）

## 文件格式约定

- Markdown 一律 UTF-8；条目以 `## ` 开头，字段用 ` | ` 分隔；bullet 用 `- `
- 时间段格式：`YYYY.MM-YYYY.MM` 或 `YYYY.MM-至今`
- facts.yaml 由脚本生成，事实条目带稳定 fact_id（W1/P1…），供溯源校验回查
- skill_details.md 例外：条目为 `## 技能名`（无 ` | ` 字段），bullet 固定四维 `情境/行动/结果/沉淀`

## behavioral_evidence 格式约定

路径：`原始事实/behavioral_evidence/`

### map.md

索引文件，按域列出所有证据碎片。由 `scripts/mining/evidence_store.py` 自动维护，禁止手动编辑。

### be_{domain}_{序号}.md

单个 STAR 证据碎片，文件名中的 `{domain}` 只能是 `work_experience` / `project_experience` / `skill_mastery` / `advantage_evidence`。

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
## 任务（Task）
## 行动（Action）
## 结果（Result）
## 关键判断（Key Insight）
## 边界条件（Boundary）
## 原话（Verbatim）
```

禁止手动编辑，统一由 `scripts/mining/evidence_store.py` 维护。

## claims 格式约定

路径：`原始事实/claims/`

### claims.json

汇总文件，包含当前所有 claim 的数组，由脚本自动维护，禁止手动编辑。

### claim_{id}.json

单个主张记录，字段标准如下：

| 字段 | 说明 |
|------|------|
| `id` | claim 唯一标识 |
| `section` | 归属板块：`work_history` / `project` / `advantage` |
| `section_id` | 板块内条目标识，如 `公司名-起始年月` |
| `source_fact` | 用户原始说法，不做包装 |
| `candidate_wording` | 可用于简历的候选表述 |
| `responsibility_level` | 参与 / 负责模块 / 主导方案或交付 / 项目负责人 |
| `verification_status` | 已确认 / 待确认 / 已过期 / 不采用 |
| `allowed_uses` | 可用于哪些岗位版本或求职材料 |
| `interview_details` | 追问展开用的决策、难点、验证、结果 |
| `boundary` | 团队成果与个人贡献的明确分界 |
| `risk_notes` | 冲突、缺口或成稿前必须处理的问题 |
| `last_verified` | 最近一次确认日期（YYYY-MM-DD） |

禁止手动编辑单个 claim 文件，统一由 `scripts/common.py` 中的 `write_claim` / `write_claims` 维护。
