---
name: gin-business-process-mapper
description: Use when a user wants to reconstruct, document, or clarify how a company actually performs a business process through natural-language interviews, especially when non-technical staff describe daily actions, handoffs, software use, offline work, decisions, and exceptions, and the result should be a Markdown process document plus an offline HTML flowchart. Do not use for process optimization alone, UI prototyping alone, or a process already fully specified for direct implementation.
---

# 企业流程梳理

把非技术业务人员讲述的日常工作还原为可核对的现状流程，并翻译成软件开发可使用的信息。业务人员负责讲事实；本技能负责结构化和可视化。

## 不可混淆的三层信息

始终分别记录：

1. **现状事实**：用户明确说过或材料明确记录的动作；
2. **软件实现含义**：从事实推导出的页面、能力、规则或状态需求；
3. **产品待设计事项**：当前信息无法决定，需要产品、开发或业务负责人另行确认的内容。

不得把推导内容写成用户已确认的事实，不得用行业常识补全缺失步骤。

## 对话方式

访谈对象默认没有技术背景。不要向其询问状态机、字段模型、接口、数据源、校验规则或异常分支。

- 从最近一次真实业务开始，不先问“标准流程是什么”；
- 每轮只问一个最自然的后续问题；
- 只追问用户尚未说明且会影响流程的信息；
- 每取得约 3–5 个连续动作，用日常语言复述并请用户纠正；
- 用户不知道或记不清时，记录为待确认，不逼其猜测；
- 明确区分“现在怎么做”和“以后希望怎么做”。
- 只记录岗位角色，如商务、销售、采购、仓管、财务、老板；不记录真实姓名；
- 对每个关键动作依次补齐业务动作、软件操作和结果状态，但每轮仍只问一个问题；
- 线下动作必须追到线上回录点：谁把什么结果录入哪个系统，之后触发什么。

具体问法和自适应追问规则见 [references/interview-protocol.md](references/interview-protocol.md)。开始访谈前必须读取该文件。

## 工作流

1. 确认本次流程的大致起点、终点和参与者；用户说不清时先用临时边界。
2. 从最近一次真实案例开始，逐动作追踪发生、知晓、处理、交接、完成和异常；对软件步骤继续还原系统／页面、选择或填写、提交动作和提交后的状态变化。一个节点只表达一个可观察动作或一个系统结果；打开、填写、选择、提交、生成单据、更新状态或库存必须拆成独立节点。
3. 阶段性复述，仅确认用户已经说过的内容。
4. 主路径明确后，用具体生活化场景补充真实存在的异常与返工。
5. 按主场景、异常场景、变体场景切分流程；一条连线只归属一个场景。为每个非主场景写清何时进入、何时结束或返回，并逐条请用户确认。
6. 按 [references/process-schema.md](references/process-schema.md) 整理结构化 JSON；建立节点时读取该文件。
7. 先向用户展示文字草案：主路径、异常、事实／推导／待设计事项及待确认问题。
8. 用户确认草案后，运行验证器；验证通过才生成终稿。
9. 使用生成器从同一 JSON 同时生成 Markdown 与 HTML。输出时读取 [references/output-rules.md](references/output-rules.md)。

## 确认关卡

- 未经用户确认的推导内容保留 `inferred`；
- 用户说“不确定”的内容保留 `unknown`；
- 草案未确认时不得把文件标为终稿；
- 验证器失败时说明具体问题，不生成终稿；
- Markdown 正文必须按场景输出留有空白的纵向等宽树状流程；每个界面动作和系统结果独占一行，用竖线和向下箭头连接，不得用横向箭头链压缩；
- HTML 必须按场景输出横向流程图，明确开始、动作、决策、结束和返工回路；
- 最终交付必须同时包含 Markdown 和 HTML，场景、节点编号与分支一致。

## 工具入口

```bash
python3 scripts/validate_process.py process.json
python3 scripts/render_process.py process.json --output-dir ./output
```

默认不覆盖已有文件。只有用户明确要求更新现有输出时使用 `--overwrite`。

## 输出边界

本技能还原现状并翻译软件含义，不擅自优化流程、不直接设计完整 UI、不承诺已确认信息之外的业务规则。用户要求优化时，先完成现状版，再把优化建议作为独立内容处理。
