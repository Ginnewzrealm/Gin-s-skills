# 企业流程梳理 Skill v2 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将企业流程梳理 Skill 升级为以真实场景为中心、能区分线上软件操作与线下人工动作，并同时生成对齐的 Markdown 场景树和离线 HTML 流程图。

**架构：** 继续使用一份 JSON 作为唯一数据源。验证器负责结构、证据、场景覆盖和循环规则；渲染器按场景分别生成 Markdown 树与 SVG 流程图，返工边不参与前向层级计算，避免循环导致布局不终止。

**技术栈：** Python 3 标准库、`unittest`、单文件 HTML/CSS/SVG、Markdown。

---

## 文件结构

- 修改 `gin-business-process-mapper/tests/fixtures/order_process.json`：迁移到 v2 数据结构并提供线上、线下、决策和场景样本。
- 创建 `gin-business-process-mapper/tests/fixtures/rework_process.json`：提供合法返工循环的回归样本。
- 修改 `gin-business-process-mapper/tests/test_validator.py`：覆盖 v2 字段、决策约束、场景覆盖、证据与模糊表达警告。
- 修改 `gin-business-process-mapper/tests/test_renderer.py`：覆盖 Markdown 场景顺序、树线、角色、软件操作、HTML 图形和循环终止。
- 修改 `gin-business-process-mapper/scripts/validate_process.py`：实现 v2 错误与警告检查。
- 修改 `gin-business-process-mapper/scripts/render_process.py`：实现场景树、附录、场景 SVG 与安全布局。
- 修改 `gin-business-process-mapper/assets/process-report-template.html`：增加场景标签、菱形样式、图例和打印展开规则。
- 修改 `gin-business-process-mapper/SKILL.md`：明确面向非技术人员的三层追问与双格式输出要求。
- 修改 `gin-business-process-mapper/references/interview-protocol.md`：增加软件操作、状态变化和线下回录点问法。
- 修改 `gin-business-process-mapper/references/process-schema.md`：记录 v2 JSON 字段和约束。
- 修改 `gin-business-process-mapper/references/output-rules.md`：固定 Markdown 场景树与 HTML 图形规则。
- 修改 `gin-business-process-mapper/evals/evals.json`：增加软件界面流转、部分不合格和返工场景。

### 任务 1：迁移 v2 样本并定义验证契约

**文件：**
- 修改：`gin-business-process-mapper/tests/fixtures/order_process.json`
- 创建：`gin-business-process-mapper/tests/fixtures/rework_process.json`
- 修改：`gin-business-process-mapper/tests/test_validator.py`

- [ ] **步骤 1：把样本节点迁移为 v2 字段**

每个节点增加 `kind`、`actor_role`、`software_location`、`software_operation`；删除 `actor`。每条连线增加连续的 `id`。决策节点写入：

```json
{
  "kind": "decision",
  "decider_role": "客服",
  "criteria": ["商品、收货信息和备注均无异常"],
  "fallback": "无法判断时转交老板确认"
}
```

流程增加 `scenes`：

```json
[
  {
    "id": "SC01",
    "name": "正常接单",
    "type": "main",
    "owner_roles": ["客服"],
    "edge_ids": ["E01", "E02", "E04"],
    "boundary_rule": "新订单生成后进入；订单签收后结束"
  },
  {
    "id": "SC02",
    "name": "订单信息异常确认",
    "type": "exception",
    "owner_roles": ["客服"],
    "edge_ids": ["E03"],
    "boundary_rule": "订单信息存在问题时进入；客户回复后返回订单处理"
  }
]
```

- [ ] **步骤 2：编写失败的验证测试**

增加测试，分别断言缺少决策依据、决策出边不足、重复条件、场景引用不存在的连线、终稿连线未被场景覆盖、普通边构成循环会报错；合法 `rework` 回路不会报错。

```python
def test_confirmed_process_requires_every_edge_in_a_scene(self):
    data = copy.deepcopy(self.fixture)
    data["scenes"][0]["edge_ids"].remove("E01")
    self.assertTrue(any("未归属场景" in error for error in validate(data)))
```

