# 知识库对话内容硬闸门持久化 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让 Agent 与用户对话中挖掘/整理出的经历事实，必须先展示给用户确认，再写入知识库，并提供可核查的写入反馈与审计命令。

**架构：** 在知识库 `原始事实/` 下新增 `待确认/` 暂存区，Agent 先调用 `stage-evidence` 把整理稿写成预览文件，用户确认后再调用 `confirm-evidence` 迁移到 `behavioral_evidence/`；同时新增 `kb_audit.py` 供用户/Agent 验证知识库结构和最近写入。

**技术栈：** Python 标准库、`scripts/mining/evidence_store.py` 现有写入能力、Markdown + JSON 双文件预览。

---

## 文件职责

| 文件 | 职责 |
|---|---|
| `scripts/common.py` | 新增 `DIR_STAGED` 常量，指向 `原始事实/待确认` |
| `scripts/staged_evidence.py` | 新增：暂存、确认、拒绝、列出预览证据 |
| `scripts/kb_interview.py` | 新增 `stage-evidence`、`confirm-evidence`、`reject-evidence`、`list-staged` 子命令 |
| `scripts/kb_audit.py` | 新增：审计知识库结构、统计、最近写入、滞留预览 |
| `tests/test_staged_evidence.py` | 测试暂存区生命周期 |
| `tests/test_kb_audit.py` | 测试审计报告 |
| `SKILL.md` | 更新 STAR 行为证据挖掘流程为"展示 → 确认 → 写入 → 审计" |
| `references/tacit-mining-methodology.md` | 新增 stage/confirm/reject 命令示例与确认话术 |

---

## 任务 1：在 common.py 中注册待确认目录

**文件：**
- 修改：`scripts/common.py:21`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_common_staged_dir.py`：

```python
#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "common", Path(__file__).parent.parent / "scripts" / "common.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["common"] = mod
spec.loader.exec_module(mod)


def test_staged_dir_constant_exists():
    assert hasattr(mod, "DIR_STAGED")
    assert mod.DIR_STAGED == "待确认"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd /Users/fubo/Downloads/Gin-s-skills-work/gin-resume-builder
python3 -m pytest tests/test_common_staged_dir.py -v
```

预期：FAIL，`AttributeError: module 'common' has no attribute 'DIR_STAGED'`

- [ ] **步骤 3：实现常量**

在 `scripts/common.py` 第 21 行后插入：

```python
DIR_STAGED = "待确认"
```

- [ ] **步骤 4：运行测试验证通过**

```bash
python3 -m pytest tests/test_common_staged_dir.py -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add scripts/common.py tests/test_common_staged_dir.py
git commit -m "feat(kb): add DIR_STAGED constant for pending evidence"
```

---

## 任务 2：实现 staged_evidence.py 模块

**文件：**
- 创建：`scripts/staged_evidence.py`
- 修改：`scripts/mining/evidence_store.py`（可选，保持独立）

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_staged_evidence.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_staged_evidence.py — 暂存证据生命周期测试。"""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "staged_evidence", Path(__file__).parent.parent / "scripts" / "staged_evidence.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["staged_evidence"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_stage_creates_markdown_and_json(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层", "配客户经理"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        verbatim="当时发现只看GMV会漏掉高活跃小体量商户",
    )
    staged_dir = tmp_path / "原始事实" / "待确认"
    md = staged_dir / "%s.md" % sid
    js = staged_dir / "%s.json" % sid
    assert md.exists()
    assert js.exists()
    assert "商户分层运营" in md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["domain"] == "work_experience"
    assert data["star"]["Result"] == "80万→110万"


def test_confirm_moves_to_behavioral_evidence(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        verbatim="原话",
    )
    name = store.confirm(sid)
    assert name.startswith("be_work_experience_")
    evidence_dir = tmp_path / "原始事实" / "behavioral_evidence"
    assert (evidence_dir / "%s.md" % name).exists()
    assert not (tmp_path / "原始事实" / "待确认" / "%s.md" % sid).exists()
    assert not (tmp_path / "原始事实" / "待确认" / "%s.json" % sid).exists()


def test_reject_deletes_preview_files(tmp_path):
    root = _make_kb(tmp_path)
    store = mod.StagedEvidenceStore(root)
    sid = store.stage(
        domain="project_experience",
        source="增长项目",
        description="测试",
        background="背景",
        task="任务",
        actions=["行动"],
        result="结果",
        insight="判断",
        boundary="边界",
        verbatim="",
    )
    store.reject(sid)
    staged_dir = tmp_path / "原始事实" / "待确认"
    assert len(list(staged_dir.iterdir())) == 0
```

