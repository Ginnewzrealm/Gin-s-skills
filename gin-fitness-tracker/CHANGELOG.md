# 健身追踪技能更新日志

> 每次对技能进行修改时，必须同步更新此文件。

---

## 如何记录更新

每条更新记录包含：

| 字段 | 说明 |
|------|------|
| 日期 | 更新日期，格式 `YYYY-MM-DD` |
| 版本 | 语义化版本号 `vX.Y.Z` |
| 更新类型 | `新增` / `修复` / `优化` / `重构` |
| 文件 | 修改的文件名 |
| 内容 | 详细描述 |

---

### v3.4.1 — 2026-08-29

**更新类型**：修复

**涉及文件**：
- `knowledge/sheets-calling-patterns.md`
- `skills/write-verify/SKILL.md`
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

1. **修复 `+cells-set` 写入导致列格式丢失问题**：写入时在每个 cell JSON 中显式附带 `number_format`，从源头保持百分比、时间等列的显示格式
2. **更新 `write_fields_by_name` 调用示例**：百分比列传小数（如 `0.216`）并附带 `"number_format": "0.00%"`，时间列附带 `"h:mm"` / `"HH:mm:ss"`
3. **明确 `number_format` 来源**：来自 `read_column_formats` 返回的 `column_constraints[col].number_format`
4. **版本号升级**：`SKILL.md` frontmatter version 从 `v3.4.0` 升级到 `v3.4.1`

---

### v3.4.2 — 2026-08-29

**更新类型**：优化

**涉及文件**：
- `scripts/validate_field_metadata.py`
- `skills/collect-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `knowledge/field-guide.md`
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

1. **新增字段元数据类型/选项硬校验脚本 `validate_field_metadata.py`**：根据字段元数据子表的「类型」和「选项」对用户输入做硬校验，支持数字、时间、日期、单选、多选、文本、公式类型
2. **`collect-data` 明确自然语言解析原则**：要求 Agent 用 LLM 语义理解从用户自然语言中提取字段和值，禁止关键词脚本硬匹配；提供用户示例并说明歧义字段需主动确认
3. **`write-verify` 增加字段元数据类型校验步骤**：写入前强制检查清单新增「字段值是否符合字段元数据子表的类型和选项」；失败时返回具体错误，单选值不在选项中需列出全部可选值
4. **`knowledge/field-guide.md` 更新为三层校验模型**：字段处理规则表扩展为「读取 / Agent 提取 / 写入前校验」四列，明确语义提取层、元数据校验层、真实格式转换层的职责边界
5. **版本号升级**：`SKILL.md` frontmatter version 从 `v3.4.1` 升级到 `v3.4.2`

---

### v3.4.0 — 2026-08-29

**更新类型**：优化

**涉及文件**：
- `SKILL.md`
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/query-data/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `references/xunji-bridge.md`
- `references/lark-sheets-bridge.md`
- `knowledge/xunji-api-guide.md`
- `knowledge/sheets-calling-patterns.md`
- `CHANGELOG.md`

**内容**：

1. **新增 Progress Checklist 使用规则**：主 `SKILL.md` 增加统一规则、场景定位句、标签说明、展示时机与禁止项
2. **5 个子技能执行流程 checklist 化**：init/collect-data/write-verify/query-data/sync-xunji 分别插入 micro-checklist，标注 `[自动]` / `[需确认]` / `[硬闸门]` / `[可回环]`
3. **硬闸门显性化**：在 collect-data 问题生成前检查单、write-verify 已有值检查、单选项匹配等位置增加 `当前阻塞：等待你确认 XXXX` 提示
4. **新增 `references/xunji-bridge.md`**：按技能桥接模式技术规范 v2.0 五章格式，整合讯记桥接约定
5. **新增 `references/lark-sheets-bridge.md`**：按规范五章格式，收敛飞书表格调用契约
6. **知识库文件增加桥接指针**：`xunji-api-guide.md` 与 `sheets-calling-patterns.md` 顶部增加指向新桥接文件的说明
7. **版本号升级**：`SKILL.md` frontmatter version 从 `v3.3.0` 升级到 `v3.4.0`
8. **collect-data 标签与 Cron 场景澄清**：Step 6 `[需确认]` 改为 `[等待用户回复]`；Step 5 硬闸门补充 Cron 触发时不等待用户、直接返回失败的降级说明

---

### v3.3.0 — 2026-08-26

**更新类型**：重构

**涉及文件**：
- `SKILL.md`
- `skills/write-verify/SKILL.md`
- `knowledge/sheets-calling-patterns.md`
- `knowledge/field-guide.md`
- `config/field-metadata-schema.md`
- `scripts/coerce_value.py`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **工具优先写入协议**：写入前调用 `lark-cli sheets +cells-get --include style,data_validation` 一次性读取每列真实 `number_format` 和 `data_validation`，建立 `column_constraints`。
2. **新增通用转换脚本 `scripts/coerce_value.py`**：根据真实列约束自动转换原始值（百分比→小数、时间字符串→Excel 小数、下拉选项校验），无字段特殊逻辑。
3. **移除字段元数据「类型」驱动的硬编码转换**：`write-verify` 不再按「数字/文本/时间」类型表决定写入形态，改为由 `read_column_formats` + `coerce_value.py` 驱动。
4. **修复时间字段类型矛盾**：`config/field-metadata-schema.md` 中入睡/起床/各餐时间字段类型统一为 `时间`；`field-guide.md` 说明字段元数据类型仅作语义提示，真实写入格式由运行时探查决定。
5. **强化单选/多选防污染**：单选匹配与选项数复查均基于 `read_column_formats` 返回的真实 `data_validation.items`，不再依赖逐列 `+dropdown-get`。
6. **更新 `evals/evals.json`**：新增覆盖百分比转换、时间转换、`INVALID_OPTION`、工具命令文档化等 eval 用例；版本号更新到 `v3.3.0`。

---

### v3.2.10 — 2026-08-23

**更新类型**：修复

**涉及文件**：
- `SKILL.md`
- `skills/write-verify/SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **修复"伪写入"问题**：Agent 口头报告写入成功但实际未写入表格。
2. **强化写入后回读验证为硬性规则**：在 `write-verify` 中新增「写入后回读验证」章节，明确要求写入 → 回读 → 对比 → 一致后才算成功；未通过回读验证不得标记为 `success`。
3. **要求记录写入成功证据**：`lark-cli` 返回必须包含 `revision` 和 `updated_cells_count`；没有这些证据视为写入失败。
4. **延迟反馈协调器成功反馈**：`SKILL.md` 明确「✅ 数据记录完成」只能在 `write-verify` 返回 `success` 且复查通过后发送；`failed` 或 `partial` 时禁止发送完成反馈。
5. **更新 `evals/evals.json`**：新增 `eval-31` 到 `eval-33`，覆盖写入后回读验证、写入成功证据、延迟成功反馈；版本号更新到 `v3.2.10`。

