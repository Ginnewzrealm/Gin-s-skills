# 流程模型规范

## 顶层结构

```json
{
  "schema_version": "1.0",
  "company": "公司名称",
  "process": {
    "number": "03",
    "name": "销售订单",
    "status": "draft",
    "summary": "流程范围"
  },
  "nodes": [],
  "pending_questions": [],
  "sources": []
}
```

- `process.status`：`draft` 或 `confirmed`。
- `sources`：原始文字的文件名、访谈名称或“用户本轮提供的纯文字”。不得填写不存在的来源。
- `pending_questions`：业务人员可以直接回答的问题。缺少金额阈值时问“阈值是多少”，不要只写“金额待确认”。

## 节点类型

| 类型 | 编号 | 必填字段 | 含义 |
|---|---|---|---|
| `start` | `S01` | `label`, `next` | 流程触发事件 |
| `action` | `A01` | `label`, `next`；已知时写 `owner` | 角色实际执行的动作 |
| `decision` | `D01` | 见下方 | 会改变后续路径的判断 |
| `unresolved` | `U01` | `label`；已知时写 `owner` | 资料不足，当前无法继续还原的路径 |
| `terminal` | `T01` | `label` | 已明确的业务终态 |

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
      "evidence": "输入同时出现新客户现款现货和默认 21 天"
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
      "condition": "具体适用规则待确认",
      "target": "U01",
      "status": "unresolved",
      "primary": false
    }
  ]
}
```

`question` 是决策问题，`inputs` 是做判断前需要看到的信息，`criteria` 是如何判断，`branches` 是判断结果对应的路径。四者不可互相替代。

## 事实状态

| 状态 | 使用条件 | 写法要求 |
|---|---|---|
| `confirmed` | 输入文字直接支持 | `evidence` 指向原文事实 |
| `inferred` | 只是对明确规则做逻辑补全 | 明示“推断”，不得冒充企业规则 |
| `unresolved` | 输入缺失、含糊或冲突 | 建立问题；必要时以 `Uxx` 结束路径 |

例：原文只说“金额大于 X 万要老板审批”。“大于 X 万 → 审批”可标 `confirmed`；“小于或等于 X 万 → 不审批”虽是自然补集，仍应标 `inferred`，除非原文明确说明。

## 主线规则

每个决策恰好一个分支设置 `primary=true`。主线的作用是让复杂公司流程在一张纵向图中稳定呈现；其他分支显示在右侧。选择最能代表常规推进或最适合阅读的路径，不得把主线解释成唯一正确路径。

## 完整性要求

- 节点 ID 唯一，目标 ID 必须存在。
- 只能有一个 `start`，至少有一个 `terminal`。
- 不允许出现未声明的循环；重复办理应拆成明确节点，或在文字中先标待确认。
- 从起点出发的所有节点必须可达。
- `confirmed` 模型不能包含 `unresolved` 节点、非确认状态或待确认问题。
