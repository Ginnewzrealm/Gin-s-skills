# wechat-article-core 优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在保留多 skill 编排的前提下，通过素材全读、narrative_protocol 风格操作化、role_boundary 人-AI 分工契约、精简阶段、新增扩写方法论知识库、借鉴 baoyu/花叔机制，优化微信公众号长文写作技能簇。

**架构：** `wechat-article-core` 主编排层新增 `role_boundary` 阻塞式确认阶段，新增 `narrative_protocol` 和结构化的 `materials_summary` 上下文字段；`style_selector.py` 完整读取 `.md` 素材并持久化到 `materials_full.md`；`template_loader.py` 从 YAML 模板提取 `narrative_protocol`；新增 `references/expansion-methodology.md`、`references/ai-flavor-guide.md`、`references/writing-checklist.md` 作为跨 skill 共享知识库；`wechat-article-clarify`、`wechat-article-angle`、`wechat-article-outline`、`khazix-writer`、`wechat-article-polish`、`wechat-article-title`、`wechat-article-quality` 消费该协议和方法论；`config.yaml` 增加素材递归开关。

**技术栈：** Python 3、PyYAML、pytest。

---

## 一、文件结构

| 文件 | 职责 |
|------|------|
| `wechat-article-core/scripts/style_selector.py` | 扫描素材、完整读取 `.md`、生成结构化摘要、持久化 `materials_full.md` |
| `wechat-article-core/scripts/template_loader.py` | 加载 YAML 模板、校验、新增 `extract_narrative_protocol()` |
| `wechat-article-core/config.yaml` | 增加 `materials.recursive` 与 `materials.extensions` 配置 |
| `wechat-article-core/SKILL.md` | 更新 stage 流程、上下文协议、role_boundary 说明、输出目录、持久化、版本自检 |
| `wechat-article-core/references/expansion-methodology.md` | 新增：核心原则、材料优先、说话位置、内容骨架、中文句法纪律 |
| `wechat-article-core/references/ai-flavor-guide.md` | 新增：四层 AI 味模型、六种 AI 味诊断、24 种 AI 写作模式 |
| `wechat-article-core/references/writing-checklist.md` | 新增：通用禁用项、文采增强四机制、内容债/语言债诊断 |
| `wechat-article-core/references/writing-style.md` | 更新/新增：通用活人感写作原则（去卡兹克个人绑定） |
| `wechat-article-clarify/SKILL.md` | 调整为需求确认 + 素材完整性确认，增加说话位置三问 |
| `wechat-article-angle/SKILL.md` | 输入增加完整素材和 `narrative_protocol`，输出增加 `narrative_fit` 和 `material_support` |
| `wechat-article-outline/SKILL.md` | 输入增加 `narrative_protocol` 和 `expansion-methodology.md`，按协议生成带素材映射的大纲 |
| `khazix-writer/SKILL.md` | 输入增加 `narrative_protocol`、`expansion-methodology.md`、`writing-checklist.md`、`writing-style.md`（精简版）；删除 AI 角色边界、四层自检、卡兹克个人风格绑定；新增"扩写纪律"小节；frontmatter 保留 `narrative_protocol.derived_from` |
| `wechat-article-polish/SKILL.md` | 输入增加 `narrative_protocol`、`ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md` |
| `wechat-article-title/SKILL.md` | 输入增加 `narrative_protocol.global_rules.opening` |
| `wechat-article-quality/SKILL.md` | 读取 `narrative_protocol.forbidden_zone`、`ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md`（完整版），增加内容债/语言债诊断 |
| `wechat-article-core/tests/test_style_selector.py` | 更新测试：完整读取、结构化摘要、递归开关 |
| `wechat-article-core/tests/test_template_loader.py` | 新增测试：`extract_narrative_protocol()` |
| `wechat-article-core/tests/test_core_stages.py` | 更新测试：移除 `polish_confirmed`，新增 `role_boundary` |

---

## 二、任务列表

### 任务 1：修改 `style_selector.py` 完整读取素材

**文件：**
- 修改：`wechat-article-core/scripts/style_selector.py`
- 修改：`wechat-article-core/tests/test_style_selector.py`

**目标：**
- 移除 `max_chars=1200` 限制。
- `scan_materials()` 支持 `recursive` 参数，默认只扫顶层。
- `summarize_materials()` 返回结构化 dict，并持久化 `materials_full.md`。

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_style_selector.py

def test_summarize_materials_returns_full_content_dict(tmp_path):
    long_text = "这是正文。" * 1000
    md_file = tmp_path / "long.md"
    md_file.write_text(long_text, encoding="utf-8")

    result = summarize_materials([md_file], output_dir=tmp_path / "out")

    assert result["fully_loaded"] is True
    assert result["total_files"] == 1
    assert result["total_chars"] == len("这是正文。" * 1000)
    assert result["files"][0]["name"] == "long.md"
    assert result["files"][0]["chars"] == len("这是正文。" * 1000)
    assert "summary_text" in result
    assert "这是正文。" in result["summary_text"]

    # 验证 materials_full.md 已生成
    full_path = tmp_path / "out" / "materials_full.md"
    assert full_path.exists()
    assert "这是正文。" in full_path.read_text(encoding="utf-8")