---

### v3.2.9 — 2026-08-23

**更新类型**：优化

**涉及文件**：
- `SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/collect-data/SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **新增「写入前强制检查清单」**：在 `write-verify` 执行流程中增加强制检查步骤，要求每次写入前依次检查：字段名是否在表头行白名单、字段类型是否允许写入、单选值是否在真实下拉选项中、时间值是否为数字小数值。
2. **新增「问题生成前强制检查清单」**：在 `collect-data` 执行流程中增加强制检查步骤，要求生成问题前字段名必须 100% 来自 `read_header` 返回的表头行，不在表头行中的字段名不得生成问题。
3. **新增「字段名白名单」机制**：在 `SKILL.md` 中明确所有字段名以运行时读取的表头行为唯一白名单；`write-verify` 中增加白名单校验，不在白名单中的字段名返回 `FIELD_NOT_FOUND`。
4. **新增「单选字段匹配算法」**：在 `write-verify` 中把单选字段的语义映射和原文复制写成明确的四步算法，禁止跳过步骤或自行构造字符串。
5. **新增错误码 `FIELD_NOT_FOUND`**：在 `SKILL.md` 错误码表和 `write-verify` 错误模板中补充该错误码，用于处理写入请求包含表头行中不存在字段名的情况。
6. **更新 `evals/evals.json`**：新增 `eval-26` 到 `eval-30`，覆盖写入前检查清单、问题生成前检查清单、字段名白名单、单选匹配算法化和 `FIELD_NOT_FOUND` 错误码；版本号更新到 `v3.2.9`。

---

### v3.2.8 — 2026-08-22

**更新类型**：优化

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `knowledge/field-guide.md`
- `SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **强化单选字段核心认知**：在 `write-verify` 中新增「单选字段的核心认知」章节，明确单选字段不是文本字段，Agent 的工作是"做选择"而不是"写答案"；选择完成后必须原样复制选项原文，禁止任何改写、缩写、同义词替换、emoji 增减。
2. **同步更新 `knowledge/field-guide.md`**：字段处理规则中明确单选/多选字段"不是写，是选"。

---

### v3.2.7 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `evals/evals.json`
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

1. **强化单选字段「原文复制」规则**：在 `write-verify` 的「锁 2」中明确禁止任何形式的改写或构造，包括把 `🟢没有` 写成 `🟢无`、去掉 emoji、替换同义词等。写入值必须 100% 来自真实下拉选项原文。
2. **修正 8/22 午后能量低谷**：将非法值 `🟢无` 改为合法选项 `🟢没有`。
3. **更新 `evals/evals.json`**：在 `eval-12` 中增加对 `🟢无` 示例的检查；版本号更新到 `v3.2.7`。

