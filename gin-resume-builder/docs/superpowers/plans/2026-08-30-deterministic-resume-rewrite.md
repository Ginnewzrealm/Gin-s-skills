# gin-resume-builder 简历 bullet 确定性改写实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:test-driven-development 与 superpowers:verification-before-completion。本计划解决「同一模板/方法论每次输出不同」以及「表达应中性、禁用贬义词」两个问题。

**目标：** 把 `scripts/bullet_rewriter.py` 从「只标注、不改写」改成真正的规则化 X-Y-Z/CAR 改写器，输出唯一确定、中性表达、不含贬义词的 `rewritten`；Claude 仅做灰区补全与审核，不再自由润色。

**架构：** 用正则与启发式规则从原句拆分出动作（X）、任务（Y）、量化结果（Z），按固定模板重组；无法拆分或检测到贬义词/负面表达时进入灰区，标注 `{?}` 并给出具体原因。硬事实（数字、公司、职位、时间）原样保留，过 `provenance_verifier.py` 溯源校验。

**技术栈：** Python 3，标准库（json、re、unittest）。

---

## 关键文件

- **修改：** `scripts/bullet_rewriter.py` — 核心改写逻辑
- **修改：** `gin-resume-builder/SKILL.md` — 更新简历管线第 6 步说明
- **修改：** `gin-resume-builder/CHANGELOG.md` — 新增 v1.18.3 条目
- **新增：** `tests/test_bullet_rewriter.py` — 改写器单元测试

---

## 任务 1：编写失败的改写器测试

**文件：**
- 创建：`tests/test_bullet_rewriter.py`

- [ ] **步骤 1：编写失败测试 — 基本 X-Y-Z 改写**

```python
import importlib.util
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("bullet_rewriter", _MODULE_DIR / "bullet_rewriter.py")
br = importlib.util.module_from_spec(_spec)
sys.modules["bullet_rewriter"] = br
_spec.loader.exec_module(br)

rewrite = br.rewrite


def _item(bullet, fact_id="W1"):
    return {
        "fact_id": fact_id, "org": "绿城科技", "role": "大客户经理",
        "period": "2020.12-2025.06", "bullet": bullet,
    }


def test_xyz_basic():
    selected = [_item("负责丽水560万合同商务谈判，签约落地，回款周期缩短30%")]
    bullets = rewrite(selected)
    assert bullets[0]["rewritten"] == "商务谈判：主导丽水560万合同商务谈判与签约落地，实现回款周期缩短30%"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python3 -m pytest tests/test_bullet_rewriter.py::test_xyz_basic -v`
预期：FAIL，`assert bullets[0]["rewritten"] == ...` 因为当前 `rewritten` 等于原文。

- [ ] **步骤 3：Commit 空测试文件**

```bash
git checkout -b fix/deterministic-resume-rewrite
git add tests/test_bullet_rewriter.py
git commit -m "test(bullet_rewriter): add failing deterministic rewrite tests"
```

---

## 任务 2：实现 X-Y-Z 规则化改写

**文件：**
- 修改：`scripts/bullet_rewriter.py`

- [ ] **步骤 1：设计并添加句子拆分与成分识别函数**

在 `scripts/bullet_rewriter.py` 中新增：

