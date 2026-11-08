# 流程模型规范（Schema 3.0）

模型只在用户看过自然语言确认内容并明确允许生成后建立。下面的字段用于记录和校验这一过程，不允许 Agent 自行编造确认回复。

## 确认与流程范围

```json
{
  "schema_version": "3.0",
  "company": "公司名称",
  "confirmation": {
    "status": "confirmed",
    "scope_summary": "用户确认的资料口径和流程范围",
    "presented": {
      "current_facts": ["已向用户复述的当前实际做法"],
      "excluded_goals": ["已说明不纳入现状的预期目标"],
      "process_boundaries": ["本流程的触发、终点、拆分或合并理由"],
      "decisions": ["已向用户确认的关键判断、已知条件与分支去向"]
    },
    "user_reply": "用户实际允许生成的原话",
    "user_reply_source_id": "CHAT_APPROVAL",
    "response_kind": "approval",
    "accepted_unknowns": true
  },
  "process": {
    "number": "03",
    "name": "销售订单审核",
    "status": "draft",
    "business_object": "销售订单",
    "trigger": "业务员提交销售订单",
    "end_state": "审核完成，进入待履约状态",
    "boundary_reason": "围绕同一份订单完成审核；仓储履约独立"
  },
  "source_materials": [],
  "evidence": [],
  "nodes": [],
  "pending_questions": [],
  "sources": []
}
```

- `presented` 是已向用户展示的内容，不是事后补写的分析；四个数组必须存在。没有目标或决策时用空数组并在对话中说明。存在决策却未展示决策内容时不能输出。
- `user_reply` 保留真实回复，必须在对应的 `source_materials` 中找到。仅纠正公司名、角色或事实时，`response_kind` 为 `correction`，确认状态仍为 `pending`；纠正后又明确说“按这个生成”才是 `approval`。
- `accepted_unknowns` 表示用户是否允许带着未回答的问题生成草案。确认范围不等于确认所有业务规则。
- `confirmation.status` 控制是否允许生成；`process.status` 表示业务内容是否仍有未知。前者已确认、后者为 `draft` 是正常情况。
- `end_state` 未说明时照实记录“资料未说明”，不补写完成状态。业务对象、触发或边界缺失也应明确记录并提出问题。
- `sources` 是输出底部显示的来源名称；`source_materials` 是核对引用所需的原文。不要把私密原文全部写入面向读者的 Markdown。

## 原文证据

```json
{
  "source_materials": [
    {"id": "CHAT01", "text": "现在销售填订单，随后交主管审核。以后希望系统自动审核。"},
    {"id": "CHAT_APPROVAL", "text": "确认，按这些现状和判断出草案，没讲清的先列问题。"}
  ],
  "evidence": [
    {"id": "E01", "source_id": "CHAT01", "quote": "现在销售填订单，随后交主管审核。", "kind": "current"},
    {"id": "E02", "source_id": "CHAT01", "quote": "以后希望系统自动审核。", "kind": "goal"}
  ]
}
```

`kind` 取值：`current` 当前做法、`goal` 预期目标、`rule` 制度要求、`unclear` 冲突或未知、`user_confirmation` 用户补充确认。

- 每条 `quote` 必须原样出现在对应来源中。不能把总结句冒充原话。
- 动作、实际判断、起点和业务终态使用 `evidence_refs`；顺序连接使用 `next_evidence_refs`；分支使用自己的 `evidence_refs`。两个动作各自有依据，不代表连接也有依据。
- 已确认现状不能仅引用目标、制度或未知说法。制度被证实正在执行时，补录用户确认依据，不篡改原始制度来源。
- **脚本只核对引用存在、来源类型和结构，不能证明原话真正支持了该动作、条件或箭头。** Agent 必须逐项对照原文做语义核对；不得把有引用等同于无编造。

## 节点与连接

| 类型 | 编号示例 | 字段 | 含义 |
|---|---|---|---|
| `start` | `S01` | `label`, `next`, `evidence_refs`, `next_evidence_refs` | 已知触发或资料描述的起点 |
| `action` | `A01` | `owner`, `label`, `next`, `evidence_refs`, `next_evidence_refs` | 一个主体执行一个具体业务动作 |
| `decision` | `D01` | 见下方 | 不同结果改变后续路径的实际判断 |
| `join` | `J01` | `label`, `next`, `next_evidence_refs` | 路径汇合，不新增业务动作 |
| `unresolved` | `U01` | `label` | 未知去向；不是业务完成或失败 |
| `terminal` | `T01` | `label`, `evidence_refs` | 已明确的业务终态 |

动作使用“主体＋动作＋对象”。例如“填写订单并关联档案”拆为两个动作。脚本无法仅凭一个字符串证明动作是否足够具体或单一，仍须语义审查。

`next` 只适用于 `start/action/join`，`branches` 只适用于 `decision`。`terminal/unresolved` 不能携带出边，避免树中出现含糊的出边。

`Uxx` 标签只写“后续去向未确认”等中性内容，完整问题放到页面底部。未知终点无需伪造证据；动作连向未知终点时可使用空的 `next_evidence_refs`，同时给动作与未知终点关联问题。资料没有已知业务终态时，允许所有已描述路径结束于 `Uxx`。