---

### v3.2.6 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `字段元数据` 子表（真实表格）
- `SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **修正字段元数据与真实下拉选项不一致问题**：真实表格「早起状态」列只有 4 个下拉选项，但字段元数据子表中错误地写成了 6 个（多了 `疲惫 / 正常`），导致 Agent 写入非法值 `🟢正常`。已将字段元数据子表修正为与真实下拉完全一致。
2. **强化单选项匹配规则**：`write-verify` 中「锁 1」改为优先读取 `read_dropdown_options` 真实下拉选项，字段元数据仅作参考；两者不一致时以真实下拉为准，并返回 `FIELD_TYPE_MISMATCH` warning。
3. **修正 8/22 早起状态**：将 `🟢正常` 改为合法选项 `🟢正常不精神也不疲惫`。

---

### v3.2.5 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `knowledge/field-guide.md`
- `SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **修复时间字段写入方式**：明确时间字段（如入睡时间、起床时间）必须写入时间对应的小数值（如 `07:00` 写成 `7/24`），不能直接写入字符串，避免被 Sheets 识别为文本导致公式计算出错。
2. **同步更新 `knowledge/field-guide.md`**：字段处理规则表中增加「时间字段」行，说明写入时必须转换为小数值。

---

### v3.2.4 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `SKILL.md`
- `knowledge/field-guide.md`
- `skills/collect-data/SKILL.md`
- `skills/query-data/SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **新增「字段来源唯一权威」规则**：在 `knowledge/field-guide.md` 中明确所有字段名必须来自运行时读取的表头行字段全集，禁止凭记忆、示例、语义推断或"补全"目的编造字段名（如"下午茶时间"、"下午茶感觉"）。
2. **强化 `collect-data` 字段来源红线**：生成问题时字段名必须 100% 来自 `read_header` 返回的表头行，当前时段无字段时不得编造问题。
3. **强化 `query-data` 字段来源红线**：`raw_record` 的键必须 100% 来自表头行字段名，禁止补全不存在的字段。
4. **更新 `evals/evals.json`**：新增 `eval-25` 检查字段来源唯一权威规则；版本号更新到 `v3.2.4`。

---

### v3.2.3 — 2026-08-22

**更新类型**：优化

**涉及文件**：
- `SKILL.md`
- `skills/query-data/SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`

**内容**：

1. **新增 `query-data` 返回字段 `raw_record`**：查询结果中每个记录必须包含表头行定义的全部字段，空白字段用 `null` 表示，不得过滤或省略。
2. **明确查询数据展示策略**：`SKILL.md` 反馈协调器根据用户意图选择展示方式——简单询问可展示 `filled_fields` 摘要；用户要求"检查"、"看一下"、"审计"、"核对"、"完整数据"时，必须展示完整 `raw_record`，Agent 不得替用户过滤空白字段。
3. **补充审计场景输出示例**：在 `query-data/SKILL.md` 中给出"检查一下 8 月 22 日数据"的完整展示示例。
4. **更新 `evals/evals.json`**：新增 `eval-24` 检查 `raw_record` 与完整展示规则；版本号更新到 `v3.2.3`。

---

### v3.2.2 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `SKILL.md`
- `evals/evals.json`
- `CHANGELOG.md`
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`
- `skills/query-data/SKILL.md`
- `knowledge/field-guide.md`
- `config/sheets-schema.md`（已有，新增引用）

**内容**：

1. **修复 `collect-data` 与 `write-verify` 返回值契约不一致**：`collect-data` 按统一契约 `{status, module, message, data, errors}` 解析 `write-verify` 结果，删除旧格式 `{success, verified, ...}` 描述。
2. **修复 `SKILL.md` 缺少 `version` 字段**：frontmatter 增加 `version: "v3.2.2"`，并同步更新 `evals/evals.json` eval-2 检查目标。
3. **修复 `init/SKILL.md` 流程图表述矛盾**：统一为"返回 `TABLE_NOT_FOUND` 错误，不自动创建"。
4. **统一 DataStore 方法名引用**：`query-data` 显式使用 `DataStore.getDailyRecord(date)`，`collect-data` 与 `query-data` 显式使用 `DataStore.getUserConfig()`；`field-guide.md` 补充子技能写入入口约束。
5. **收敛表格结构常量引用**：`collect-data`、`query-data`、`init` 中对 `lark-sheets` 调用的表名与范围描述统一引用已有的 `config/sheets-schema.md`，避免表格结构细节泄漏到业务逻辑。
6. **补充路由表模糊输入策略**：明确「健身追踪 + 日期/时段」进入补数据/轮询/询问分支。

---

### v3.2.1 — 2026-08-22