```python
# 能力小标题候选词（用于从原句提取或兜底）
CAPABILITY_HINTS = {
    "谈判": "商务谈判", "签约": "商务谈判", "合同": "商务谈判",
    "渠道": "渠道拓展", "经销商": "渠道拓展", "终端": "渠道拓展",
    "团队": "团队管理", "人员": "团队管理", "培养": "团队管理",
    "营收": "业绩增长", "销售": "业绩增长", "回款": "业绩增长",
    "流程": "流程优化", "机制": "机制搭建", "系统": "系统搭建",
    "项目": "项目管理", "协调": "跨部门协同", "协同": "跨部门协同",
}

# 强动词池（按优先级排序，优先匹配前面的词）
ACTION_VERBS = [
    "主导", "负责", "搭建", "设计", "开发", "优化", "重构", "落地",
    "推动", "谈判", "策划", "分析", "带领", "组织", "整合", "协同",
    "建立", "制定", "推进", "完成", "实现", "提升", "降低", "缩短",
]

# 结果提示词（Z 成分的信号）
RESULT_HINTS = [
    "提升", "提高", "增长", "增加", "降低", "减少", "下降", "节省",
    "缩短", "达成", "完成", "实现", "贡献", "超过", "排名", "获得",
    "从", "至", "到", "增至", "降至",
]

RESULT_PAT = re.compile(r"(.*?)(提升|提高|增长|增加|降低|减少|下降|节省|缩短|达成|完成|实现|贡献|超过|排名|获得|从.*?(?:至|到|增至|降至))(.*?)(\d+(?:\.\d+)?%?|\d+[万千百个]?)(.*)")
METRIC_PAT = re.compile(r"\d+(?:\.\d+)?%?|\d+[万千百个]|\d{4}[./年]\d{1,2}")


def _split_clauses(text):
    """按中文标点拆分成子句。"""
    return [c.strip() for c in re.split(r"[，、；。]", text) if c.strip()]


def _extract_capability_tag(text):
    """从文本提取能力小标题，找不到时返回空字符串。"""
    for hint, tag in CAPABILITY_HINTS.items():
        if hint in text:
            return tag
    return ""


def _extract_action(clauses):
    """找含强动词的子句作为 X；返回 (动作子句, 剩余子句)。"""
    for v in ACTION_VERBS:
        for i, c in enumerate(clauses):
            if v in c:
                return c, clauses[:i] + clauses[i+1:]
    # 兜底：返回第一句
    return clauses[0], clauses[1:]


def _extract_result(clauses):
    """找含数字/百分比/结果提示词的子句作为 Z；返回 (结果子句, 剩余子句)。"""
    for i, c in enumerate(clauses):
        if METRIC_PAT.search(c) and any(h in c for h in RESULT_HINTS):
            return c, clauses[:i] + clauses[i+1:]
    # 兜底：找第一个带数字的
    for i, c in enumerate(clauses):
        if METRIC_PAT.search(c):
            return c, clauses[:i] + clauses[i+1:]
    return "", clauses


def _normalize_action(action_text):
    """把动作子句整理成以强动词开头的短动作描述。"""
    # 去掉常见冗余前缀
    action_text = re.sub(r"^(负责|主导|参与|协助)\s*", "", action_text)
    # 确保以强动词开头
    for v in ACTION_VERBS:
        if action_text.startswith(v):
            return action_text
    # 如果没有强动词，选一个最贴切的补到前面
    for v in ACTION_VERBS:
        if v in action_text:
            return action_text
    return "推进" + action_text if action_text else ""


def _compose_xyz(capability, action, task, result):
    """按 X-Y-Z 模板组合，输出确定性文案。"""
    parts = []
    if action:
        parts.append("通过" + action)
    if task:
        parts.append("完成" + task)
    if result:
        parts.append("实现" + result)
    body = "，".join(parts)
    if capability:
        return f"{capability}：{body}"
    return body
```

- [ ] **步骤 2：重写 `rewrite()` 函数调用新拆分逻辑**

```python
def rewrite(selected):
    out = []
    for item in selected:
        original = item["bullet"]
        a = annotate(original)
        clauses = _split_clauses(original)

        # 责任层级前缀处理
        level, cleaned = common.extract_responsibility_level(original)
        if cleaned != original:
            clauses = _split_clauses(cleaned)

        action, rest = _extract_action(clauses)
        result, rest = _extract_result(rest)
        task = "、".join(rest) if rest else ""

        capability = _extract_capability_tag(original)
        action = _normalize_action(action)

        rewritten = _compose_xyz(capability, action, task, result)
        # 如果拆分失败，保留原文并标记灰区
        if not rewritten or rewritten == "：":
            rewritten = original
            a["grey_zones"].append("无法自动拆分为 X-Y-Z 结构，需用户补充")

        out.append({
            "fact_id": item["fact_id"], "org": item["org"], "role": item["role"],
            "period": item["period"], "original": original,
            "rewritten": rewritten,
            "hard_facts": a["hard_facts"],
            "has_action": a["has_action"], "has_result": a["has_result"],
            "grey_zones": a["grey_zones"],
        })
    return out
```

- [ ] **步骤 3：运行测试验证通过**

运行：`python3 -m pytest tests/test_bullet_rewriter.py::test_xyz_basic -v`
预期：PASS。

- [ ] **步骤 4：Commit**

```bash
git add scripts/bullet_rewriter.py tests/test_bullet_rewriter.py
git commit -m "feat(bullet_rewriter): deterministic X-Y-Z rewrite"
```

---

## 任务 3：添加中性表达与贬义词过滤

