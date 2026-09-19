# gin-writing-materials 优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让素材校验、主题定义、文档生成和会话状态通过一个可执行且可验证的管线连接起来。

**架构：** 保留现有 Python 模块和文件结构，在 `fragment`/`validate` 层收紧数据契约，在 `topic_def` 层提供结构化读取，在 `pipeline` 层串联校验与生成。已有 `build(...)` API 保留，CLI 只增加参数入口。

**技术栈：** Python 3.9、现有 Markdown/JSON 文件格式、pytest。

---

### 任务 1：强化碎片校验

**文件：** `gin-writing-materials/scripts/fragment.py`、`gin-writing-materials/scripts/validate.py`、对应测试。

- [x] 为空字段、非法 `confidence`、非法 `direction` 编写失败测试。
- [x] 让会话错误使 `ok=False`，并让默认文档生成拒绝错误碎片。
- [x] 运行相关测试并确认通过。

### 任务 2：统一主题定义输入

**文件：** `gin-writing-materials/scripts/topic_def.py`、`gin-writing-materials/scripts/build_doc.py`、对应测试。

- [x] 从 `00-主题定义.md` 读取问题、范围、成功标准、约束和假设。
- [x] 让成品文档输出这些字段，保持原有 Python 构建接口兼容。
- [x] 运行相关测试并确认通过。

### 任务 3：增加可执行管线和状态收尾

**文件：** `gin-writing-materials/scripts/pipeline.py`、CLI 入口、阶段状态测试。

- [x] 增加 `validate.py`、`build_doc.py` CLI。
- [x] 增加管线入口，成功生成后标记会话 `completed`。
- [x] 限制只有带 `[可回环]` 的当前阶段允许回环，并修正不同动作的完成态恢复。

### 任务 4：同步文档和验证资产

**文件：** `SKILL.md`、`README.md`、`references/interface-human-writing.md`、`CHANGELOG.md`、`evals/evals.json`。

- [x] 将标准入口改为 `pipeline.py`，同步真实输出文件名和下游说明。
- [x] 增加非法碎片与管线评估条目。
- [x] 保留历史验证报告，并标注其适用时间。

### 验证

- [x] `python3 -m pytest -q gin-writing-materials/tests` → 78 passed。
- [x] `PYTHONPYCACHEPREFIX=/tmp/gin-pyc python3 -m compileall -q gin-writing-materials/scripts gin-writing-materials/tests`。
- [x] CLI `--help` 和管线生成 smoke test。