**更新类型**：重构 + 修复

**涉及文件**：
- `SKILL.md`
- `knowledge/field-guide.md`
- `knowledge/sheets-calling-patterns.md`（新增）
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/query-data/SKILL.md`
- `CHANGELOG.md`

**内容**：

1. **新增 `knowledge/sheets-calling-patterns.md`**：定义健身追踪与 `lark-sheets` skill 之间的 9 种显式调用模式（`verify_spreadsheet`、`read_header`、`read_field_metadata`、`read_user_config`、`find_date_row`、`read_dropdown_options`、`create_date_row`、`write_fields_by_name`、`verify_row_values`），并给出完整 CLI 命令模板。
2. **所有子技能改用显式调用模式**：`init`、`collect-data`、`write-verify`、`query-data` 中所有对 `lark-sheets` 的调用不再使用模糊意图（如"读取表头行"），必须附带 `sheets-calling-patterns.md` 中定义的完整命令模板。
3. **明确技能边界**：健身追踪负责业务字段语义、字段名→列字母映射、字段类型校验、单选选项匹配；`lark-sheets` skill 负责执行具体 `lark-cli sheets ...` CLI 命令。
4. **`init` 新增字段元数据一致性抽查**：初始化时随机抽取 3-5 个单选/多选字段，通过 `read_dropdown_options` 模式读取真实下拉选项，与字段元数据子表中的「选项」列比对；不一致时返回 warning，但不阻塞初始化。
5. **移除 `init` 的自动创建子表行为**：字段元数据子表或用户配置子表缺失时返回 `TABLE_NOT_FOUND`，不再自动创建。
6. **统一 `create_date_row` 描述**：`collect-data` 的每日轮询与补数据模式在日期行不存在时，统一调用 `create_date_row` 模式按日期升序插入新行。
7. **修复写入命令描述**：`write-verify` 明确使用 `write_fields_by_name` 模式的 `+cells-set --writes` 批量写入命令，删除"不直接调用 `lark-cli sheets`"的错误表述。
8. **修复复查命令描述**：`write-verify` 明确使用 `verify_row_values` 模式的 `+csv-get` 回读整行进行校验。

---

### v3.0.2 — 2026-08-22

**更新类型**：修复

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `skills/collect-data/SKILL.md`

**内容**：

修复写入格式错误导致的表格数据污染，核心原因不是校验缺失，而是写入方式错误：

1. **按字段名写入，不按数组顺序**——避免脂肪写入数字列、时间写错列
2. **跳过公式字段**——从字段元数据「写入方=Sheets」或「类型=公式」动态识别，不再写死字段名
3. **单选字段使用表格实际选项原文**——禁止 Agent 凭印象构造新措辞
4. **不自己做格式转换**——数字/时间/日期的具体格式由飞书表格单元格格式处理，Agent 只传正确形态的原始值

### v3.0.1 — 2026-08-03

**更新类型**：修复 + 重构

**涉及文件**：
- `skills/daily-poll/SKILL.md`（删除）
- `skills/sync-xunji/SKILL.md`
- `knowledge/routing-rules.md`（删除）
- `SKILL.md`
- `config/bitable-schema.md`
- `CHANGELOG.md`

**内容**：

采纳 skill-creator 验证测试（闭环/耦合/I-O 依赖）的 4 项修复：

1. **删除 v3.0 重构残留 `skills/daily-poll/SKILL.md`**
   - 该模块已拆分为 collect-data + query-data，主路由表与子技能索引均无它
   - 与 collect-data 内容 54% 重复，自带「查看模式」与 query-data 职责冲突
   - 头部注释技能名残缺（jian-shen-zhui-su），无统一返回格式，存在误注册风险

2. **删除 sync-xunji 与 xunji-api-guide 的双写**
   - 移除 `skills/sync-xunji/SKILL.md` 中「具体行为规则」整节（与 xunji-api-guide「数据来源优先级」94% 重复）
   - 保留单行引用，统一以 knowledge/xunji-api-guide.md 为准
   - 落实 v2.0.3 第 6 条当时未落地的修复

3. **删除路由规则双写**
   - 删除 `knowledge/routing-rules.md`（与主 SKILL.md 路由/反馈规则 75% 重复）
   - 主 SKILL.md 保留全文为唯一权威，知识库索引与附录索引同步移除该行

4. **消除配置表结构双写漂移**
   - `config/bitable-schema.md` 用户配置表段落改为引用 `config/user-profile-schema.md`
   - 修复漂移实证：调整信号、固定训练日、增肌期开始/结束 4 个配置项此前在 bitable-schema 中缺失

---

### v3.0.2 — 2026-08-03

**更新类型**：重构 + 优化

**涉及文件**：
- `knowledge/polling-rules.md`
- `skills/collect-data/SKILL.md`
- `skills/query-data/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `config/bitable-schema.md`
- `config/openclaw-config.md`（新增）
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

