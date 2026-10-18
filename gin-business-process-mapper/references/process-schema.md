# 流程数据结构

JSON 是 Markdown 与 HTML 的唯一数据源。

## 流程对象

必填：`process_id`、`process_name`、`purpose`、`scope_start`、`scope_end`、`participants`、`systems_and_channels`、`nodes`、`edges`、`open_questions`、`future_expectations`、`sources`、`version`、`status`。

`status` 只能是 `draft` 或 `confirmed`。

## 节点对象

必填字段：

| 字段 | 含义 |
|---|---|
| `id` | 连续编号，如 `N01` |
| `name` | 业务人员能理解的动作名称 |
| `business_fact` | 用户确认的现状事实 |
| `actor` | 实际执行者 |
| `execution_mode` | `manual` / `automatic` / `assisted` |
| `carrier` | `system` / `chat` / `email` / `spreadsheet` / `paper` / `onsite` / `other` |
| `carrier_name` | 具体系统或工具名称；不知道可为空字符串 |
| `entry_or_signal` | 执行者如何知道该处理 |
| `business_action` | 实际动作 |
| `interface_implications` | 从事实推导的软件含义数组 |
| `inputs` / `outputs` | 输入和输出数组 |
| `completion_signal` | 如何判断完成 |
| `state_before` / `state_after` | 已确认或推导的状态，可为空 |
| `rules` | 已确认规则数组 |
| `exceptions` | 节点内异常数组 |
| `evidence_status` | `confirmed` / `inferred` / `unknown` |
| `evidence_refs` | 对话或文件来源编号数组 |

节点整体为 `confirmed` 时，`business_fact` 必须有 `evidence_refs`。推导出来的界面能力仍应在文字中标为“软件实现含义”，不能因节点已确认而变成用户原话。

## 连线对象

必填：`from`、`to`、`label`、`condition`、`kind`、`evidence_status`、`evidence_refs`。

`kind` 只能是 `normal`、`decision`、`exception`、`timeout`、`cancel` 或 `rework`。每条边必须引用已存在节点。

## 证据来源

`sources` 中每项包含 `id`、`type`、`summary`。`type` 可使用 `conversation`、`document`、`screenshot` 或 `confirmation`。只保存完成流程还原所需的摘要，不虚构原文。