已有依据的实际退回或重新提交：在相应分支上设置 `back_edge: true`；普通动作的 `next` 返回前序步骤时在该动作上设置 `back_edge: true`。返回连接仍须原文证据。未标注的环被拒绝；不能借此删除企业实际回路。

没有关键决策的流程可以只包含动作与终点。不要为得到菱形而把普通核对动作改成判断。

## 决策节点

```json
{
  "id": "D01",
  "type": "decision",
  "owner": "商务主管",
  "title": "账期审核",
  "question": "客户账期是否符合公司规则？",
  "evidence_refs": ["E03"],
  "inputs": ["客户类型", "申请账期"],
  "criteria": [
    {
      "text": "不同客户适用的账期标准待确认",
      "status": "unresolved",
      "evidence": "资料提到审核账期，但没有说明适用标准",
      "evidence_refs": ["E03"]
    }
  ],
  "branches_complete": true,
  "branches": [
    {
      "label": "符合规则",
      "condition": "符合适用账期规则；具体规则待确认",
      "condition_status": "unresolved",
      "target": "D02",
      "target_status": "confirmed",
      "status": "unresolved",
      "evidence_refs": ["E03"],
      "primary": true
    },
    {
      "label": "不符合规则",
      "condition": "不符合适用账期规则；具体规则待确认",
      "condition_status": "unresolved",
      "target": "U01",
      "target_status": "unresolved",
      "status": "unresolved",
      "evidence_refs": ["E03"],
      "primary": false
    }
  ]
}
```

- 完整决策允许 2–N 个分支，每条都写条件和目标。`branches_complete` 缺省为 `true`。资料没有说全时显式设为 `false`，只列有依据的已知分支，允许 0 条、1 条或更多条；同时关联具体待确认问题，流程保持 `draft`。不能为了凑足两个分支补造拒绝、退回或未知互补条件。
- 分支非空时恰好一条 `primary=true`，空数组不设主分支。`primary` 只影响布局，不表示其他分支不重要。
- 已知正在进行某个判断、但所有结果去向均未说明时，保留决策节点作为图中当前描述的末端，`branches=[]`、`branches_complete=false`，缺失信息列在下方问题中。这个节点不是“业务完成”。
- 分开记录条件和去向的状态：可以知道“批准后交给谁”，但不知道“批准标准”。两个状态都为 `confirmed` 时，分支 `status` 才能为 `confirmed`。
- `confirmed`：有直接依据；`unresolved`：缺失、含糊或冲突；`inferred`：推断。推断不能升级成企业事实，必须关联问题并在交付中明确标注。
- 未知标准的 `criteria.evidence_refs` 可以为空；必须保留具体问题，不能编造依据。已知标准必须有现状或用户确认依据。
- 分支引用证明资料确实存在该路径或判断结果。只知道批准路径时，不能把“批准后进入出库”的原文同时引用为“拒绝后退回”的依据；未说出的结果留在问题中，不进入已知分支数组。
- 多个条件之间的“任一／同时”、优先级、是否可并行触发，必须来自资料或用户确认。不能根据排列顺序自行决定。

## 待确认问题与验收

```json
{"id": "Q01", "text": "不符合账期规则时，订单实际交给谁处理？", "related_nodes": ["D01", "U01"]}
```

未知条件、未知去向、未完整描述的分支集合和推断项必须关联问题。问题具体到业务人员可回答的事实，不夹带优化建议。

校验检查：确认记录、原文引用、有效 ID/目标、起点可达、声明的回路、全部分支、未知项对应问题、内容状态一致。`process.status=confirmed` 时不能仍有未知终点、未确认条件、不完整分支集合或问题。

`validate` 可检查确认状态为 `pending` 的临时数据；正式 `render` 和直接调用 `render_files` 都会拒绝尚未取得用户确认的模型，并且不会创建输出目录。仅通过结构校验不代表业务理解正确，交付前仍需原文语义核对和Markdown 阅读验收。

回归样例 `tests/fixtures/sales-order.json` 使用**合成访谈和模拟确认**，只检验技能行为，不充当金华得创的实际公司资料。


## 无法定位先后的已知动作

不要建立第二棵树，也不要为了让节点可达而补造连接。把已有事实写进对应待确认问题的可选 `known_facts` 数组，每项为 `text` 与 `evidence_refs`。事实必须有现状证据；同一问题的 `text` 询问实际接入点或先后，`related_nodes` 指向主树的相关节点。例如：

```json
{"id":"Q01","text":"拍摄视频与交回登记员的先后是什么？","related_nodes":["A09"],"known_facts":[{"text":"技术员会拍摄维修后的质检视频并发给客户；与交回登记员的先后未说明。","evidence_refs":["E_VIDEO"]}]}
```

只在原文证明两个动作先后时才在事实文字里使用“随后”。不要把未知目标、方案或第二个独立流程藏进 `known_facts`。

顺序连接如仅为已展示并获准保留的推断，使用 `next_status: "inferred"`，添加 `next_note`，并关联问题；分支上的 `target_status` 与 `path_note` 同理。短提示必须在树中可见，未知去向仍用 Uxx。`next_note` 或 `path_note` 不能当作真实业务动作。

只接受一个 `process`。阶段名称不控制渲染边界，不能为阶段创建额外起点。生成器从唯一实际起点展开全图，忽略排版阶段过滤。