采纳 skill-creator 结构优化评估的 5 项获批修改：

1. **修复「时区与周定义」归属错位**
   - 时区规则、周定义与 Week Number 从 `skills/collect-data/SKILL.md` 迁移至 `knowledge/polling-rules.md`
   - 修复 query-data 需要输出 week number 但规则定义只在 collect-data 内的缺陷
   - 同时消除 collect-data 与 polling-rules 重复的「时段划分」表
   - 找回 daily-poll 删除时丢失的 ISO 8601 差异详细说明

2. **主 SKILL.md 三索引表合并**：子技能索引 + 知识库索引 + 附录文件索引（16 项中 11 项重复）合并为单一「文件索引」

3. **sync-xunji 相邻单行节合并**：「数据来源优先级」与「具体行为规则」合并为一节

4. **字段 description 规范统一**：`config/bitable-schema.md` 该节改为引用 `knowledge/polling-rules.md`

5. **主 SKILL.md 温和瘦身**（295 → 263 行）
   - 错误码表压缩为紧凑格式（完整文案模板保留在各子模块文件）
   - OpenClaw 配置键与事件入口下移至新增 `config/openclaw-config.md`

---

### v3.0.3 — 2026-08-03

**更新类型**：优化

**涉及文件**：
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

- 优化 frontmatter description 提升触发准确率（skill-creator 描述检查）：
  - 补齐 8 个缺失的中文触发词：看看健身、健身记录、查询健身、补一下、健身追踪配置、记录体重、今天吃了多少、看看这周数据
  - 补充 cron 每日轮询定时触发说明
  - 负面边界补齐「每周复盘分析」
  - 保留触发反馈提醒句（用户确认）
  - 触发词覆盖率 8/16 → 16/16，长度 173 → 280 字符（上限 1024）

---

### v3.0.4 — 2026-08-04

**更新类型**：修复 + 优化

**涉及文件**：
- `SKILL.md`
- `knowledge/field-guide.md`
- `skills/query-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `CHANGELOG.md`

**内容**：

针对真实使用中暴露的两类问题（报数据不触发、读写飞书字段出错）的 4 项修复：

1. **修复报字段数据不触发**：description 从「列举具体话术」改为「类目式触发」，按身体/状态/饮食/训练四类数据覆盖飞书表全部字段的报数场景；正文「何时使用」同步更新
2. **field-guide 新增「常见执行错误」节**：记录三个真实案例（读取自行挑字段子集、凭记忆写字段、按顺序构造写入内容），按错误做法→后果→正确做法记录
3. **查询模式条款收紧**：field-guide 与 query-data 明文禁止 record-list 自行传字段子集，任何模式字段全集以 +field-list 为准
4. **write-verify 复查基准明确化**：值对比以 +field-list 字段全集为基准，禁止以内存映射为基准；新增「出现未知字段名」错误分支

---

### v3.0.5 — 2026-08-05

**更新类型**：新增 + 优化

**涉及文件**：
- `skills/query-data/SKILL.md`
- `knowledge/polling-rules.md`
- `CHANGELOG.md`

**内容**：

针对真实使用中暴露的问题（裸调 feishu_bitable_get_record 绕过 query-data，把还没到时段的字段也报为「空白」）的 3 项修改：

1. **query-data 新增「今日时段归类（三态）」**：查询范围包含今日时，空白轮询字段不再笼统列为「空白」，而是按字段 description 的时段标记与当前时段对比分为三类——✅ 已填 / ⬜ 应填未填（字段时段 ≤ 当前时段）/ ⏳ 未到时段（字段时段 > 当前时段）。历史日期不做归类（全部空白即空白），未来日期全部为 ⏳ 未到时段
2. **区分轮询字段与元字段**：已填/空白统计只覆盖 description 含时段标记的轮询字段；日期、记录来源、数据异常标记、备注等元字段不参与统计，避免被误报为「空白字段」
3. **流程前置校准**：query-data 执行流程改为「解析范围 → 校准北京时间判断当前时段 → 调用 +field-list 读取字段全集与 description → 读配置 → 读数据 → 三态归类展示」；查询范围包含今日时必须调用 +field-list（时段归类与轮询字段识别的基准）。polling-rules.md 同步声明时段规则同时适用于 collect-data 问题生成与 query-data 空白字段归类

---

### v3.0.6 — 2026-08-05

**更新类型**：修复 + 新增

**涉及文件**：
- `skills/write-verify/SKILL.md`
- `knowledge/field-guide.md`
- `SKILL.md`
- `CHANGELOG.md`

**内容**：

针对真实使用中暴露的问题（agent 写入单选字段时按自己的语义理解构造新值，飞书 API 静默自动创建新选项，污染选项列表）的 4 项修改：

1. **write-verify 新增「单选/多选字段选项防污染（三锁）」**：
   - 锁 1（写入前·精确匹配）：语义映射不上任何已有选项时停止写入，返回 INVALID_OPTION 并列出全部现有选项；**一律禁止新建选项，无例外**——新增选项只能由用户在飞书字段设置中手动添加
   - 锁 2（值构造·原文复制）：写入值必须从 +field-list 选项列表中原样复制（含 emoji、空格、大小写），总原则为「语义理解只用于选，不用于写」
   - 锁 3（写入后·选项数对比）：record-get 复查通过后重新调用 +field-list 对比选项数量，数量增加即告警用户手动删除被静默新建的选项（常规值对比复查检测不到此类污染）
2. **field-guide 常见执行错误新增错误 4**：把语义理解的结果直接写入单选字段 → 飞书静默建项污染选项列表；记录错误做法/后果/正确做法
3. **write-verify 错误提示模板更新**：INVALID_OPTION 模板补充禁止新建说明与手动新增指引；新增「检测到未授权新选项」告警模板
4. **主 SKILL.md 错误码表同步**：INVALID_OPTION 处置说明补充「一律禁止新建选项」

---

### v3.2.0 — 2026-08-21

**更新类型**：重构 + 新增

**涉及文件**：
- `SKILL.md`
- `config/openclaw-config.md`
- `config/sheets-schema.md`
- `config/field-metadata-schema.md`（新增）
- `knowledge/field-guide.md`
- `knowledge/polling-rules.md`
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/query-data/SKILL.md`
- `evals/evals.json`（新增）
- `CHANGELOG.md`