def test_scan_materials_default_non_recursive(tmp_path):
    (tmp_path / "a.md").write_text("top", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("nested", encoding="utf-8")

    files = scan_materials(tmp_path)
    assert len(files) == 1
    assert files[0].name == "a.md"


def test_scan_materials_recursive(tmp_path):
    (tmp_path / "a.md").write_text("top", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("nested", encoding="utf-8")

    files = scan_materials(tmp_path, recursive=True)
    names = {f.name for f in files}
    assert names == {"a.md", "nested.md"}
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
python3 -m pytest tests/test_style_selector.py::test_summarize_materials_returns_full_content_dict tests/test_style_selector.py::test_scan_materials_default_non_recursive tests/test_style_selector.py::test_scan_materials_recursive -v
```

预期：3 个测试 FAIL（返回类型不支持、recursive 参数不存在）。

- [ ] **步骤 3：修改 `style_selector.py`**

```python
# wechat-article-core/scripts/style_selector.py

from typing import List, Optional


SUPPORTED_EXTENSIONS = {".md", ".txt", ".url"}


def scan_materials(input_dir: Path, recursive: bool = False) -> List[Path]:
    """扫描输入目录中的素材文件。

    默认只扫描顶层目录，避免读到无关文件。
    开启 recursive 后递归扫描所有子目录。
    """
    if not input_dir or not input_dir.exists():
        return []

    files = []
    for item in input_dir.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(item)
        elif item.is_dir() and recursive:
            files.extend(scan_materials(item, recursive=True))
    return sorted(files)


def summarize_materials(
    files: List[Path],
    output_dir: Optional[Path] = None,
) -> dict:
    """完整读取文本类素材，生成结构化摘要并持久化全量内容。

    Returns:
        {
            "fully_loaded": bool,
            "total_files": int,
            "total_chars": int,
            "files": [{"name": str, "chars": int}],
            "summary_text": str,
            "materials_path": str,
        }
    """
    parts = []
    file_infos = []
    total_chars = 0

    for f in files:
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                raw = f.read_text(encoding="utf-8")
                cleaned = _strip_markdown(raw)
                total_chars += len(cleaned)
                file_infos.append(
                    {
                        "name": f.name,
                        "chars": len(cleaned),
                    }
                )
                parts.append(f"【{f.name}】{cleaned}")
            except Exception:
                file_infos.append({"name": f.name, "chars": 0, "error": "读取失败"})
                parts.append(f"【{f.name}】（读取失败）")
        else:
            file_infos.append({"name": f.name, "chars": 0, "skipped": True})
            parts.append(f"【{f.name}】（非文本文件）")

    summary_text = "\n".join(parts)
    materials_path = None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        materials_file = output_dir / "materials_full.md"
        materials_file.write_text(summary_text, encoding="utf-8")
        materials_path = str(materials_file)

    return {
        "fully_loaded": True,
        "total_files": len(files),
        "total_chars": total_chars,
        "files": file_infos,
        "summary_text": summary_text,
        "materials_path": materials_path,
    }
```

- [ ] **步骤 4：更新旧测试以适应新 API**

```python
# tests/test_style_selector.py

# 替换原 test_summarize_materials_reads_text
def test_summarize_materials_reads_text(tmp_path):
    (tmp_path / "a.md").write_text("这是素材内容", encoding="utf-8")
    result = summarize_materials([tmp_path / "a.md"])
    assert "这是素材内容" in result["summary_text"]


# 替换原 test_summarize_materials_skips_frontmatter_and_headers
def test_summarize_materials_skips_frontmatter_and_headers(tmp_path):
    content = (
        "---\n"
        "title: 测试\n"
        "date: 2026-08-25\n"
        "---\n\n"
        "# 这是大标题\n\n"
        "**这是重点**\n\n"
        "这才是正文内容，应该被保留。\n"
        "## 二级标题\n\n"
        "后续正文。\n"
    )
    md_file = tmp_path / "sample.md"
    md_file.write_text(content, encoding="utf-8")
    result = summarize_materials([md_file])
    summary = result["summary_text"]
    assert "这才是正文内容" in summary
    assert "# 这是大标题" not in summary
    assert "**这是重点**" not in summary
    assert "title: 测试" not in summary


# 替换原 test_scan_materials_recursive_one_level
def test_scan_materials_recursive_one_level(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("nested", encoding="utf-8")
    files = scan_materials(tmp_path, recursive=True)
    assert len(files) == 1
    assert files[0].name == "nested.md"
```

- [ ] **步骤 5：运行测试验证通过**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
python3 -m pytest tests/test_style_selector.py -v
```

预期：全部 PASS。

- [ ] **步骤 6：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add scripts/style_selector.py tests/test_style_selector.py
git commit -m "feat(style_selector): 完整读取 Markdown 素材并持久化 materials_full.md"
```

---

### 任务 2：新增 `extract_narrative_protocol()` 到 `template_loader.py`

**文件：**
- 修改：`wechat-article-core/scripts/template_loader.py`
- 修改：`wechat-article-core/tests/test_template_loader.py`

**目标：**
- 从 YAML 模板的 `结构参考`、`怎么开头`、`怎么推进` 等字段提取 `narrative_protocol`。

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_template_loader.py

def test_extract_narrative_protocol_from_social_slice():
    template = load_template(_TEMPLATE_DIR / "social-slice.yaml")
    protocol = template_loader.extract_narrative_protocol(template)

    assert protocol["derived_from"] == "social-slice"
    assert len(protocol["sections"]) > 0
    first = protocol["sections"][0]
    assert "name" in first
    assert "purpose" in first
    assert "length" in first
    assert "must_include" in first
    assert "global_rules" in protocol
    assert "opening" in protocol["global_rules"]
    assert "forbidden_zone" in protocol
    assert len(protocol["forbidden_zone"]) > 0


def test_extract_narrative_protocol_parses_forbidden_zone_list():
    protocol = template_loader.extract_narrative_protocol({
        "meta": {"id": "test"},
        "结构参考": [],
        "禁区": ["禁止A", "禁止B"],
    })
    assert protocol["forbidden_zone"] == ["禁止A", "禁止B"]


def test_extract_narrative_protocol_parses_forbidden_zone_text():
    protocol = template_loader.extract_narrative_protocol({
        "meta": {"id": "test"},
        "结构参考": [],
        "禁区": "- 禁止A\n- 禁止B\n",
    })
    assert "禁止A" in protocol["forbidden_zone"]
    assert "禁止B" in protocol["forbidden_zone"]
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
python3 -m pytest tests/test_template_loader.py::test_extract_narrative_protocol_from_social_slice tests/test_template_loader.py::test_extract_narrative_protocol_parses_forbidden_zone_list tests/test_template_loader.py::test_extract_narrative_protocol_parses_forbidden_zone_text -v
```

预期：3 个测试 FAIL（函数未定义）。

- [ ] **步骤 3：修改 `template_loader.py`**

```python
# wechat-article-core/scripts/template_loader.py

from typing import Any, List


def extract_narrative_protocol(template: dict) -> dict:
    """从 YAML 模板中提取叙事协议，供大纲生成和正文写作强制执行。"""
    meta = template.get("meta", {})
    raw_sections = template.get("结构参考", [])

    sections = []
    for sec in raw_sections:
        if not isinstance(sec, dict):
            continue
        sections.append(
            {
                "name": sec.get("section", ""),
                "purpose": sec.get("purpose", ""),
                "length": sec.get("length", ""),
                "must_include": sec.get("must_include", []),
                "forbidden": sec.get("forbidden", []),
                "template": sec.get("template", ""),
            }
        )

    return {
        "derived_from": meta.get("id", ""),
        "sections": sections,
        "global_rules": {
            "opening": template.get("怎么开头", ""),
            "progression": template.get("怎么推进", ""),
            "twist": template.get("怎么处理意外/转折", ""),
            "knowledge": template.get('怎么"掏知识"', ""),
            "reader": template.get("怎么处理读者", ""),
            "ending": template.get("怎么结尾", ""),
        },
        "tone": template.get("情绪基调", ""),
        "forbidden_zone": _parse_forbidden_zone(template.get("禁区", [])),
    }


def _parse_forbidden_zone(value: Any) -> List[str]:
    """解析禁区字段，支持列表或文本块。"""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if not value:
        return []
    return [
        line.strip().lstrip("- ").strip()
        for line in str(value).strip().splitlines()
        if line.strip()
    ]
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
python3 -m pytest tests/test_template_loader.py -v
```

预期：全部 PASS。

- [ ] **步骤 5：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add scripts/template_loader.py tests/test_template_loader.py
git commit -m "feat(template_loader): 从 YAML 模板提取 narrative_protocol"
```

---

### 任务 3：更新 `config.yaml`

**文件：**
- 修改：`wechat-article-core/config.yaml`

**目标：**
- 增加素材读取配置。

- [ ] **步骤 1：修改 `config.yaml`**

```yaml
# 在 optional_dependencies 之后、default_template 之前插入

materials:
  recursive: false
  extensions:
    - ".md"
    - ".txt"
    - ".url"

default_template: social-slice
```

- [ ] **步骤 2：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add config.yaml
git commit -m "config: 增加 materials 读取配置"
```

---

### 任务 4：新增扩写方法论知识库（3 个 references 文件）

**文件：**
- 创建：`wechat-article-core/references/expansion-methodology.md`
- 创建：`wechat-article-core/references/ai-flavor-guide.md`
- 创建：`wechat-article-core/references/writing-checklist.md`

**目标：**
- 建立跨 skill 共享的公众号长文扩写方法论知识库。
- 按消费方拆分为 3 个文件，降低单个 skill 上下文噪音。

- [ ] **步骤 1：创建 `expansion-methodology.md`**

```markdown
# 公众号长文扩写方法论

> 消费方：`wechat-article-outline`、`khazix-writer`

## 一、核心原则

扩写不是把大纲扩成更多字，而是：

- 把骨架填上真实材料
- 让每一句话都有来路
- 让读者能感受到说话者的存在
- 让文章有节奏、有判断、有记忆点

## 二、写前定调（说话位置法）

动笔前回答三个问题：

1. **谁在说这件事？** 亲历者 / 调查者 / 观察者 / 研究者
2. **他凭什么知道这些事？** 哪些是亲历、哪些是查证、哪些是推测
3. **他为什么现在想说这件事？** 触发点是什么

## 三、材料优先原则

非虚构稿每个 section 扩写前，先检查：

- 本 section 的 `must_include` 哪些有素材支撑？
- 哪些是必须用户补充的真实经历？
- 材料不足时只能：
  - 标注 `【需用户补充】`
  - 用已确认的事实性流程代替
  - 缩短本 section

## 四、内容骨架

每个 section 尽量包含：

1. 情境：一个真实情境或矛盾
2. 判断：本节核心判断
3. 证据：具体人 / 场景 / 数据 / 行为
4. 方法/区分：给读者一个可用的区分或翻译
5. 下一步/后果/开放问题

## 五、中文句法纪律

- 主干先行：先写谁做了什么，再补原因、时间、条件
- 主语不重复：上下文明确后不再重复主语
- 抽象动作换成具体动作：把"进行了优化"改成"砍掉了三个环节"
- 每个判断都要有细节托着：细节标准是"换了别人就不成立"
- 后一句接住前一句的问题：推进靠材料和因果
- 情绪从动作里出来：不写"我非常震惊"，写"盯着屏幕看了十秒"
- 每段只完成一件事
- 新段落必须增加新东西
- 长短句交替，制造节奏
```

- [ ] **步骤 2：创建 `ai-flavor-guide.md`**

```markdown
# AI 味治理指南

> 消费方：`wechat-article-quality`、`wechat-article-polish`

## 一、四层 AI 味模型

- 词汇层：套话、AI 高频词
- 句式层：否定排比、工整对偶、匀速句长
- 结构层：每节末尾落金句、导游式路标、完美闭环
- 经验层：细节可替换、判断两头堵、作者不在场

## 二、六种 AI 味诊断

1. 太完整：每个角度都覆盖，但没有活的情境
2. 太顺滑：连接很圆，冲突消失，节奏匀速
3. 太抽象：价值、增长、能力等名词替代可见事实
4. 太客观：不说谁看见了什么、谁做了决定
5. 太会总结：结尾向上升华，不落到动作/后果
6. 清理后发扁：AI 质感没了，但没有命名/意象/节奏

## 三、24 种 AI 写作模式（精简）

- 过度强调意义、遗产和更广泛的趋势
- 过度强调知名度和媒体报道
- 以 -ing 结尾的肤浅分析
- 宣传和广告式语言
- 模糊归因和含糊措辞
- 提纲式的"挑战与未来展望"部分
- 过度使用的 AI 词汇
- 避免使用"是"（系动词回避）
- 否定式排比
- 三段式法则过度使用
- 刻意换词
- 虚假范围
- 破折号/粗体过度使用
- 内联标题垂直列表
- 表情符号
- 协作交流痕迹
- 知识截止日期免责声明
- 谄媚语气
- 填充短语
- 过度限定
- 通用积极结论
```

- [ ] **步骤 3：创建 `writing-checklist.md`**

```markdown
# 写作检查清单

> 消费方：`khazix-writer`、`wechat-article-quality`、`wechat-article-polish`

## 一、通用禁用项

- 翻案腔：不是...而是... / 你以为...其实...
- 同构排比：连续三句以上同一句型
- 抽象名词配具体动词：时间不会保管，焦虑不会显形
- 动词名词化：进行了/实现了/完成了 + 动名词
- 提示性冒号："一句话总结："
- 商业黑话：赋能、抓手、闭环、底层逻辑
- 模型抒情词：安放、抵达、微光、褶皱、丰盈
- AI 高频词：此外、至关重要、深入探讨、格局
- 模糊归因：专家认为、行业报告显示
- 口号式结尾：让我们共同期待、开启新篇章

## 二、文采增强四机制

1. **命名处境**：把模糊问题压成读者能记住的一句话
2. **让不可见的东西可见**：把时间、愿望、混乱变成可被看见的东西
3. **给句子一个容器**：纸、清单、屏幕、路径、表格
4. **落回动作或证据**：能被写下、测试、观察、重复或复盘

## 三、内容债 vs 语言债

- **内容债**：缺事实、无真实例子、无观点、受众不清、判断无支撑
- **语言债**：AI 套话、结构过分整齐、连接词过多、被动语态、升华式结尾、过度顺滑

修复策略：

- 内容债 → 标注【需补素材】，不硬编
- 语言债 → 按本文件规则改写
```

- [ ] **步骤 4：更新 `references/writing-style.md`**

将原卡兹克个人风格指南改为通用活人感写作原则。

保留：

```markdown
# 活人感写作通用原则

## 一、叙述者位置
- 明确谁在说话
- 说明凭什么知道
- 交代为什么现在说

## 二、材料优先
- 用具体事实、动作、数字、原话支撑判断
- 不编造用户未提供的个人经历

## 三、表达原则
- 讲人话，不用套话
- 敢下判断但保留灰度
- 先理解对立面，再给出视角
- 情绪从动作和事实里自然出来
- 长短句交替，制造节奏
- 每段只完成一件事
- 新段落必须增加新东西

## 四、通用禁区
- 教科书开头
- 翻案腔
- 模糊归因
- 口号式结尾
- 动词名词化
- 商业黑话
```

删除：

- 卡兹克个人核心价值观 4 条
- 卡兹克专属口语化词组
- 具体情绪标点用法
- 人物画像法、文化升维、亲自下场等绑定个人的表达

- [ ] **步骤 5：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add references/expansion-methodology.md references/ai-flavor-guide.md references/writing-checklist.md references/writing-style.md
git commit -m "docs: 新增公众号长文扩写方法论知识库（拆分为 3 个文件）并更新通用风格指南"
```

---

### 任务 5：更新 `wechat-article-core/SKILL.md`

**文件：**
- 修改：`wechat-article-core/SKILL.md`

**目标：**
- 更新入口流程：完整读取素材、生成 narrative_protocol。
- 更新 stage 流程：新增 `role_boundary`，删除 `polish_confirmed`。
- 更新上下文协议字段。
- 增加 `role_boundary` 阶段说明。
- 增加输出目录结构、持久化、版本自检。

- [ ] **步骤 1：更新入口流程描述**

在入口流程第 4 步（风格选择）中，将 `style_selector.py` 调用改为：

```markdown
4. **调用 `scripts/style_selector.py` 进行风格选择与素材读取：**
   - 主 skill 将 `context.md.paths.input_dir` 和 `materials.recursive` 传入 `style_selector.scan_materials()`。
   - 完整读取所有 `.md` 素材，生成 `materials_full.md` 保存到 `output_dir/<article_id>/materials/`。
   - 主 skill 调用 `template_loader.list_all_templates(...)` 获取可用风格，
     再调用 `style_selector.recommend_styles(topic, materials_summary["summary_text"], templates)` 生成推荐列表。
   - 用户选择后，主 skill 将 `selected_template` 写入 `context.md`。
   - 主 skill 调用 `template_loader.extract_narrative_protocol(selected_template)` 生成 `narrative_protocol` 并写入 `context.md`。
```

- [ ] **步骤 2：更新阶段定义表**

```markdown
| stage | 下一步动作 | 调用的子技能 | 类型 |
|-------|-----------|-------------|------|
| init | 路径初始化检查 + 风格选择 | init_checker.py + style_selector.py + template_loader.py（主 skill 内部） | AI |
| clarify | 需求澄清 | wechat-article-clarify | 人工 |
| template_loaded | 加载模板 + 生成 narrative_protocol | （主 skill 内部加载） | AI |
| angle_diagnosed | 素材诊断 | wechat-article-angle | AI |
| role_boundary | 人-AI 协作契约书确认 | （主 skill 内部） | 人工 |
| angle_matched | 生成候选大纲 | wechat-article-outline | AI |
| outline_generated | 选择/修改大纲 | （人工） | 人工 |
| outline_selected | 分段写正文 | khazix-writer | AI |
| draft_written | 二次改写正文 | （人工） | 人工 |
| draft_revised | 小标题优化 + 润色 | wechat-article-polish | AI |
| polished | 提炼标题候选 | wechat-article-title(article) | AI |
| titled | 选择/修改标题 | （人工） | 人工 |
| title_confirmed | 质量自检 | wechat-article-quality | AI |
| quality_failed | 返回润色 | wechat-article-polish | AI（循环） |
| quality_checked | 终审定稿 | （人工） | 人工 |
| finalized | 输出 Markdown | （主 skill 内部） | AI |
| markdown_output | 发布/保存决策 | （人工） | 人工 |
| publish_decision | 保存/推送 | wps-skill / baoyu-post-to-wechat | AI/外部 |
```

- [ ] **步骤 3：更新流程闭环规则**

删除原规则中关于 `polish_confirmed` 的必经节点描述。
增加：

```markdown
5. **role_boundary 是阻塞式人工节点**
   - 用户必须确认 `collaboration_charter` 后，才能进入 `angle_matched`。
   - 未确认时，主 skill 停留在 `role_boundary` 阶段，重复展示契约书等待用户回复。

6. **输出目录结构化**
   - 所有产物按 `output_dir/<article_id>/` 组织。
   - 子目录包括：materials/、drafts/、outlines/、titles/、reports/。

7. **流程持久化**
   - 主 skill 维护 `progress.md` 和 `blocked.md`。
   - 每次会话启动时先读取 `progress.md` 恢复状态。

8. **版本自检**
   - 本 skill 目录下维护 `.last-update-check` 文件。
   - 每 30 天检查一次远程仓库是否有更新。
```

- [ ] **步骤 4：更新上下文协议示例**

在 `context.md` 示例中新增/修改字段：

```yaml
materials_summary:
  fully_loaded: true
  recursive: false
  total_files: 3
  total_chars: 12580
  files:
    - name: 采访记录.md
      chars: 5420
      path: /home/user/wechat-article-output/<article_id>/materials/采访记录.md
  summary_text: "..."
  materials_path: /home/user/wechat-article-output/<article_id>/materials/materials_full.md

narrative_protocol:
  derived_from: social-slice
  sections:
    - name: 现在
      purpose: 用一个具体画面把人物推出来
      length: 150-300
      must_include:
        - 具体时间/场景
        - 人物动作
        - 反常或矛盾
  global_rules:
    opening: 从具体人物具体时刻开始
    progression: 每写一段只推进一层
  tone: 克制、平视、有温度
  forbidden_zone:
    - 第一人称"我""我们"
    - "随着AI时代的到来"

collaboration_charter:
  ai_owned:
    - 推荐角度
    - 生成大纲
  human_required:
    - 第一手经历
    - 核心角度拍板
  user_preference:
    strict_template: true
    missing_experience_handling: 占位符
  confirmed: false

requirements:
  topic: ""
  target_reader: ""
  core_points: []
  word_count: 2500
  materials: []
  speaker_position:
    who: ""
    credential: ""
    trigger: ""
```

- [ ] **步骤 5：新增 `role_boundary` 阶段说明章节**

在 SKILL.md 中新增：

```markdown
## role_boundary 阶段（人-AI 协作契约书）

### 位置

`angle_diagnosed` 之后，`angle_matched` 之前。

### 类型

阻塞式人工节点。用户未确认前，不进入大纲生成。

### 输出

主 skill 输出《人-AI 协作契约书》，包含：

- **AI 负责做**：推荐角度、生成大纲、找证据/类比、按角度扩写、结构优化、质量自检。
- **必须由你来做**：第一手经历、核心角度拍板、情绪节点、关键金句、二次改写、终审定稿。
- **当前需要你确认**：素材是否足够、是否有真实经验、是否严格遵循模板结构、缺真实经历时如何处理。

用户确认后，主 skill 将 `collaboration_charter.confirmed` 置为 `true` 并写入 `context.md`。
```

- [ ] **步骤 6：新增输出目录与持久化章节**

```markdown
## 输出目录结构

```
output_dir/
└── <article_id>/
    ├── context.md
    ├── article.md
    ├── progress.md        # 当前 stage、关键决策、风险点
    ├── blocked.md         # 等待用户确认的内容
    ├── materials/
    │   └── materials_full.md
    ├── drafts/
    │   ├── article_draft.md
    │   ├── article_draft_revised.md
    │   └── polished_draft.md
    ├── outlines/
    │   └── outline_candidates.md
    ├── titles/
    │   └── title_candidates.md
    └── reports/
        └── quality_report.md
```

## 长流程持久化文件

- `progress.md`：当前 stage、已完成的关键决策、风险点
- `blocked.md`：等待用户确认或补充的项
- `materials_full.md`：已完整读取的素材

## 版本自检

本 skill 目录下维护 `.last-update-check` 文件，记录最近一次检查远程仓库的日期。

- 文件存在且距今不足 30 天：跳过自检
- 文件不存在或超过 30 天：对比本地 commit 与远程 origin HEAD
- 确认落后时，在当前任务完成后提示用户更新，不自动执行
```

- [ ] **步骤 7：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add SKILL.md
git commit -m "docs(core): 更新流程、新增 role_boundary 与 narrative_protocol、定义输出目录与持久化"
```

---

### 任务 6：更新 `wechat-article-clarify/SKILL.md`

**文件：**
- 修改：`wechat-article-clarify/SKILL.md`

**目标：**
- 从"素材收集"调整为"需求确认 + 素材完整性确认"。
- 增加说话位置三问。
- 输出 `requirements.speaker_position`。

> **前提**：上游已有专门整理素材的 skill，输入为结构化 Markdown 素材文档，本 skill 不再重复收集素材内容。

- [ ] **步骤 1：修改动作章节**

原文：

```markdown
通过结构化访谈明确：
1. 主题：文章要讨论什么？
2. 目标读者：给谁看？（身份标签）
3. 核心观点：最想表达什么？
4. 字数要求：预计多长？
5. 可用素材：有什么故事、数字、痛点、反常识观点？
```

改为：

```markdown
通过结构化访谈确认：
1. 主题：文章要讨论什么？
2. 目标读者：给谁看？（身份标签）
3. 核心观点/立场：你最想表达什么判断？
4. 字数要求：预计多长？
5. 说话位置：
   - 谁在说这件事？（亲历者 / 调查者 / 观察者 / 研究者）
   - 他凭什么知道这些事？（亲历 / 查证 / 推测）
   - 他为什么现在想说这件事？（触发点是什么）
6. 素材完整性确认：
   - 已提供的结构化素材是否足够支撑这个选题？
   - 还缺什么关键信息？（只确认缺口，不收集素材内容）
```

- [ ] **步骤 2：修改输出结构**

```markdown
- 需求记录结构：
  - `topic`
  - `target_reader`
  - `core_points`
  - `word_count`
  - `materials`
  - `speaker_position`
    - `who`：叙述者身份
    - `credential`：凭什么知道
    - `trigger`：为什么现在说
  - `notes`（可选）
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-clarify
git add SKILL.md
git commit -m "docs(clarify): 增加说话位置三问"
```

---

### 任务 7：更新 `wechat-article-angle/SKILL.md`

**文件：**
- 修改：`wechat-article-angle/SKILL.md`

**目标：**
- 输入增加完整素材和 `narrative_protocol`。
- 输出增加 `narrative_fit` 和 `material_support`。

- [ ] **步骤 1：修改输入章节**

```markdown
## 输入

- 需求记录
- 模板规则
- `context.md.narrative_protocol`（新增）
- `context.md.materials_summary.materials_path` 指向的 `materials_full.md`（新增）
- `context.md.requirements.speaker_position`（新增）
- references/angle-library.md
- references/emotion-trigger-system.md
- references/content-principles-dbs.md
```

- [ ] **步骤 2：修改输出章节**

```markdown
## 输出

- 素材诊断报告
- 可用角度列表，每项包含：
  - `id`
  - `name`
  - `description`
  - `narrative_fit`：与 narrative_protocol 的匹配度说明
  - `material_support`：素材支撑点列表
  - 主/次情绪触发点
- 推荐情绪触发点
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-angle
git add SKILL.md
git commit -m "docs(angle): 基于完整素材和 narrative_protocol 诊断"
```

---

### 任务 8：更新 `wechat-article-outline/SKILL.md`

**文件：**
- 修改：`wechat-article-outline/SKILL.md`

**目标：**
- 输入增加 `narrative_protocol`、`expansion-methodology.md`、完整素材。
- 输出 sections 必须按 narrative_protocol 生成。
- 每个 section 增加 `materials_ref` 和 `human_needed`。

- [ ] **步骤 1：修改输入章节**

```markdown
## 输入

- 需求记录
- 模板规则
- `context.md.narrative_protocol`（新增）
- `context.md.materials_summary.materials_path` 指向的 `materials_full.md`（新增）
- `wechat-article-core/references/expansion-methodology.md`（新增）
- references/hook-design.md
- references/content-outline-framework.md
- references/content-principles-dbs.md
```

- [ ] **步骤 2：修改动作第 3 步**

原文：

```markdown
3. 章节结构（sections）复用风格文件中的 `结构参考` 列表格式，每个 section 包含标题和职责说明。
```

改为：

```markdown
3. 章节结构（sections）必须严格按 `narrative_protocol.sections` 的顺序、职责和约束生成。
   - `name` 对应 narrative_protocol 的 section name
   - `purpose` 从 narrative_protocol 复制
   - `must_include` 从 narrative_protocol 复制
   - `forbidden` 从 narrative_protocol 复制
   - `content` 根据素材和需求填充
   - `materials_ref` 标注本 section 有哪些素材支撑
   - `human_needed` 标注哪些必须用户补充真实经历
   - `word_count_estimate` 预估本 section 字数
```

- [ ] **步骤 3：修改输出章节**

在 `sections` 输出结构中增加：

```markdown
- `sections`
  - `name`
  - `purpose`
  - `must_include`
  - `forbidden`
  - `content`
  - `materials_ref`（新增）
  - `human_needed`（新增）
  - `word_count_estimate`（新增）
```

- [ ] **步骤 4：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-outline
git add SKILL.md
git commit -m "docs(outline): 按 narrative_protocol 生成带素材映射的大纲"
```

---

### 任务 9：更新 `khazix-writer/SKILL.md`

**文件：**
- 修改：`khazix-writer/SKILL.md`

**目标：**
- 名字保留 `khazix-writer`，但不再绑定卡兹克个人风格。
- 输入增加 `narrative_protocol`、`expansion-methodology.md`、`writing-checklist.md`、`writing-style.md`（精简版）、`outline.sections[].materials_ref`。
- 删除 AI 角色边界、四层自检、卡兹克个人风格层。
- 新增"扩写纪律"小节。
- frontmatter 保留 `narrative_protocol.derived_from`。

- [ ] **步骤 1：修改输入章节**

在输入列表中增加：

```markdown
- `context.md.narrative_protocol`（新增）：当前风格模板的叙事协议
- `wechat-article-core/references/expansion-methodology.md`（新增，精简执行版）
- `wechat-article-core/references/writing-checklist.md`（新增，精简执行版）
- `wechat-article-core/references/writing-style.md`（新增，精简执行版）：通用活人感写作原则
- `context.md.selected_outline.sections[].materials_ref`（新增）：本 section 的素材支撑
- `context.md.selected_outline.sections[].human_needed`（新增）：本 section 必须用户补充的真实经历
```

- [ ] **步骤 2：删除第二步"明确 AI 的角色边界"**

直接删除整个第二步。将其中关于标注的规则移到第三步开头：

```markdown
### AI 填充标注规则

- 段落基于素材由 AI 填充：标注 `<!-- ai_filled -->`
- 段落需要用户补充真实经历：标注 `<!-- needs_human_experience -->`
```

- [ ] **步骤 3：删除第四步"四层自检体系"**

直接删除整个第四步。替换为：

```markdown
## 第四步：输出前轻量禁区扫描

在输出 `article_draft.md` 前，快速扫描：

1. 无 narrative_protocol.forbidden_zone 中的条目
2. 无 writing-checklist.md 中的通用禁用项
3. 无致命 AI 味模式（教科书开头、模糊归因、口号式结尾）

不输出质检报告，只保证不犯明显错误。完整质检由 `wechat-article-quality` 负责。
```

- [ ] **步骤 4：删除卡兹克个人风格层**

删除以下内容：

- 核心价值观 4 条
- 卡兹克专属口语化词组（如"太特么赤鸡了"、"不是哥们"）
- 具体情绪标点用法（如"。。。"、"???"、"= ="）
- 人物画像法、文化升维、亲自下场等绑定个人的表达

将通用活人感原则迁移到 `references/writing-style.md`：

- 节奏感（长短句、扣主线）
- 用具体细节支撑判断
- 敢下判断但保留灰度
- 理解对立面再给出视角
- 情绪从动作里出来
- 五感画面写实
- 认知迭代坦诚感
- 细节瑕疵留存感
- 分层降维通俗化

保留通用叙事技巧作为扩写纪律补充：

- 文章原型分类
- 结构模板
- 疑问句节奏
- 英雄之旅叙事弧
- 反向论证
- 案例人物公正性

- [ ] **步骤 5：在第三步开头新增"扩写纪律"小节**

在"第三步：写作"开头、"文章原型"之前插入：

```markdown
### 3.0 扩写纪律（执行时必须遵守）

每个 section 写作前，先回答：

1. **说话位置**
   - 本 section 谁在说话？凭什么知道？
   - 读者读完上一段会问什么？

2. **材料检查**
   - outline 里标注的 `materials_ref` 是否都已覆盖？
   - `must_include` 中哪些有素材？哪些缺？
   - 缺的只能：标注 `【需用户补充】` / 用已确认事实代替 / 缩短本 section

3. **推进检查**
   - 本段是否新增了至少一件事实、动作、例子或判断？
   - 下一段是否接住了本段留下的问题？
   - 没有同一观点换说法重复

4. **句法纪律**
   - 主干先行
   - 主语不重复
   - 抽象动作换成具体动作
   - 每个判断有细节托着
   - 情绪从动作里出来
   - 每段只完成一件事
   - 新段落增加新东西

5. **风格约束**
   - 遵守 `narrative_protocol.tone`
   - 遵守 `narrative_protocol.forbidden_zone`
   - 参考 `references/writing-style.md` 中的通用活人感原则

6. **禁区检查**
   - 无 narrative_protocol.forbidden_zone 中的条目
   - 无 writing-checklist.md 中的通用禁用项

7. **AI 味快速自检**
   - 不是太完整 / 太顺滑 / 太抽象 / 太客观 / 太会总结
```

- [ ] **步骤 6：修改输出章节**

在 frontmatter 要求中增加：

```markdown
- frontmatter 必须包含：
  - `title`：临时标题
  - `article_type`：文章类型
  - `emotion_tone`：情绪基调
  - `word_count`：目标字数
  - `target_reader`：目标读者
  - `narrative_protocol_derived_from`（新增）：如 `social-slice`
```

- [ ] **步骤 7：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/khazix-writer
git add SKILL.md
git commit -m "docs(khazix-writer): 去卡兹克风格绑定，按 narrative_protocol 和通用扩写纪律写作"
```

---

### 任务 10：更新 `wechat-article-polish/SKILL.md`

**文件：**
- 修改：`wechat-article-polish/SKILL.md`

**目标：**
- 输入增加 `narrative_protocol`、`ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md`。

- [ ] **步骤 1：修改输入章节**

```markdown
## 输入

- `context.md.draft_revised_path`：人二次改写后的正文文件路径
- `context.md.selected_outline`：选定大纲
- `context.md.selected_template`：模板规则
- `context.md.narrative_protocol`（新增）
- `wechat-article-core/references/ai-flavor-guide.md`（新增）
- `wechat-article-core/references/writing-checklist.md`（新增）
- `wechat-article-core/references/writing-style.md`（新增）
- references/writing-style.md
- references/content-principles-dbs.md
- references/emotion-trigger-system.md
- references/quality-checklist.md（问题清单，可选）
```

- [ ] **步骤 2：修改动作章节**

在动作中增加：

```markdown
3. 按 `narrative_protocol.tone` 和 `narrative_protocol.forbidden_zone` 调整语气，确保润色后不偏离模板约束。
4. 按 `ai-flavor-guide.md`、`writing-checklist.md` 和 `writing-style.md` 中的规则去除 AI 腔。
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-polish
git add SKILL.md
git commit -m "docs(polish): 增加 narrative_protocol 和扩写方法论输入"
```

---

### 任务 11：更新 `wechat-article-title/SKILL.md`

**文件：**
- 修改：`wechat-article-title/SKILL.md`

**目标：**
- 输入增加 `narrative_protocol.global_rules.opening`。

- [ ] **步骤 1：修改输入章节**

```markdown
## 输入

- 正文
- 模板规则
- `context.md.narrative_protocol.global_rules.opening`（新增）
- 情绪触发点
- mode 参数（article/subheading）
- references/bigpeng/title-formulas.md
- references/bigpeng/topic-templates.md
- references/bigpeng/title-corpus.md
- references/bigpeng/qa-checklist.md
```

- [ ] **步骤 2：修改 mode=article 动作**

增加：

```markdown
6. 标题必须符合作品模板的开头规则（如 `narrative_protocol.global_rules.opening` 要求从具体人物切入，则标题不应是宏大叙事式）。
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-title
git add SKILL.md
git commit -m "docs(title): 增加 narrative_protocol.opening 输入"
```

---

### 任务 12：更新 `wechat-article-quality/SKILL.md`

**文件：**
- 修改：`wechat-article-quality/SKILL.md`

**目标：**
- L1 检查增加模板专属禁区。
- 增加内容债/语言债诊断。
- 引入 `ai-flavor-guide.md`、`writing-checklist.md`、`writing-style.md`（完整版）作为验收标准。

- [ ] **步骤 1：修改输入章节**

```markdown
## 输入

- 最终标题
- 润色后正文
- 模板规则
- `context.md.narrative_protocol.forbidden_zone`（新增）
- `wechat-article-core/references/ai-flavor-guide.md`（新增，完整验收版）
- `wechat-article-core/references/writing-checklist.md`（新增，完整验收版）
- `wechat-article-core/references/writing-style.md`（新增，完整验收版）
- references/quality-checklist.md
- references/emotion-trigger-system.md
- references/writing-style.md
- references/content-principles-dbs.md
```

- [ ] **步骤 2：在 L1 检查中新增禁区检查**

```markdown
### L1-5 模板专属禁区检查

读取 `narrative_protocol.forbidden_zone`，全文搜索其中每条规则。
命中任何一条即视为 hard-fail。

示例（social-slice）：
- 第一人称"我""我们"
- "随着AI时代的到来"
- 二元对立结论
- 宏观叙事
```

- [ ] **步骤 3：在 L3 检查前新增内容债/语言债诊断**

```markdown
### L3-0 内容债 vs 语言债诊断

**内容债**：
- 缺事实、无真实例子
- 无观点
- 受众不清
- 判断无支撑

**语言债**：
- AI 套话
- 结构过分整齐
- 连接词过多
- 被动语态
- 升华式结尾
- 过度顺滑

处理策略：
- 内容债 → 标注【需补素材】，不硬编
- 语言债 → 按 writing-checklist.md 规则改写
```

- [ ] **步骤 4：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-quality
git add SKILL.md
git commit -m "docs(quality): 读取 narrative_protocol 模板禁区，增加内容债/语言债诊断"
```

---

### 任务 13：更新 `tests/test_core_stages.py`

**文件：**
- 修改：`wechat-article-core/tests/test_core_stages.py`

**目标：**
- 移除 `polish_confirmed` 要求，新增 `role_boundary` 要求。

- [ ] **步骤 1：修改测试**

```python
# tests/test_core_stages.py

def test_core_stages_include_human_review():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    required_stages = [
        "role_boundary",
        "draft_revised",
        "finalized",
    ]
    for stage in required_stages:
        assert stage in content, f"stage {stage} missing from SKILL.md"


def test_core_stages_removed_polish_confirmed():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "polish_confirmed" not in content, "polish_confirmed stage should be removed"
```

- [ ] **步骤 2：运行测试**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
python3 -m pytest tests/test_core_stages.py -v
```

预期：
- `test_core_stages_include_human_review` 在 SKILL.md 更新后 PASS
- `test_core_stages_removed_polish_confirmed` 在 SKILL.md 删除 `polish_confirmed` 后 PASS

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add tests/test_core_stages.py
git commit -m "test(core): 更新阶段检查：新增 role_boundary，移除 polish_confirmed"
```

---

### 任务 14：实现 `progress.md` 和 `blocked.md` 持久化逻辑

**文件：**
- 修改：`wechat-article-core/SKILL.md`
- 可选创建：`wechat-article-core/scripts/state_persistence.py`

**目标：**
- 定义 `progress.md` 和 `blocked.md` 的格式和更新时机。
- 持久化文件放在 `output_dir/<article_id>/` 根目录，与文章产物同目录。

- [ ] **步骤 1：在 SKILL.md 中新增持久化文件说明**

已在任务 5 中完成。

- [ ] **步骤 2（可选）：创建 state_persistence.py**

如果主 skill 直接维护文件，则不需要单独脚本。如果需要复用，可创建：

```python
# wechat-article-core/scripts/state_persistence.py

from pathlib import Path
from typing import Optional


def save_progress(output_dir: Path, stage: str, decisions: dict, risks: list):
    """保存当前进度到 output_dir/<article_id>/progress.md。"""
    progress_file = output_dir / "progress.md"
    lines = [f"# 写作进度\n", f"\n当前阶段：{stage}\n", "\n## 关键决策\n"]
    for key, value in decisions.items():
        lines.append(f"- {key}: {value}\n")
    lines.append("\n## 风险点\n")
    for risk in risks:
        lines.append(f"- {risk}\n")
    progress_file.write_text("".join(lines), encoding="utf-8")


def save_blocked(output_dir: Path, items: list):
    """保存阻塞项到 output_dir/<article_id>/blocked.md。"""
    blocked_file = output_dir / "blocked.md"
    lines = ["# 等待确认/补充\n\n"]
    for item in items:
        lines.append(f"- [ ] {item}\n")
    blocked_file.write_text("".join(lines), encoding="utf-8")
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add scripts/state_persistence.py
git commit -m "feat(core): 增加 progress/blocked 持久化脚本"
```

---

### 任务 15：实现版本自检逻辑

**文件：**
- 修改：`wechat-article-core/SKILL.md`
- 可选创建：`wechat-article-core/scripts/update_checker.py`

**目标：**
- 每 30 天检查一次远程仓库更新。

- [ ] **步骤 1：在 SKILL.md 中新增版本自检说明**

已在任务 5 中完成。

- [ ] **步骤 2（可选）：创建 update_checker.py**

```python
# wechat-article-core/scripts/update_checker.py

import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def check_for_updates(skill_dir: Path) -> dict:
    """检查本地 skill 是否落后于远程仓库。"""
    last_check_file = skill_dir / ".last-update-check"
    now = datetime.now()

    if last_check_file.exists():
        last_check = datetime.fromtimestamp(last_check_file.stat().st_mtime)
        if now - last_check < timedelta(days=30):
            return {"status": "skipped", "reason": "最近 30 天内已检查"}

    last_check_file.touch()

    try:
        subprocess.run(["git", "fetch", "origin"], cwd=skill_dir, check=True, capture_output=True)
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=skill_dir, check=True, capture_output=True, text=True
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "rev-parse", "origin/HEAD"], cwd=skill_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        if local != remote:
            return {"status": "behind", "local": local, "remote": remote}
        return {"status": "up_to_date"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

- [ ] **步骤 3：Commit**

```bash
cd /home/user/.claude/skills/agents-bridge/skills/wechat-article-core
git add scripts/update_checker.py
git commit -m "feat(core): 增加版本自检脚本"
```

---

## 三、自检

### 规格覆盖度

| 规格需求 | 实现任务 |
|---------|---------|
| 素材全读 | 任务 1 |
| 结构化 materials_summary | 任务 1、5 |
| narrative_protocol 提取 | 任务 2 |
| 新增 expansion-methodology.md | 任务 4 |
| 新增 ai-flavor-guide.md | 任务 4 |
| 新增 writing-checklist.md | 任务 4 |
| 更新 writing-style.md（去卡兹克个人绑定） | 任务 4 |
| clarify 调整为需求确认 + 素材完整性确认 | 任务 6 |
| angle 基于完整素材和 narrative_protocol | 任务 7 |
| 大纲按 narrative_protocol 生成 | 任务 8 |
| 大纲 section 增加素材映射 | 任务 8 |
| 正文按 narrative_protocol 写作 | 任务 9 |
| khazix-writer 删除重复角色边界 | 任务 9 |
| khazix-writer 删除重复四层自检 | 任务 9 |
| khazix-writer 删除卡兹克个人风格绑定 | 任务 9 |
| polish 读取 narrative_protocol 和 AI 味指南 | 任务 10 |
| title 读取 narrative_protocol.opening | 任务 11 |
| quality 读取模板禁区 | 任务 12 |
| quality 增加内容债/语言债诊断 | 任务 12 |
| role_boundary 阻塞确认 | 任务 5 |
| 精简流程（去掉 polish_confirmed） | 任务 5、13 |
| 输出目录结构化 | 任务 5 |
| 文件持久化（progress/blocked 在 output_dir/<article_id>/ 根目录） | 任务 14 |
| 版本自检 | 任务 15 |
| 素材递归开关 | 任务 1、3 |

### 占位符扫描

- 无 "TODO"、"待定"、"后续实现"。
- 每个代码步骤包含完整代码。
- 每个测试步骤包含完整断言。

### 类型一致性

- `summarize_materials` 返回 dict，字段名为 `fully_loaded`、`total_files`、`total_chars`、`files`、`summary_text`、`materials_path`。
- `extract_narrative_protocol` 返回 dict，字段名为 `derived_from`、`sections`、`global_rules`、`tone`、`forbidden_zone`。
- `sections` 中每个 section 包含 `name`、`purpose`、`length`、`must_include`、`forbidden`、`template`。
- `outline_candidates[].sections` 增加 `materials_ref`、`human_needed`、`word_count_estimate`。
- `requirements` 增加 `speaker_position`（含 `who`、`credential`、`trigger`）。
- `collaboration_charter` 字段保持一致。
- 正文 frontmatter 增加 `narrative_protocol_derived_from`（字符串，值为 narrative_protocol.derived_from）。

---

## 四、执行方式

**计划已完成并保存到 `docs/superpowers/plans/2026-08-25-wechat-article-core-optimization-plan.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 `superpowers:executing-plans` 执行任务，批量执行并设有检查点

**选哪种方式？**