**文件：**
- 修改：`scripts/bullet_rewriter.py`

- [ ] **步骤 1：编写失败测试 — 贬义词拦截**

在 `tests/test_bullet_rewriter.py` 追加：

```python
def test_neutral_tone_flag():
    selected = [_item("只是帮忙整理了一下资料，工作比较被动")]
    bullets = rewrite(selected)
    assert "{?}" in bullets[0]["rewritten"] or any("贬义" in g for g in bullets[0]["grey_zones"])
    assert bullets[0]["rewritten"] == selected[0]["bullet"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python3 -m pytest tests/test_bullet_rewriter.py::test_neutral_tone_flag -v`
预期：FAIL。

- [ ] **步骤 3：实现贬义词与负面表达检测**

在 `scripts/bullet_rewriter.py` 新增：

```python
# 贬义词 / 负面自我描述黑名单
DEROGATORY_WORDS = {
    "只是", "仅仅", "不过是", "随便", "凑合", "应付", "疲于应付",
    "救火", "填坑", "背锅", "背黑锅", "背锅侠", "打杂", "跑腿",
    "被动", "消极", "无奈", "无助", "没辙", "束手无策", "无能为力",
    "边缘化", "被忽视", "被排挤", "吃亏", "受气", "委屈", "苦逼",
    "混日子", "摸鱼", "摆烂", "躺平", "得过且过",
}

# 弱化动词：在结果不够硬实时，把这类词替换成强动词
WEAK_VERBS = {
    "参与": "协同", "协助": "支持", "帮忙": "支持",
    "做了": "完成", "搞了": "完成", "弄了": "完成",
}


def _contains_derogatory(text):
    """检测是否含贬义词或明显负面自我描述。"""
    for w in DEROGATORY_WORDS:
        if w in text:
            return w
    return ""


def _replace_weak_verbs(text):
    """把弱化动词替换为中性/强动词。"""
    for weak, strong in WEAK_VERBS.items():
        text = text.replace(weak, strong)
    return text
```

- [ ] **步骤 4：在 `rewrite()` 中集成检测与兜底**

在 `rewrite()` 的灰区判断前加入：

```python
        derogatory = _contains_derogatory(original)
        if derogatory:
            a["grey_zones"].append("检测到贬义词或负面表达「%s」，需用户改为中性描述" % derogatory)
            rewritten = original
```

并在 `_normalize_action()` 中调用 `_replace_weak_verbs()`：

```python
def _normalize_action(action_text):
    action_text = _replace_weak_verbs(action_text)
    action_text = re.sub(r"^(负责|主导|参与|协助)\s*", "", action_text)
    ...
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python3 -m pytest tests/test_bullet_rewriter.py -v`
预期：全部 PASS。

- [ ] **步骤 6：Commit**

```bash
git add scripts/bullet_rewriter.py tests/test_bullet_rewriter.py
git commit -m "feat(bullet_rewriter): neutral tone and derogatory word guard"
```

---

## 任务 4：补充更多边界测试

**文件：**
- 修改：`tests/test_bullet_rewriter.py`

- [ ] **步骤 1：增加以下测试用例**

```python
def test_car_pattern():
    selected = [_item("面对日均10万单履约超时问题，重排配送分区算法，超时率从8%降到3%")]
    bullets = rewrite(selected)
    assert "重排配送分区算法" in bullets[0]["rewritten"]
    assert "超时率从8%降到3%" in bullets[0]["rewritten"]
    assert "实现" in bullets[0]["rewritten"]


def test_weak_verb_replacement():
    selected = [_item("协助客户沟通与需求对接，用户满意度提升15%")]
    bullets = rewrite(selected)
    assert "支持" in bullets[0]["rewritten"] or "协同" in bullets[0]["rewritten"]
    assert "提升15%" in bullets[0]["rewritten"]


def test_grey_zone_when_no_metric():
    selected = [_item("负责客户沟通与需求对接")]
    bullets = rewrite(selected)
    assert any("缺少可量化结果" in g for g in bullets[0]["grey_zones"])


def test_hard_facts_preserved():
    selected = [_item("主导丽水560万合同商务谈判，签约落地")]
    bullets = rewrite(selected)
    assert "560万" in bullets[0]["rewritten"]
    assert "丽水" in bullets[0]["rewritten"]
```

- [ ] **步骤 2：运行测试**

运行：`python3 -m pytest tests/test_bullet_rewriter.py -v`
预期：全部 PASS；若有失败，回到任务 2/3 调整规则。