- [ ] **步骤 2：运行测试验证失败**

```bash
python3 -m pytest tests/test_staged_evidence.py -v
```

预期：3 个 FAIL，因为 `scripts/staged_evidence.py` 不存在。

- [ ] **步骤 3：实现模块**

创建 `scripts/staged_evidence.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""staged_evidence.py — 待确认证据暂存区管理。

Agent 先把整理好的 STAR 写入 `原始事实/待确认/`，等用户确认后再迁移到
`behavioral_evidence/`。这样用户可以随时打开预览文件检查实际文字。
"""
import json
import os
import re
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from mining.evidence_store import EvidenceStore


class StagedEvidenceStore:
    """管理 `原始事实/待确认/` 目录。"""

    DIR_NAME = common.DIR_STAGED

    def __init__(self, root):
        self.root = root
        self.dir_path = os.path.join(root, common.DIR_RAW, self.DIR_NAME)
        os.makedirs(self.dir_path, exist_ok=True)

    def _next_seq(self, domain):
        pattern = re.compile(r"^st_%s_(\d{3})\.md$" % re.escape(domain))
        max_n = 0
        for name in os.listdir(self.dir_path):
            m = pattern.match(name)
            if m:
                max_n = max(max_n, int(m.group(1)))
        return max_n + 1

    def stage(self, domain, source, description, background, task, actions,
              result, insight, boundary, confidence="preview", verbatim=""):
        """写入预览 Markdown + JSON 侧载，返回 staged_id。"""
        seq = self._next_seq(domain)
        sid = "st_%s_%03d" % (domain, seq)
        md_path = os.path.join(self.dir_path, "%s.md" % sid)
        json_path = os.path.join(self.dir_path, "%s.json" % sid)

        star = {
            "Background": background,
            "Task": task,
            "Action": list(actions),
            "Result": result,
            "Key Insight": insight,
            "Boundary": boundary,
        }

        md_lines = [
            "---",
            "staged_id: %s" % sid,
            "description: %s" % description,
            "type: staged",
            "domain: %s" % domain,
            "source: %s" % source,
            "confidence: %s" % confidence,
            "created: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
            "---",
            "",
            "## 背景（Background）",
            background,
            "",
            "## 任务（Task）",
            task,
            "",
            "## 行动（Action）",
        ]
        for a in star["Action"]:
            md_lines.append("- %s" % a)
        md_lines.extend([
            "",
            "## 结果（Result）",
            result,
            "",
            "## 关键判断（Key Insight）",
            insight,
            "",
            "## 边界条件（Boundary）",
            boundary,
            "",
            "## 原话（Verbatim）",
            "> %s" % verbatim if verbatim else "> （无）",
            "",
            "> 状态：待确认。回复 OK 后 Agent 将把它写入 `原始事实/behavioral_evidence/`。",
        ])

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        payload = {
            "staged_id": sid,
            "domain": domain,
            "description": description,
            "source": source,
            "confidence": confidence,
            "verbatim": verbatim,
            "star": star,
            "created": datetime.now().isoformat(),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return sid

    def list_staged(self):
        """返回所有待确认条目列表（元组：staged_id, description, created）。"""
        items = []
        for name in sorted(os.listdir(self.dir_path)):
            if not name.endswith(".json"):
                continue
            json_path = os.path.join(self.dir_path, name)
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            items.append((data["staged_id"], data["description"], data.get("created", "")))
        return items

    def confirm(self, staged_id):
        """把指定预览迁移到 behavioral_evidence/，并删除预览文件。"""
        json_path = os.path.join(self.dir_path, "%s.json" % staged_id)
        md_path = os.path.join(self.dir_path, "%s.md" % staged_id)
        if not os.path.exists(json_path):
            raise FileNotFoundError("待确认证据不存在：%s" % staged_id)

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        store = EvidenceStore(self.root)
        name = store.save(
            domain=data["domain"],
            description=data["description"],
            source=data["source"],
            star=data["star"],
            confidence="confirmed",
            verbatim=data.get("verbatim", ""),
        )

        os.remove(json_path)
        os.remove(md_path)
        return name

    def reject(self, staged_id):
        """用户拒绝，删除预览文件。"""
        for ext in (".md", ".json"):
            path = os.path.join(self.dir_path, "%s%s" % (staged_id, ext))
            if os.path.exists(path):
                os.remove(path)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
python3 -m pytest tests/test_staged_evidence.py -v
```

