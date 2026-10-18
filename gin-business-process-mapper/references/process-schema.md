# 流程数据结构

JSON 是 Markdown 流程树的唯一数据源。

## 流程对象

必填：`process_id`、`process_name`、`purpose`、`scope_start`、`scope_end`、`participants`、`systems_and_channels`、`nodes`、`edges`、`scenes`、`open_questions`、`future_expectations`、`sources`、`version`、`status`。

`status` 只能是 `draft` 或 `confirmed`。

## 节点对象

必填字段：

| 字段 | 含义 |
|---|---|
| `id` | 连续编号，如 `N01` |
| `name` | 业务人员能理解的动作名称 |
| `kind` | `start` / `action` / `decision` / `end` |
| `business_fact` | 用户确认的现状事实 |
| `actor_role` | 岗位角色，不记录人名 |
| `execution_mode` | `manual` / `automatic` / `assisted` |
| `carrier` | `system` / `chat` / `email` / `spreadsheet` / `paper` / `onsite` / `other` |
| `carrier_name` | 具体系统或工具名称；不知道可为空字符串 |
| `entry_or_signal` | 执行者如何知道该处理 |
| `business_action` | 实际动作 |
| `software_location` | 系统和页面位置；纯线下动作可为空 |
| `software_operation` | 选择、填写、上传、提交等实际界面动作；未知可为空 |
| `interface_implications` | 从事实推导的软件含义数组 |
| `inputs` / `outputs` | 输入和输出数组 |
| `completion_signal` | 如何判断完成 |
| `state_before` / `state_after` | 已确认或推导的状态，可为空 |
| `rules` | 已确认规则数组 |
| `exceptions` | 节点内异常数组 |
| `evidence_status` | `confirmed` / `inferred` / `unknown` |
| `evidence_refs` | 对话或文件来源编号数组 |

节点整体为 `confirmed` 时，`business_fact` 必须有 `evidence_refs`。推导出来的界面能力仍应在文字中标为“软件实现含义”，不能因节点已确认而变成用户原话。

决策节点额外必填 `decider_role`、非空 `criteria` 和 `fallback`。每个决策节点至少有两条出边，每条出边的 `condition` 必须非空且互不重复。

## 连线对象

必填：`id`、`from`、`to`、`label`、`condition`、`kind`、`evidence_status`、`evidence_refs`。

`kind` 只能是 `normal`、`decision`、`exception`、`timeout`、`cancel` 或 `rework`。每条边必须引用已存在节点。

普通边不得形成循环。真实存在的返工和取消回路分别使用 `rework`、`cancel`，渲染时从主流程下方返回。

## 场景对象

必填：`id`、`name`、`type`、`owner_roles`、`edge_ids`、`boundary_rule`。

`type` 只能是 `main`、`exception` 或 `variant`，且至少有一个主场景。

场景按完整业务情境划分，不按某一条决策分支划分。场景的 `edge_ids` 必须组成一棵完整流程树：只要场景包含某个决策节点，就必须包含该节点在全流程数据中的全部出边，包括正常、异常、超时、取消和返工出口。不得把同一决策的出口拆到不同场景。不同业务情境需要复用共同路径时，同一连线可以出现在多个场景中。

`owner_roles` 只填写岗位角色。`boundary_rule` 用业务语言说明何时进入，以及各叶子分支在哪里闭环、回流或到达已确认的流程边界。

## 证据来源

`sources` 中每项包含 `id`、`type`、`summary`。`type` 可使用 `conversation`、`document`、`screenshot` 或 `confirmation`。只保存完成流程还原所需的摘要，不虚构原文。