**内容**：

1. **后端切换为飞书普通表格（Sheets）**：删除 `feishu_bitable` 支持，默认后端改为 `feishu_sheets`，配置键 `fitness.bitable.*` 全部移除。
2. **所有飞书操作委托给 `lark-sheets` skill**：健身追踪技能文档中不再出现 `lark-cli base ...` 或 `lark-cli sheets ...` 命令。
3. **新增「字段元数据」子表**：替代 Bitable 的字段 description，统一约定每个字段的时段、类型、写入方、选项、填写说明、单位、格式，避免不同 Agent 填写格式不一致。
4. **字段元数据子表为字段归属与格式的主来源**：`collect-data` / `query-data` / `write-verify` 运行时优先读取该子表；缺失时回退到字段名模式匹配。
5. **新增配置键 `fitness.sheets.field_metadata_sheet_name`**：默认 `字段元数据`，初始化时自动检测/创建。
6. **初始化流程新增字段元数据子表检测/创建步骤**。
5. **自动按日期升序创建日期行**：每日记录表由 "预先有空行" 模式改为写入时按需自动插入行，保持日期升序。
6. **公式字段由 Sheets 自动计算**：周编号、睡眠时长、腰臀比、早晚体重差为公式列；Agent 不写入这些字段。
7. **BMI 由 Agent 写入静态值**：collect-data 根据用户身高和晨起体重计算 BMI 后写入，不使用公式。
8. **周编号以周日为一周第一天**：与 `knowledge/polling-rules.md` 的周定义保持一致。
9. **错误码 `LARK_CLI_UNAVAILABLE` 改为 `LARK_SKILL_UNAVAILABLE`**，明确依赖的是 `lark-sheets` skill。
10. **新增 `evals/evals.json`**：覆盖 Sheets 后端、字段元数据子表、自动创建日期行、公式字段跳过、BMI 静态写入等场景。

---

### v3.0.7 — 2026-08-05

**更新类型**：优化 + 修复

**涉及文件**：
- `skills/sync-xunji/SKILL.md`
- `knowledge/xunji-api-guide.md`
- `skills/init/SKILL.md`
- `CHANGELOG.md`

**内容**：

借鉴「技能桥接模式」对讯记依赖的 4 项优化（用户已批准）：

1. **新增职责边界声明（禁止越界）**：sync-xunji 明文桥接三原则（不直连接口 / 不持有凭证 / 只桥接「检测安装 → 调用 → 接收结果」）；用户提出讯记领域操作需求时引导使用讯记 skill，本技能禁止代劳；讯记数据缺失禁止估算、禁止编造；三个讯记 skill 两两独立
2. **修复依赖路径写法错位（P1）**：依赖表原写 `knowledge/skills/xunji-*/SKILL.md`（本技能包内部路径），与「讯记为外部独立安装 skill」的事实矛盾，包内也无此目录——按此路径检测会永远找不到。改为按技能名检测运行环境中的安装状态，明文「不在本技能包内查找其文件」
3. **清理 sync-xunji 与 xunji-api-guide 的双写残留**：调用时机表、依赖 skill 表、数据质量标记、错误处理模板四处逐字双写，统一以 xunji-api-guide.md 为唯一权威，sync-xunji 只保留执行流程 + 单行引用（延续 v3.0.1 的单一权威原则）
4. **init 讯记检测节补强**：新增已安装时的就位告知；明文初始化检测只用于告知状态，实际同步由 sync-xunji 现场重新检测