预期：3 个 PASS

- [ ] **步骤 5：Commit**

```bash
git add scripts/staged_evidence.py tests/test_staged_evidence.py
git commit -m "feat(kb): add staged evidence store with confirm/reject lifecycle"
```

---

## 任务 3：在 kb_interview.py 中暴露 stage/confirm/reject/list 命令

**文件：**
- 修改：`scripts/kb_interview.py`
- 修改：`scripts/common.py`（`KB_COMMANDS`）

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_kb_interview_stage.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_interview", Path(__file__).parent.parent / "scripts" / "kb_interview.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_interview"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_cmd_stage_evidence_creates_preview(tmp_path):
    root = _make_kb(tmp_path)
    sid = mod.cmd_stage_evidence(
        root=root,
        domain="work_experience",
        source="美团-高级产品经理",
        description="商户分层运营",
        background="增长停滞",
        task="提升月活",
        actions=["重新分层"],
        result="80万→110万",
        insight="活跃度比GMV重要",
        boundary="头部必须人工",
        verbatim="原话",
    )
    assert sid.startswith("st_work_experience_")
    assert (tmp_path / "原始事实" / "待确认" / "%s.md" % sid).exists()


def test_cmd_confirm_evidence_writes_and_cleans(tmp_path):
    root = _make_kb(tmp_path)
    sid = mod.cmd_stage_evidence(root=root, domain="work_experience", source="s", description="d",
                                  background="b", task="t", actions=["a"], result="r",
                                  insight="i", boundary="b2", verbatim="v")
    name = mod.cmd_confirm_evidence(root, sid)
    assert name.startswith("be_work_experience_")
    assert (tmp_path / "原始事实" / "behavioral_evidence" / "%s.md" % name).exists()
    assert not (tmp_path / "原始事实" / "待确认" / "%s.md" % sid).exists()
```

- [ ] **步骤 2：运行测试验证失败**

```bash
python3 -m pytest tests/test_kb_interview_stage.py -v
```

预期：FAIL，`AttributeError: module 'kb_interview' has no attribute 'cmd_stage_evidence'`

- [ ] **步骤 3：实现命令函数和 CLI**

在 `scripts/kb_interview.py` 中：

1. 导入 `StagedEvidenceStore`：

```python
from staged_evidence import StagedEvidenceStore
```

2. 在 `common.KB_COMMANDS` 中新增：

```python
"stage-evidence": "把整理好的 STAR 证据先写入待确认区",
"confirm-evidence": "把待确认证据迁移到 behavioral_evidence/",
"reject-evidence": "删除待确认证据",
"list-staged": "列出待确认证据",
```

3. 新增命令函数：

```python
def cmd_stage_evidence(root, domain, source, description, background, task,
                       actions, result, insight, boundary, verbatim=""):
    store = StagedEvidenceStore(root)
    sid = store.stage(
        domain=domain,
        source=source,
        description=description,
        background=background,
        task=task,
        actions=actions,
        result=result,
        insight=insight,
        boundary=boundary,
        verbatim=verbatim,
    )
    print("[预览] 已写入待确认区：原始事实/待确认/%s.md" % sid)
    print("请查看内容后回复 OK 以保存，或告诉我修改意见。")
    return sid


def cmd_confirm_evidence(root, staged_id):
    store = StagedEvidenceStore(root)
    name = store.confirm(staged_id)
    _, ver = facts_parser.post_write(root, "确认并保存行为证据：%s" % name)
    print("[完成] 已写入知识库：原始事实/behavioral_evidence/%s.md" % name)
    print("知识库版本：v%d" % ver)
    return name


def cmd_reject_evidence(root, staged_id):
    store = StagedEvidenceStore(root)
    store.reject(staged_id)
    print("[已忽略] 待确认证据 %s 已删除" % staged_id)


