# 流程模型规范（Schema 2.0）

## 顶层结构

```json
{
  "schema_version": "2.0",
  "company": "公司名称",
  "confirmation": {
    "status": "confirmed",
    "scope_summary": "用户确认的资料口径、范围和流程边界摘要"
  },
  "process": {
    "number": "03",
    "name": "销售订单审核",
    "status": "draft",
    "summary": "流程范围",
    "business_object": "销售订单",
    "trigger": "业务员提交销售订单",
    "end_state": "订单审核完成并进入待履约状态",
    "boundary_reason": "围绕同一份销售订单完成审核；仓储履约为下游流程"
  },
  "nodes": [],
  "pending_questions": [],
  "sources": []
}
```

### 确认状态

- `confirmation.status`：`pending` 或 `confirmed`。
- `scope_summary`：记录用户确认后的资料口径和边界，不记录模型猜测。
- `validate` 允许检查 `pending` 模型；`render` 只接受 `confirmed`。
- `process.status`：`draft` 或 `confirmed`，表示业务规则是否仍有待确认项，与生成前确认门是两件事。

### 流程边界字段

`business_object`、`trigger`、`end_state` 和 `boundary_reason` 都是必填文字。资料未说明终点时可以如实写“资料未说明”，同时建立具体问题；不得编造终态。

## 节点类型

| 类型 | 编号 | 必填字段 | 含义 |
|---|---|---|---|
| `start` | `S01` | `label`, `next` | 流程触发事件 |
| `action` | `A01` | `owner`, `label`, `next` | 一个主体执行的一个业务动作 |
| `decision` | `D01` | 见下方 | 改变后续路径的判断 |
| `join` | `J01` | `label`, `next` | 多条路径的视觉汇合，不是业务动作 |
| `unresolved` | `U01` | `label`；已知时写 `owner` | 决策分支去向确实未知的中性终点 |
| `terminal` | `T01` | `label` | 已明确的业务终态 |

动作节点不得把多个主体或多个动作合并。`填写订单并关联档案` 应拆成两个 `action`。

## 决策节点

```json
{
  "id": "D01",
  "type": "decision",
  "owner": "商务主管",
  "title": "账期审核",
  "question": "客户账期是否符合公司规则？",
  "inputs": ["客户类型", "申请账期", "账期规则"],
  "criteria": [
    {
      "text": "新客户现款现货的适用范围待确认",
      "status": "unresolved",
      "evidence": "资料同时出现新客户现款现货和默认 21 天"
    }
  ],
  "branches": [
    {
      "label": "符合规则",
      "condition": "客户类型和申请账期符合现行规则",
      "target": "D02",
      "status": "confirmed",
      "primary": true
    },
    {
      "label": "不符合规则",
      "condition": "账期适用规则待确认",
      "target": "U01",
      "status": "unresolved",
      "primary": false
    }
  ]
}
```

每个决策至少两个分支，也可以有三、四个或更多分支。每个分支都必须有非空 `condition` 和有效 `target`。`primary` 仅用于稳定排序和兼容模型，不表示其他分支不重要；HTML 必须显示全部分支。

## 事实状态

| 状态 | 使用条件 | 写法要求 |
|---|---|---|
| `confirmed` | 输入文字或用户确认直接支持 | `evidence` 指向依据 |
| `inferred` | 仅由明确规则做逻辑补全 | 明示推断，不冒充现状 |
| `unresolved` | 输入缺失、含糊或冲突 | 建立问题；必要时以 `Uxx` 结束分支 |

资料缺少中间环节时，先在确认前对话中提问，不能立即创建 `Uxx` 或猜测动作。`Uxx` 只在用户允许生成仍有未知去向的草案时使用。

## 待确认问题

```json
{
  "id": "Q01",
  "text": "大额订单的金额阈值是多少？",
  "related_nodes": ["D04"]
}
```

- ID 使用 `Q01` 形式且唯一。
- `text` 必须是业务人员可以直接回答的问题。
- `related_nodes` 至少包含一个已存在的节点。
- 问题只描述缺少的事实，不附带优化建议。

## 完整性要求

- 节点 ID 唯一，目标 ID 存在。
- 只能有一个 `start`，至少有一个 `terminal`。
- 所有节点从起点可达；不允许未声明循环。
- 所有动作都有主体。
- 每个决策至少两个分支，恰好一个 `primary=true`。
- 问题 ID 唯一且关联节点有效。
- `confirmed` 流程不能包含非确认状态、`Uxx` 或待确认问题。
