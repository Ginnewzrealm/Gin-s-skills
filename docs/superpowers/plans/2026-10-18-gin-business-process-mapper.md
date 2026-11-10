# gin-business-process-mapper 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 创建一个面向非技术业务人员的企业流程梳理 Skill，从日常叙述生成一致的 Markdown 流程说明和离线 HTML 流程图。

**架构：** Skill 用自然语言协议把业务叙述整理为 JSON；`validate_process.py` 验证节点、连线和证据状态；`render_process.py` 从同一 JSON 确定性生成 Markdown 和 HTML。HTML 模板内嵌 CSS、SVG 与交互脚本，不依赖网络。

**技术栈：** Markdown、YAML、Python 3 标准库、`unittest`、HTML/CSS/SVG/JavaScript。

---

## 文件结构

- `gin-business-process-mapper/SKILL.md`：触发条件、访谈原则、工作流与引用路由。
- `gin-business-process-mapper/agents/openai.yaml`：Codex UI 名称和默认调用提示。
- `gin-business-process-mapper/references/interview-protocol.md`：非技术访谈协议。
- `gin-business-process-mapper/references/process-schema.md`：JSON 字段与证据状态。
- `gin-business-process-mapper/references/output-rules.md`：双格式输出和一致性规则。
- `gin-business-process-mapper/assets/process-report-template.html`：HTML 外观和占位槽。
- `gin-business-process-mapper/scripts/validate_process.py`：结构验证器。
- `gin-business-process-mapper/scripts/render_process.py`：Markdown 与 HTML 生成器。
- `gin-business-process-mapper/tests/fixtures/order_process.json`：已确认订单流程样本。
- `gin-business-process-mapper/tests/test_validator.py`：验证器测试。
- `gin-business-process-mapper/tests/test_renderer.py`：双格式生成测试。
- `gin-business-process-mapper/evals/evals.json`：Skill 行为评测场景。
- `gin-business-process-mapper/evals/baseline.md`：无 Skill 基线失败记录。

### 任务 1：行为基线与 Skill 骨架

**文件：**
- 创建：`gin-business-process-mapper/evals/evals.json`
- 创建：`gin-business-process-mapper/evals/baseline.md`
- 创建：`gin-business-process-mapper/SKILL.md`
- 创建：`gin-business-process-mapper/agents/openai.yaml`
- 创建：`gin-business-process-mapper/references/interview-protocol.md`
- 创建：`gin-business-process-mapper/references/process-schema.md`
- 创建：`gin-business-process-mapper/references/output-rules.md`

- [x] **步骤 1：定义四个真实评测请求**

`evals.json` 覆盖：含糊的日常动作、当前与未来期望混杂、异常处理、信息不足。每条包含 `prompt` 和可观察的 `expectations`，例如“每轮只问一个业务语言问题”“不把推测写成确认事实”。

- [x] **步骤 2：在没有新 Skill 的上下文中运行代表性请求**

记录模型是否直接询问按钮、字段、状态机，是否未经确认补全软件流程。把逐字表现与失败原因写入 `evals/baseline.md`。

- [x] **步骤 3：写最小 Skill 与引用文档**

`SKILL.md` 必须把访谈信息分为：现状事实、软件实现含义、产品待设计事项；每次只问一个日常语言问题；先确认草案再生成文件。

- [x] **步骤 4：验证 Skill 结构**

运行：

```bash
python3 /Users/fubo/.codex/skills/.system/skill-creator/scripts/quick_validate.py gin-business-process-mapper
```

预期：`Skill is valid!`

- [x] **步骤 5：提交**

```bash
git add gin-business-process-mapper
git commit -m "feat: add business process interview skill"
```

### 任务 2：流程模型验证器

**文件：**
- 创建：`gin-business-process-mapper/tests/fixtures/order_process.json`
- 创建：`gin-business-process-mapper/tests/test_validator.py`
- 创建：`gin-business-process-mapper/scripts/validate_process.py`

- [x] **步骤 1：编写失败测试**

测试至少断言：有效样本通过；重复节点 ID 失败；连线引用缺失节点失败；缺少起止边界失败；无效证据状态失败；`inferred` 内容不能标为已确认事实。

```python
def test_rejects_edge_to_missing_node(self):
    data = deepcopy(self.fixture)
    data["edges"][0]["to"] = "N99"
    errors = validate(data)
    self.assertTrue(any("N99" in error for error in errors))
```

- [x] **步骤 2：运行测试确认失败**

运行：

```bash
python3 -m unittest gin-business-process-mapper/tests/test_validator.py -v
```

预期：FAIL，原因是 `validate_process` 尚不存在。

- [x] **步骤 3：实现验证器**

提供 `validate(data) -> list[str]` 和 CLI：

```bash
python3 scripts/validate_process.py process.json
```

无错误退出 0；有错误逐行输出并退出 1。

- [x] **步骤 4：运行测试确认通过**

运行同一步骤 2，预期全部 PASS。