- [ ] **步骤 3：运行验证测试并确认红灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_validator -v`

预期：新增测试因 v2 字段和约束尚未实现而失败。

- [ ] **步骤 4：Commit 测试和样本**

```bash
git add gin-business-process-mapper/tests
git commit -m "test: define business process schema v2"
```

### 任务 2：实现 v2 验证器与循环规则

**文件：**
- 修改：`gin-business-process-mapper/scripts/validate_process.py`
- 测试：`gin-business-process-mapper/tests/test_validator.py`

- [ ] **步骤 1：更新字段和枚举**

定义 `NODE_KINDS = {"start", "action", "decision", "end"}`、`SCENE_TYPES = {"main", "exception", "variant"}`，并将字段集合更新为 v2。仅 `kind == "decision"` 的节点强制要求 `decider_role`、`criteria`、`fallback`。

- [ ] **步骤 2：实现决策、场景、证据和循环验证**

普通前向边集合排除 `rework` 与 `cancel`。用深度优先搜索检查该集合是否成环：

```python
def _has_cycle(node_ids, edges):
    outgoing = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if edge.get("kind") not in {"rework", "cancel"}:
            outgoing.setdefault(edge.get("from"), []).append(edge.get("to"))
    visiting, visited = set(), set()
    def visit(node_id):
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        if any(visit(target) for target in outgoing.get(node_id, [])):
            return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False
    return any(visit(node_id) for node_id in node_ids)
```

- [ ] **步骤 3：增加表达质量警告接口**

新增 `lint(data)`，检查 `business_action`、`criteria`、`fallback` 和 `boundary_rule` 是否只包含“处理、跟进、弄一下、看情况”等模糊表达。`validate()` 继续只返回阻塞错误，CLI 分别打印 `ERROR:` 与 `WARNING:`。

- [ ] **步骤 4：运行验证测试确认绿灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_validator -v`

预期：全部通过。

- [ ] **步骤 5：Commit**

```bash
git add gin-business-process-mapper/scripts/validate_process.py gin-business-process-mapper/tests/test_validator.py
git commit -m "feat: validate business process schema v2"
```

### 任务 3：实现 Markdown 场景树

**文件：**
- 修改：`gin-business-process-mapper/tests/test_renderer.py`
- 修改：`gin-business-process-mapper/scripts/render_process.py`

- [ ] **步骤 1：编写失败的 Markdown 测试**

断言主场景先于异常场景；输出包含 `场景一`、岗位角色、`◇`、`├─`、`└─`、软件位置、软件操作和状态变化；不再包含重复的“产品待设计事项”和“待确认问题”章节。

```python
def test_markdown_renders_scenario_tree_with_software_operations(self):
    output = render_markdown(self.data)
    self.assertLess(output.index("正常接单"), output.index("订单信息异常确认"))
    for text in ["◇", "├─", "└─", "岗位角色", "软件操作", "状态变化"]:
        self.assertIn(text, output)
```

- [ ] **步骤 2：运行单项测试确认红灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_renderer.RenderMarkdownTests -v`

预期：场景树断言失败。

- [ ] **步骤 3：实现按场景遍历和宽松树形排版**

建立节点、出边和场景边索引。主场景、异常场景、变体场景依次输出。每张卡片使用等宽代码块并保留分支间空行；节点文案由岗位角色、软件位置、软件操作和状态结果组成。返工边输出“回到「节点名称」”，不递归进入已访问节点。

- [ ] **步骤 4：保留技术附录并合并待确认章节**

正文保持业务可读；附录列出节点 ID、证据状态、输入输出和实现含义。未来期望单独标记为“不属于现状流程”。

- [ ] **步骤 5：运行 Markdown 测试确认绿灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_renderer.RenderMarkdownTests -v`

预期：全部通过。

- [ ] **步骤 6：Commit**

```bash
git add gin-business-process-mapper/scripts/render_process.py gin-business-process-mapper/tests/test_renderer.py
git commit -m "feat: render scenario-first markdown flows"
```

### 任务 4：修复循环布局并升级 HTML 场景图

**文件：**
- 修改：`gin-business-process-mapper/tests/test_renderer.py`
- 修改：`gin-business-process-mapper/scripts/render_process.py`
- 修改：`gin-business-process-mapper/assets/process-report-template.html`

- [ ] **步骤 1：编写失败的 HTML 和循环回归测试**

加载 `rework_process.json`，断言 `_layout_nodes` 能返回；断言 HTML 包含场景切换按钮、`decision-node` 菱形类、岗位角色、软件操作以及打印时展示全部场景的 CSS。