附带闭环修正：sync-xunji 执行流程补「写入必须经 write-verify 统一入口」（对齐主 SKILL.md 的写入唯一入口架构，原文件遗漏）。

---

## 更新记录

<!-- 请在下方添加新的更新记录，每次更新都要追加，不要删除旧记录 -->

### v3.0.0 — 2026-07-26

**更新类型**：重构 + 优化

**涉及文件**：
- `SKILL.md`
- `CHANGELOG.md`
- `skills/init/SKILL.md`
- `skills/collect-data/SKILL.md`（新增，原 `skills/daily-poll/SKILL.md` 拆分）
- `skills/query-data/SKILL.md`（新增）
- `skills/write-verify/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `knowledge/routing-rules.md`（新增）
- `knowledge/polling-rules.md`
- `knowledge/field-guide.md`
- `knowledge/sleep-rules.md`（新增）
- `knowledge/training-day-rules.md`（新增）
- `knowledge/target-display-guide.md`
- `knowledge/xunji-api-guide.md`
- `evals/evals.json`

**内容**：

1. **重构模块结构**
   - 将 `skills/daily-poll/SKILL.md` 拆分为：
     - `skills/collect-data/SKILL.md`：负责每日轮询、补数据、回复录入
     - `skills/query-data/SKILL.md`：负责查看数据，只读不写
   - 各子模块职责单一，便于独立测试和维护

2. **统一反馈协调器**
   - `SKILL.md` 承担反馈协调器角色
   - 触发时统一发送：`🏃 健身追踪技能已激活，正在连接数据...`
   - 每个子模块进入时发送专业简洁的状态反馈
   - 操作完成后统一发送完成反馈

3. **更新触发反馈用语**
   - 旧：`🏃 已触发健身追踪技能，正在处理数据...`
   - 新：`🏃 健身追踪技能已激活，正在连接数据...`

4. **统一错误处理**
   - 新增错误码体系：`CONFIG_MISSING`、`TABLE_NOT_FOUND`、`RECORD_NOT_FOUND`、`LARK_CLI_UNAVAILABLE`、`FIELD_WRITE_FAILED`、`INVALID_OPTION`、`XUNJI_UNAVAILABLE`
   - 所有错误由 `SKILL.md` 汇总输出，格式统一为：错误描述 + 原因 + 操作 + 影响

5. **统一子模块返回格式**
   - 所有子模块返回：`status`、`module`、`message`、`data`、`errors`
   - 支持状态：`success`、`partial`、`failed`、`needs_user_input`

6. **拆分知识库**
   - 将 `knowledge/polling-rules.md` 中混杂的内容拆分为：
     - `knowledge/routing-rules.md`：触发与路由
     - `knowledge/polling-rules.md`：时段与 description 规范
     - `knowledge/sleep-rules.md`：睡眠数据归属
     - `knowledge/training-day-rules.md`：训练日/休息日 + 碳水循环

7. **修复 evals.json 矛盾**
   - eval-12：description 缺失时改为"用字段名继续轮询，不停止"
   - eval-6：查询模式改为"可用 record 自带 field_id_list，不强制 field-list"
   - 新增 `query-data` 模块测试用例
   - 新增子模块状态反馈断言
   - 新增统一错误码格式断言

---

### v2.0.5 — 2026-07-19

**更新类型**：优化

**涉及文件**：
- `knowledge/field-guide.md`

**内容**：
- 新增"两种模式的 field-list 调用规则"章节
- 查询模式：允许用 record 自带 field_id_list，减少一次 API 调用
- 写入模式：必须调用 field-list 确认选项和类型（不变）
- 新增备选方案说明

---

### v2.0.4 — 2026-07-19

**更新类型**：修复

**涉及文件**：
- `skills/init/SKILL.md`

**内容**：
- 修复备选方案代码：api GET 返回结构是 `{data: {items: [...]}}`，需 `response.data.items`
- 修复需加 `--format json` 才能 JSON.parse
- 字段名用 bracket notation 避免歧义

---

### v2.0.3 — 2026-07-19

**更新类型**：修复

**涉及文件**：
- `SKILL.md`
- `skills/daily-poll/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/init/SKILL.md`
- `knowledge/polling-rules.md`
- `knowledge/xunji-api-guide.md`
- `config/bitable-schema.md`
- `config/user-profile-schema.md`
- `CHANGELOG.md`

**内容**：

采纳审查反馈的18项修复：

1. **description 空值处理三处矛盾**：统一为"用字段名本身，不停止"
2. **碳水循环训练日推算公式缺失**：补充根据每周训练频率和固定训练日推算的逻辑
3. **两种表创建规则矛盾**：明确每日记录表需预先创建行，用户配置表可自动创建
4. **writeDailyRecord 语义矛盾**：改为"记录不存在则告知用户手动创建"
5. **碳水循环逻辑三处重复**：统一引用 polling-rules.md
6. **数据来源优先级三处重复**：统一引用 xunji-api-guide.md
7. **Obsidian 后端无操作文档**：补充 ObsidianStore 配置格式
8. **week number 与 ISO 8601 差异未说明**：补充注意事项
9. **批量字段处理顺序未定义**：明确先写成功的，最后汇总告知
10. **技能估算保底机制无细节**：补充营养/训练/身体数据的估算规则
11. **格式示例缺少 unit**：已确认示例正确
12. **字段类型与 init 不一致**：统一为"文本"存储
13. **cron 配置格式黑盒**：补充 fitness.polling_schedule 格式说明

---

### v2.0.2 — 2026-07-19

**更新类型**：修复 + 优化

**涉及文件**：
- `SKILL.md`
- `skills/daily-poll/SKILL.md`
- `skills/write-verify/SKILL.md`
- `skills/init/SKILL.md`
- `knowledge/polling-rules.md`
- `CHANGELOG.md`

**内容**：

采纳实际项目技能反馈的8项优化：

1. **禁止 create 新行规则**：飞书表预先有当天空行，技能只写入字段。记录不存在时告知用户先去飞书手动创建
2. **字段截断检测**：复查时对比字段数量，截断时换工具重试，仍截断告知用户数据异常
3. **写入前当前值检查**：字段已有值时必须询问用户确认才能覆盖，禁止静默覆盖
4. **换工具重试机制**：重试时切换工具（lark-cli ↔ feishu_bitable_update_record）
5. **lark-cli 失效备选方案**：+record-search 失效时用 api GET 拉全部记录 + node 内存过滤
6. **睡眠数据归属规则**：入睡时间统一记录在起床日期那行，"昨晚"语义范围定义（前一天 18:00 - 当天 06:00）
7. **description 为空时策略**：有 description 用 description，没有则用字段名，不停止轮询
8. **批量字段逐个验证**：多字段时逐字段独立写入和验证，每个字段独立汇总

---

### v2.0.1 — 2026-07-19

**更新类型**：修复 + 优化

**涉及文件**：
- `SKILL.md`
- `skills/init/SKILL.md`
- `skills/daily-poll/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `skills/write-verify/SKILL.md`
- `knowledge/polling-rules.md`
- `knowledge/field-guide.md`
- `knowledge/xunji-api-guide.md`
- `knowledge/target-display-guide.md`
- `config/bitable-schema.md`
- `config/user-profile-schema.md`
- `CHANGELOG.md`（新增）