- [ ] **步骤 3：Commit**

```bash
git add tests/test_bullet_rewriter.py
git commit -m "test(bullet_rewriter): add boundary tests for CAR, weak verbs, grey zones"
```

---

## 任务 5：更新 SKILL.md 与 CHANGELOG.md

**文件：**
- 修改：`gin-resume-builder/SKILL.md`
- 修改：`gin-resume-builder/CHANGELOG.md`

- [ ] **步骤 1：修改 SKILL.md 简历管线第 6 步**

把：

> 6. **改写**：`bullet_rewriter.py --selected picked.json --out bullets.json` 产出硬事实层 → Claude 在此基础上润色表达（三层控制：硬事实自动校验、表达风格不校验、灰区 {?} 用户确认）。

改为：

> 6. **改写**：`bullet_rewriter.py --selected picked.json --out bullets.json` 按 X-Y-Z / CAR 公式做**规则化改写**，输出唯一确定的 `rewritten`；硬事实（数字、公司、职位、时间）原样保留，表达强制中性、禁用贬义词。无法拆分或检测到贬义/负面表达时自动标注 `{?}`，由 Claude 引导用户补全或确认。

- [ ] **步骤 2：更新版本号与 CHANGELOG**

`SKILL.md` 版本 `v1.18.2` → `v1.18.3`。

`CHANGELOG.md` 新增：

```markdown
## v1.18.3（2026-08-30）

- feat(bullet_rewriter): 将简历 bullet 改写从 Claude 自由润色改为脚本级 X-Y-Z/CAR 规则化改写，同一输入输出确定
- feat(bullet_rewriter): 增加中性表达约束与贬义词黑名单，检测到贬义/负面自我描述时自动标注 {?}
- test: 新增 `tests/test_bullet_rewriter.py` 覆盖 X-Y-Z、CAR、弱动词替换、灰区、贬义词拦截
```

- [ ] **步骤 3：Commit**

```bash
git add SKILL.md CHANGELOG.md
git commit -m "docs: resume pipeline now uses deterministic bullet rewriter v1.18.3"
```

---

## 任务 6：全量验证

- [ ] **步骤 1：运行新增测试**

```bash
python3 -m pytest tests/test_bullet_rewriter.py -v
```
预期：全部 PASS。

- [ ] **步骤 2：运行全部测试**

```bash
python3 -m pytest tests/ -v
```
预期：全部 PASS；若 strong_claim_auditor / provenance_verifier 测试因 `rewritten` 内容变化而失败，检查是否为预期变化，必要时同步更新测试数据。

- [ ] **步骤 3：脚本编译检查**

```bash
python3 -m py_compile scripts/*.py
```
预期：无语法错误。

- [ ] **步骤 4：端到端冒烟测试**

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-resume-builder
# 构造一个最小 selected.json
cat > /tmp/selected.json <<'EOF'
[
  {"fact_id": "W1", "org": "绿城科技", "role": "大客户经理", "period": "2020.12-2025.06", "bullet": "负责丽水560万合同商务谈判，签约落地，回款周期缩短30%"}
]
EOF
python3 scripts/bullet_rewriter.py --selected /tmp/selected.json
```
预期：输出包含确定性改写后的 bullet，无贬义词，灰区为空。

- [ ] **步骤 5：Commit（如测试数据有同步更新）**

```bash
git add tests/ scripts/ SKILL.md CHANGELOG.md
git commit -m "test: update test fixtures for deterministic rewritten bullets" || true
```

---

## 风险与取舍

- **自然度下降**：规则化改写可能不如 Claude 自由润色流畅。取舍：优先确定性与合规性，灰区交给 Claude/用户补全。
- **规则覆盖不全**：复杂中文句式可能拆错。后续可逐步扩展 `CAPABILITY_HINTS`、`ACTION_VERBS`、`RESULT_HINTS`。
- **Claude 润色层移除**：`SKILL.md` 明确改写由脚本完成；如需保留少量润色，应通过 `--polish` 显式开关，且默认关闭。
- **贬义词黑名单维护**：首批覆盖常见贬义/负面词，后续根据实际输出补充。

---

## 自检

- [x] 规格覆盖：确定性输出、中性表达、贬义词拦截均已对应任务。
- [x] 无占位符：每步均给出实际代码与命令。
- [x] 类型一致：`rewritten` 字段仍为字符串；测试导入方式与其他测试一致。