- [ ] **步骤 2：运行测试确认红灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_renderer.RenderHtmlTests -v`

预期：旧布局在返工循环上不能完成，场景与菱形断言失败。

- [ ] **步骤 3：实现安全层级布局**

层级计算只使用不属于 `rework`、`cancel` 的边，并在每个节点完成后固定层级；返工和取消边从图底部绕回，不参与层级更新。

- [ ] **步骤 4：按场景生成 SVG 与控件**

为每个场景生成一个 `<section class="scene-panel">`。决策节点使用旋转方形或 `<polygon>` 绘制菱形；开始/结束使用大圆角；动作节点使用矩形。标签按钮通过内联 JavaScript切换可见场景，打印媒体规则展示全部场景。

- [ ] **步骤 5：运行 HTML 测试确认绿灯**

运行：`python3 -m unittest gin-business-process-mapper.tests.test_renderer.RenderHtmlTests -v`

预期：全部通过且返工样本在测试时限内完成。

- [ ] **步骤 6：Commit**

```bash
git add gin-business-process-mapper/scripts/render_process.py gin-business-process-mapper/assets/process-report-template.html gin-business-process-mapper/tests/test_renderer.py
git commit -m "feat: render scene-based html process maps"
```

### 任务 5：更新 Skill 访谈协议、结构说明与评测

**文件：**
- 修改：`gin-business-process-mapper/SKILL.md`
- 修改：`gin-business-process-mapper/references/interview-protocol.md`
- 修改：`gin-business-process-mapper/references/process-schema.md`
- 修改：`gin-business-process-mapper/references/output-rules.md`
- 修改：`gin-business-process-mapper/evals/evals.json`

- [ ] **步骤 1：增加三层追问协议**

明确依次追问“业务动作 → 软件操作 → 结果状态”，但仍一次只问一个生活化问题。在线下动作之后追问“谁把结果录回哪个系统”。角色只允许岗位称谓，不记录人名。

- [ ] **步骤 2：同步 v2 数据和输出规则**

文档必须与代码一致使用 `actor_role`、`software_location`、`software_operation`、`kind`、`scenes` 和连线 `id`，并说明 Markdown 与 HTML 均为正式交付物。

- [ ] **步骤 3：增加行为评测**

加入“采购入库部分不合格”场景，期望技能继续追问 ERP 页面、实收数量、提交动作、库存变化、采购联系供应商以及退货单和发货状态，禁止只输出“良品先入库、不良品退换”。

- [ ] **步骤 4：运行内容核对**

运行：`rg -n 'actor_names|真实姓名|良品先入库|系统里处理一下' gin-business-process-mapper`

预期：不出现人名字段；示例中的模糊表达仅出现在反例或追问说明中。

- [ ] **步骤 5：Commit**

```bash
git add gin-business-process-mapper/SKILL.md gin-business-process-mapper/references gin-business-process-mapper/evals/evals.json
git commit -m "docs: teach software-aware process interviews"
```

### 任务 6：端到端验证与 GitHub 更新

**文件：**
- 验证：`gin-business-process-mapper/`

- [ ] **步骤 1：运行 Skill 结构验证**

运行：`python3 /Users/fubo/.codex/skills/.system/skill-creator/scripts/quick_validate.py gin-business-process-mapper`

预期：验证通过。

- [ ] **步骤 2：运行全部单元测试**

运行：`python3 -m unittest discover -s gin-business-process-mapper/tests -v`

预期：全部通过。

- [ ] **步骤 3：生成两种样例输出并核对**

运行：

```bash
python3 gin-business-process-mapper/scripts/render_process.py gin-business-process-mapper/tests/fixtures/order_process.json --output-dir /tmp/gin-business-process-mapper-v2 --overwrite
```

预期：生成 Markdown 与 HTML；HTML 不含外部 URL；两种文件均包含全部节点、场景和岗位角色。

- [ ] **步骤 4：运行仓库测试**

运行：`python3 -m unittest discover -s tests -v`

预期：全部通过。

- [ ] **步骤 5：推送分支并检查 PR**

```bash
git push origin codex/gin-business-process-mapper
gh pr checks 9
```

记录本次技能相关测试结果；若仓库 CI 仍受其他技能的既有依赖问题影响，在交付说明中明确区分。
