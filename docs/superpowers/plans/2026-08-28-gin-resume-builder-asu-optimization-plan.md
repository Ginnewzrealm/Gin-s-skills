# gin-resume-builder ASu 优化方案实施计划

> 来源：`/Users/fubo/Downloads/ASu技能对比与改进方案.md`
> 工作区：`/Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-builder-asu`
> 分支：`feature/gin-resume-builder-asu-claims`
> 日期：2026-08-28

---

## 目标

在保持现有 N9 简历管线框架不变的前提下，内嵌 ASu 的「主张—证据账本」机制，解决事实归属、年限、责任层级混乱的问题。

---

## 任务拆分

### 任务 1：Claim 目录结构与字段定义（P0）

**目标：** 让知识库能持久化 claim 记录。

**改动点：**
- `scripts/common.py`：
  - `ensure_kb_structure()` 新增 `原始事实/claims/` 子目录。
  - 新增 claim 标准字段常量 `CLAIM_FIELDS`。
  - 新增 `read_claims(root)` / `write_claim(root, claim)` / `write_claims(root, claims)` 工具函数。
- `references/knowledge-structure.md`：补充 claims 目录说明与 claim 字段语义。
- `references/resume-section-standard.md`：补充 `responsibility_level` 标注规则。

**验收：**
- `ensure_kb_structure()` 运行后目录结构包含 `原始事实/claims/`。
- claim 文件 JSON Schema 与 ASu 方案一致：id、section、section_id、source_fact、candidate_wording、responsibility_level、verification_status、allowed_uses、interview_details、boundary、risk_notes、last_verified。

---

### 任务 2：知识库格式增加责任层级与验证状态（P0）

**目标：** 在现有 `work_history.md` / `projects.md` 中支持责任层级标注。

**改动点：**
- `scripts/common.py`：
  - 扩展 `parse_entries()`：识别 bullet 前的 `**[主导]**`、`**[参与]**` 等责任层级标记，输出到 `bullets` 字符串（保留标记）并额外提取 `responsibility_level` 字段。
- `scripts/facts_parser.py`：
  - 将 responsibility_level 写入 `facts.yaml`。
  - 默认 `verification_status = "待确认"`，用户已确认过的可改为 `"已确认"`。
- `references/knowledge-structure.md`：给出 markdown 标注示例。

**验收：**
- 含 `**[主导]**` 前缀的 bullet 能被正确解析。
- `facts.yaml` 中每个 fact 增加 `responsibility_level` 和 `verification_status` 字段。

---

### 任务 3：溯源校验升级（P0）

**目标：** 在现有 `provenance_verifier.py` 中增加年限、归属、责任层级三重检查。

**改动点：**
- `scripts/provenance_verifier.py`：
  - 接收 resume.json 或 bullets.json（含 `section_id`、`org`、`role`、`period`）。
  - **年限一致性**：bullet 里的时间段是否与 fact 的 `period` 一致。
  - **公司归属**：bullet 中的 `org` 是否与 fact 的 `company` / `name` 一致。
  - **责任层级匹配**：bullet 文本含「主导/负责/0→1/核心」等强主张时，检查 `responsibility_level` 是否为参与；若是参与则标红或降级提示。
  - 退出码调整：0=通过，1=警告可继续，2=拦截必须裁决，3=发现事实冲突（两版本矛盾）。
- `gin-resume-builder/tests/`：新增 `test_provenance_verifier.py`，覆盖通过/年限错误/归属错误/责任层级不匹配/冲突退出码 3。

**验收：**
- 测试覆盖 5 种场景且全部通过。
- 命令行返回正确退出码。

---

### 任务 4：强主张审计节点（P1）

**目标：** 在 N9 管线第⑤步（改写）之后增加审计，防止夸大强主张。

**改动点：**
- 新建 `scripts/strong_claim_auditor.py`：
  - 扫描所有待写入 bullet，命中强动词（主导、负责、0→1、核心、Owner）时触发审计。
  - 必须能回答：个人具体做了什么决策/动作？结果数字的口径/来源？
  - 无法回答 → 自动降级措辞为「参与」或标注 `【待确认】`。
  - 输出审计报告 JSON。
- `SKILL.md`：更新 N9 管线步骤说明，插入第⑥步「强主张审计」。

**验收：**
- 示例 bullet 含「主导」但 responsibility_level=参与时，输出降级或待确认标记。
- 有明确证据时正常通过。

---

### 任务 5：主张绑定节点（P1）

**目标：** 每条通过的 bullet 生成/更新一条 claim 记录。

**改动点：**
- 新建 `scripts/claim_binder.py`：
  - 输入：通过审计和溯源校验的 bullets + facts。
  - 为每条 bullet 生成 claim：
    - `source_fact`：原始 bullet 文本。
    - `candidate_wording`：改写后文本。
    - `responsibility_level`：从 fact/bullet 提取。
    - `verification_status`：默认 `"已确认"`（已通过硬闸门）。
    - `boundary`：追问用户个人贡献占比或团队/个人分界。
    - `interview_details`：追问决策、难点、验证、结果四要素。
  - 写入 `原始事实/claims/claims.json`。
- `scripts/common.py`：新增 claim 读写工具（已在任务 1）。
- `SKILL.md`：更新 N9 管线步骤说明，插入第⑧步「主张绑定」。

**验收：**
- 运行后 `claims.json` 包含与 bullets 对应的 claim 记录。
- 边界和面试细节字段非空。

---

### 任务 6：冲突处理与退出码 3（P1）

**目标：** 同一事实出现多个矛盾版本时，明确退出码 3 并要求用户裁决。

**改动点：**
- `scripts/provenance_verifier.py`：
  - 当检测到同一段经历/同一条主张存在多个版本且互相矛盾时，返回退出码 3。
  - 输出冲突项列表。
- `scripts/kb_interview.py` / `scripts/facts_parser.py`：
  - 追加事实时检测冲突：同 `section_id` + 同 `source_fact` 核心信息不一致时，不直接覆盖，改为生成冲突记录。

**验收：**
- 测试用例覆盖冲突场景，返回退出码 3。

---

### 任务 7：interview_details 回填 STAR 故事库（P2）

**目标：** 让 STAR 故事库与 claim 账本关联。

**改动点：**
- `scripts/star_story_generator.py`：
  - 生成 STAR 故事后，读取 `claims.json`，找到对应 claim，回填 `interview_details`。
- `references/star-story-bank.md`：说明回填机制。

**验收：**
- STAR 故事生成后，对应 claim 的 interview_details 被更新。

---

### 任务 8：材料盘点最小化补问（P2）

**目标：** 在简历管线开始前，自动盘点缺失项并只问最关键的 3 项。

**改动点：**
- 新建 `scripts/material_inventory.py`：
  - 扫描知识库已有内容。
  - 列出缺失项并按对交付的影响排序。
  - 输出前 3 个待补问问题。
- `SKILL.md`：在访谈流程前增加「材料盘点」环节。

**验收：**
- 运行后输出 ≤3 个补问问题。

---

## 通用要求

- 每个任务遵循 TDD：先写测试，再写实现。
- 每次改动后运行 `python3 -m pytest gin-resume-builder/tests/ -q`。
- 版本号使用 `scripts/version_bump.py` 递增 minor 版本，并更新 `更新日志.md`。
- 所有改动在 `.worktrees/gin-resume-builder-asu` 内完成，不污染 main。

---

## 后续收尾

- 全部任务完成后运行 `superpowers:finishing-a-development-branch` 决定合并/PR/清理。