**内容**：
- 修复子技能 description 字段导致 OpenClaw 误注册问题（删除所有子技能的 description 字段）
- 修复 init 子技能缺少 lark-cli 命令验证问题
- 修复 polling-rules 和 daily-poll 硬编码字段名问题，改为动态字段读取
- 修复 daily-poll 缺少 fields_failed 失败处理分支问题
- 优化 DataStore 接口说明，增加 AI 实现指南
- 优化 init 子技能，增加用户配置表自动创建步骤
- 新增 CHANGELOG.md 更新日志文件
- 新增 SKILL.md 更新日志规则
- 所有子技能改为内部模块，不注册为独立技能
- bitable-schema.md 改为参考模板，强调实时读取

---

### v2.0.0 — 2026-07-19

**更新类型**：初始版本

**涉及文件**：
- `SKILL.md`
- `skills/init/SKILL.md`
- `skills/daily-poll/SKILL.md`
- `skills/sync-xunji/SKILL.md`
- `skills/write-verify/SKILL.md`
- `knowledge/polling-rules.md`
- `knowledge/field-guide.md`
- `knowledge/xunji-api-guide.md`
- `knowledge/target-display-guide.md`
- `config/bitable-schema.md`
- `config/user-profile-schema.md`

**内容**：
- 初始版本 v2.0.0 发布
- 从 v3.6.0 升级而来
- 新增 DataStore 数据存储抽象层
- 新增 4 个子技能模块：init、daily-poll、sync-xunji、write-verify
- 支持飞书Bitable / local_json / Obsidian 三种后端
- 采用动态字段读取，不硬编码字段名
- 所有子技能无 description 字段，作为内部模块调用
- 支持碳水循环展示
- 支持讯记数据可选填充（不覆盖用户数据）
- 写入后复查验证机制
- 调整信号 JSON Schema 格式定义