- [x] **步骤 5：提交**

```bash
git add gin-business-process-mapper/scripts/validate_process.py gin-business-process-mapper/tests
git commit -m "feat: validate structured business processes"
```

### 任务 3：Markdown 生成器

**文件：**
- 修改：`gin-business-process-mapper/tests/test_renderer.py`
- 创建：`gin-business-process-mapper/scripts/render_process.py`

- [x] **步骤 1：编写失败测试**

测试 `render_markdown(data)` 包含流程范围、角色载体、所有节点 ID、异常边、软件实现含义、产品待设计事项、待确认项和事实来源；特殊字符保持可读。

```python
def test_markdown_contains_same_nodes_as_source(self):
    output = render_markdown(self.data)
    for node in self.data["nodes"]:
        self.assertIn(node["id"], output)
```

- [x] **步骤 2：运行测试确认失败**

运行：

```bash
python3 -m unittest gin-business-process-mapper/tests/test_renderer.py -v
```

预期：FAIL，原因是 `render_process` 尚不存在。

- [x] **步骤 3：实现 Markdown 生成**

调用验证器后生成固定十章节文档。确认事实、推导项和待设计项使用不同标签；不得静默生成无效数据。

- [x] **步骤 4：运行测试确认通过**

运行同一步骤 2，预期 Markdown 测试 PASS。

- [x] **步骤 5：提交**

```bash
git add gin-business-process-mapper/scripts/render_process.py gin-business-process-mapper/tests/test_renderer.py
git commit -m "feat: render business process markdown"
```

### 任务 4：离线 HTML 流程图

**文件：**
- 创建：`gin-business-process-mapper/assets/process-report-template.html`
- 修改：`gin-business-process-mapper/scripts/render_process.py`
- 修改：`gin-business-process-mapper/tests/test_renderer.py`

- [x] **步骤 1：编写失败测试**

测试 HTML 包含所有节点 ID、SVG 流程图、节点详情、证据状态、键盘焦点、窄屏样式与打印样式；输出不得包含 `http://` 或 `https://`；用户文本必须 HTML 转义。

```python
def test_html_is_offline_and_escapes_user_text(self):
    data = deepcopy(self.data)
    data["nodes"][0]["business_fact"] = "客户输入 <script>alert(1)</script>"
    output = render_html(data, self.template)
    self.assertNotIn("<script>alert(1)</script>", output)
    self.assertNotRegex(output, r"https?://")
```

- [x] **步骤 2：运行测试确认失败**

运行 renderer 测试，预期 HTML 相关断言 FAIL。

- [x] **步骤 3：实现模板与 SVG 布局**

沿用已确认原型的白底、青绿色标题、横向主线和上下分支。主线节点从左到右；异常和返工边放在下方；节点过多时按 `phase` 分组生成局部图。所有用户文本通过 `html.escape`。

- [x] **步骤 4：增加 CLI 双输出**

```bash
python3 scripts/render_process.py process.json --output-dir ./output
```

生成 `<流程名称>-流程说明.md` 与 `<流程名称>-流程图.html`，已有文件默认报错；显式 `--overwrite` 才覆盖。

- [x] **步骤 5：运行测试确认通过**

运行：

```bash
python3 -m unittest discover -s gin-business-process-mapper/tests -v
```

预期：全部 PASS。

- [x] **步骤 6：提交**

```bash
git add gin-business-process-mapper/assets gin-business-process-mapper/scripts gin-business-process-mapper/tests
git commit -m "feat: render offline business process html"
```

### 任务 5：端到端验证与交付

**文件：**
- 修改：`gin-business-process-mapper/evals/baseline.md`
- 创建：`gin-business-process-mapper/evals/with-skill.md`

- [x] **步骤 1：使用 Skill 重跑代表性场景**

逐项记录：是否使用非技术语言、是否一次只问一个问题、是否分离事实和推导、是否在确认前避免生成终稿。

- [x] **步骤 2：生成订单流程样本**

运行：

```bash
python3 gin-business-process-mapper/scripts/render_process.py \
  gin-business-process-mapper/tests/fixtures/order_process.json \
  --output-dir /tmp/gin-business-process-output
```

预期生成一个 Markdown 和一个 HTML。

- [x] **步骤 3：验证 Skill 和脚本**

```bash
python3 /Users/fubo/.codex/skills/.system/skill-creator/scripts/quick_validate.py gin-business-process-mapper
python3 -m unittest discover -s gin-business-process-mapper/tests -v
bash run_all_tests.sh
```

预期：Skill 合法；新 Skill 测试全部通过；仓库全量测试在正常写权限下全部通过。

- [x] **步骤 4：需求核对**

逐项核对设计规格第 3–10 节，确认无占位符、两种输出节点一致、HTML 无网络依赖、推导内容有明显标记。

- [x] **步骤 5：提交**

```bash
git add gin-business-process-mapper/evals
git commit -m "test: verify business process mapper behavior"
```