def cmd_list_staged(root):
    store = StagedEvidenceStore(root)
    items = store.list_staged()
    if not items:
        print("待确认区为空")
        return
    print("待确认证据：")
    for sid, desc, created in items:
        print("  - %s：%s（%s）" % (sid, desc, created))
```

4. 在 `main()` 的 argparse 中加入参数：

```python
ap.add_argument("--background", default="", help="stage-evidence 专用：背景")
ap.add_argument("--task", default="", help="stage-evidence 专用：任务")
ap.add_argument("--action", action="append", default=[], help="stage-evidence 专用：行动（可重复）")
ap.add_argument("--result", default="", help="stage-evidence 专用：结果")
ap.add_argument("--insight", default="", help="stage-evidence 专用：关键判断")
ap.add_argument("--boundary", default="", help="stage-evidence 专用：边界条件")
ap.add_argument("--verbatim", default="", help="stage-evidence 专用：用户原话")
ap.add_argument("--staged-id", default="", help="confirm-evidence / reject-evidence 专用：staged_id")
```

5. 在命令分发中加入：

```python
elif args.command == "stage-evidence":
    cmd_stage_evidence(
        root=root,
        domain=args.domain,
        source=args.source,
        description=args.description,
        background=args.background,
        task=args.task,
        actions=args.action,
        result=args.result,
        insight=args.insight,
        boundary=args.boundary,
        verbatim=args.verbatim,
    )
elif args.command == "confirm-evidence":
    cmd_confirm_evidence(root, args.staged_id)
elif args.command == "reject-evidence":
    cmd_reject_evidence(root, args.staged_id)
elif args.command == "list-staged":
    cmd_list_staged(root)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
python3 -m pytest tests/test_kb_interview_stage.py -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add scripts/common.py scripts/kb_interview.py tests/test_kb_interview_stage.py
git commit -m "feat(kb): expose stage/confirm/reject/list-staged commands"
```

---

## 任务 4：实现 kb_audit.py 审计命令

**文件：**
- 创建：`scripts/kb_audit.py`
- 创建：`tests/test_kb_audit.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_kb_audit.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_audit", Path(__file__).parent.parent / "scripts" / "kb_audit.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_audit"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def test_audit_reports_basic_counts(tmp_path):
    root = _make_kb(tmp_path)
    (tmp_path / "原始事实" / "basic_info.md").write_text("- 姓名: 张三\n", encoding="utf-8")
    (tmp_path / "原始事实" / "work_history.md").write_text("## 美团 | PM | 2024-至今\n- 负责增长\n", encoding="utf-8")
    (tmp_path / "原始事实" / "behavioral_evidence").mkdir()
    (tmp_path / "原始事实" / "behavioral_evidence" / "be_work_experience_001.md").write_text("test", encoding="utf-8")

    report = mod.audit(root)
    assert report["structure_ok"] is True
    assert report["counts"]["raw_files"] == 2
    assert report["counts"]["behavioral_evidence"] == 1
    assert report["counts"]["staged"] == 0


def test_audit_flags_missing_structure(tmp_path):
    root = str(tmp_path)
    report = mod.audit(root)
    assert report["structure_ok"] is False
    assert any("原始事实" in issue for issue in report["issues"])
```

- [ ] **步骤 2：运行测试验证失败**

```bash
python3 -m pytest tests/test_kb_audit.py -v
```

预期：FAIL，`No module named 'kb_audit'`

- [ ] **步骤 3：实现审计脚本**

创建 `scripts/kb_audit.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_audit.py — 知识库结构与写入审计。

用法：
    python3 scripts/kb_audit.py --kb <路径>
    python3 scripts/kb_audit.py --kb <路径> --since 2026-09-01
"""
import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def _exists(root, *parts):
    return os.path.isdir(os.path.join(root, *parts))


def _count_files(root, *parts):
    d = os.path.join(root, *parts)
    if not os.path.isdir(d):
        return 0
    return len([n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n))])


def _recent_files(root, since_str):
    try:
        since = datetime.strptime(since_str, "%Y-%m-%d")
    except ValueError:
        raise SystemExit("[错误] --since 格式应为 YYYY-MM-DD")
    result = []
    for base in (common.DIR_RAW, common.DIR_AUTO, common.DIR_INTERVIEW, common.DIR_OUTPUT):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            for name in filenames:
                path = os.path.join(dirpath, name)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime >= since:
                    result.append((path, mtime.isoformat()))
    return result


def audit(root, since=None):
    report = {
        "path": root,
        "structure_ok": True,
        "issues": [],
        "counts": {},
        "recent_files": [],
    }

    required = [common.DIR_RAW, common.DIR_AUTO, common.DIR_INTERVIEW, common.DIR_OUTPUT]
    for d in required:
        if not _exists(root, d):
            report["structure_ok"] = False
            report["issues"].append("缺少目录：%s" % d)

    if report["structure_ok"]:
        raw_count = 0
        for key in common.RAW_FILES:
            p = os.path.join(root, common.DIR_RAW, common.RAW_FILES[key])
            if os.path.exists(p) and os.path.getsize(p) > 0:
                raw_count += 1
        report["counts"]["raw_files"] = raw_count
        report["counts"]["behavioral_evidence"] = _count_files(root, common.DIR_RAW, "behavioral_evidence")
        report["counts"]["staged"] = _count_files(root, common.DIR_RAW, common.DIR_STAGED) // 2  # md + json
        report["counts"]["claims"] = _count_files(root, common.DIR_RAW, "claims")

        staged_dir = os.path.join(root, common.DIR_RAW, common.DIR_STAGED)
        if os.path.isdir(staged_dir):
            stale = []
            threshold = datetime.now() - timedelta(days=7)
            for name in os.listdir(staged_dir):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(staged_dir, name)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime < threshold:
                    stale.append(name)
            if stale:
                report["issues"].append("待确认区有 %d 条超过 7 天未确认：%s" % (len(stale), ", ".join(sorted(stale))))

    if since:
        report["recent_files"] = _recent_files(root, since)

    return report


def main():
    ap = argparse.ArgumentParser(description="知识库审计")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--since", help="只列出该日期以来修改过的文件（YYYY-MM-DD）")
    args = ap.parse_args()
    root = common.kb_root(args.kb)
    report = audit(root, since=args.since)

    print("知识库路径：%s" % report["path"])
    print("结构完整：%s" % ("是" if report["structure_ok"] else "否"))
    for k, v in report["counts"].items():
        print("  %s：%d" % (k, v))
    if report["recent_files"]:
        print("\n最近修改文件：")
        for path, mtime in sorted(report["recent_files"], key=lambda x: x[1], reverse=True):
            print("  %s  (%s)" % (path, mtime))
    if report["issues"]:
        print("\n注意：")
        for issue in report["issues"]:
            print("  - %s" % issue)
        sys.exit(1)
    print("\n审计通过")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 4：运行测试验证通过**

```bash
python3 -m pytest tests/test_kb_audit.py -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add scripts/kb_audit.py tests/test_kb_audit.py
git commit -m "feat(kb): add kb_audit.py for knowledge base integrity checks"
```

---

## 任务 5：更新 SKILL.md 和 tacit-mining-methodology.md

**文件：**
- 修改：`SKILL.md`
- 修改：`references/tacit-mining-methodology.md`

- [ ] **步骤 1：更新 SKILL.md**

把第 89 行的 STAR 行为证据挖掘流程改为：

```markdown
- **STAR 行为证据挖掘**：在 KB 访谈/增量更新对话中，当用户说出具体工作经历、项目经历、技能使用场景或优势时，Agent 应语义触发 → 暂停主线 → 按 `references/tacit-mining-methodology.md` 用 CDM/对比/Laddering/反事实/隐喻轮换追问 5-8 轮 → 整理成可读 STAR → 调用 `kb_interview.py stage-evidence` 写入 `原始事实/待确认/` → **展示给用户确认 `[硬闸门]`** → 用户回复 OK 后调用 `kb_interview.py confirm-evidence` 迁移到 `原始事实/behavioral_evidence/` → 调用 `kb_audit.py` 验证 → 反馈文件路径与统计 → 返回主线
```

并在进度条 Step 2/Step 3 之间新增一步：

```markdown
- [ ] Step 3 整理成可读 STAR 并写入待确认区 `[自动]`
- [ ] Step 4 用户确认写入 `[硬闸门]`
- [ ] Step 5 迁移到 behavioral_evidence/ 并审计 `[自动]`
```

- [ ] **步骤 2：更新 references/tacit-mining-methodology.md**

在"写入命令"（当前第 8 节）之前插入新的小节"确认式写入流程"：

```markdown
## 8. 确认式写入流程

深挖结束后，Agent 必须先把整理稿写入 `原始事实/待确认/`，等用户明确回复 OK 后再迁移。

### 步骤 1：写入待确认区

```bash
python3 scripts/kb_interview.py stage-evidence \
  --kb <知识库路径> \
  --domain work_experience \
  --source "美团-高级产品经理" \
  --description "商户分层运营，月活 80 万→110 万" \
  --background "2024 年 Q2 商户增长停滞" \
  --task "把月活商户从 80 万提升到 100 万" \
  --action "按 GMV+活跃度重新分 5 层" \
  --action "对头部商户配 1v1 客户经理" \
  --action "对腰部商户做自动化权益触达" \
  --result "3 个月内月活商户从 80 万提升到 110 万，流失率下降 18%" \
  --insight "商户分层不能只看 GMV，活跃度才是预警指标" \
  --boundary "头部商户必须人工介入，自动化只适合腰部及以下" \
  --verbatim "当时发现只看 GMV 会漏掉一批高活跃但小体量的商户。"
```

Agent 必须读取生成的 `原始事实/待确认/st_*.md`，把内容展示给用户：

> **商户分层运营，月活 80 万→110 万**
> - 背景：2024 年 Q2 商户增长停滞……
> - 任务：……
> - 行动：……
> - 结果：……
> - 关键判断：……
> - 边界条件：……
>
duplicate?
> 以上是我整理出来的经历要点。确认写入知识库吗？回复 **OK** 即保存，或告诉我哪里需要修改。

### 步骤 2：用户确认后迁移

用户回复 OK 后：

```bash
python3 scripts/kb_interview.py confirm-evidence --kb <知识库路径> --staged-id st_work_experience_001
```

输出示例：

```
[完成] 已写入知识库：原始事实/behavioral_evidence/be_work_experience_001.md
知识库版本：v42
```

### 步骤 3：审计

```bash
python3 scripts/kb_audit.py --kb <知识库路径>
```

### 用户拒绝或修改

- 用户拒绝：`python3 scripts/kb_interview.py reject-evidence --kb <路径> --staged-id st_work_experience_001`
- 用户要求修改：Agent 修改后重新 `stage-evidence`，覆盖原预览文件（用同一 `staged_id` 或新生成一个），再次展示确认。
```

然后原来的"写入命令"改为第 9 节，后续节号顺延。

- [ ] **步骤 3：Commit**

```bash
git add SKILL.md references/tacit-mining-methodology.md
git commit -m "docs(kb): update STAR mining flow with staging and confirmation gate"
```

---

## 任务 6：回归测试与版本升级

- [ ] **步骤 1：运行完整测试套件**

```bash
python3 -m pytest -q
```

预期：全部通过（当前 56 + 新增测试）

- [ ] **步骤 2：版本升级**

```bash
python3 scripts/version_bump.py --type minor --note "STAR 深挖增加待确认区、确认写入硬闸门与知识库审计命令"
```

- [ ] **步骤 3：最终 Commit**

```bash
git add -A
git commit -m "chore(version): bump to v1.x.x for KB hard-gate persistence"
```

---

## 自检

**规格覆盖度：**
- 用户要求"聊完后把整理好的文字发出来给用户确认" → 任务 3/5 的 stage-evidence + 展示话术
- 用户要求"用户说 OK 后直接写入知识库并给反馈" → 任务 3 的 confirm-evidence + 成功消息
- 用户要求"便于用户检查实际文字有没有落进去" → 任务 2 的 `原始事实/待确认/` 预览文件 + 任务 4 的 `kb_audit.py`
- 用户要求"怎么保证交互内容是真的落入仓库" → 任务 5 的硬闸门流程 + 任务 4 的审计命令

**占位符扫描：** 所有步骤包含实际代码、命令、输出示例，无"待定"或"后续实现"。

**类型一致性：** `staged_id` 在 `staged_evidence.py`、`kb_interview.py`、测试和文档中命名一致；命令参数 `--staged-id` 与变量 `staged_id` 对应。

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-09-02-kb-conversation-persist-hard-gate.md`。

**两种执行方式：**

1. **子代理驱动（推荐）** — 每个任务调度一个新子代理，任务间审查
2. **内联执行** — 在当前会话中使用 executing-plans 批量执行，并设检查点

选哪种方式？
