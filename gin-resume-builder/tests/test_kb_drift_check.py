#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kb_drift_check", Path(__file__).parent.parent / "scripts" / "kb_drift_check.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["kb_drift_check"] = mod
spec.loader.exec_module(mod)


def _make_kb(tmp_path):
    for d in ("原始事实", "自动生成", "面试素材", "生成物"):
        (tmp_path / d).mkdir()
    return str(tmp_path)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_drift_reports_term_only_in_derived(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md",
           "## 某项目 | 顾问 | 2025-至今\n- 负责开单流程优化\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    # 同一词出现在 2 个派生文件、源里没有 → 应进待回流清单
    _write(tmp_path / "生成物" / "简历" / "a.md", "覆盖返修自动处理流程，降本增效。")
    _write(tmp_path / "生成物" / "简历" / "b.md", "实现返修自动处理，人工仅审核。")

    report = mod.check(root)
    terms = [d["term"] for d in report["drift"]]
    assert "返修自动处理" in terms
    item = next(d for d in report["drift"] if d["term"] == "返修自动处理")
    assert len(item["files"]) == 2
    assert item["count"] >= 2


def test_drift_ignores_terms_present_in_source(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md",
           "## 某项目 | 顾问 | 2025-至今\n- 落地返修自动处理流程\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    _write(tmp_path / "生成物" / "简历" / "a.md", "覆盖返修自动处理。")
    _write(tmp_path / "生成物" / "简历" / "b.md", "实现返修自动处理。")

    report = mod.check(root)
    assert all(d["term"] != "返修自动处理" for d in report["drift"])


def test_drift_source_includes_facts_yaml_and_evidence(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "behavioral_evidence" / "be_work_experience_001.md",
           "签下返修自动处理的大单")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": [{"bullets": ["含有库存预警机制"]}]}')
    _write(tmp_path / "生成物" / "简历" / "a.md", "返修自动处理与库存预警机制均已落地。")
    _write(tmp_path / "生成物" / "简历" / "b.md", "返修自动处理与库存预警机制均已落地。")

    report = mod.check(root)
    terms = [d["term"] for d in report["drift"]]
    assert "返修自动处理" not in terms
    assert "库存预警机制" not in terms


def test_drift_filters_stopwords(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md", "## 项目 | 角色 | 2025-至今\n- 负责\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    noise = "我们通过项目进行了相关的优化，并且负责管理以及协调工作。"
    _write(tmp_path / "面试素材" / "star_stories.md", noise + noise)
    _write(tmp_path / "生成物" / "resumes" / "c.md", noise + noise)

    report = mod.check(root)
    for sw in ("我们", "通过", "进行", "相关", "以及", "负责", "工作"):
        assert all(d["term"] != sw for d in report["drift"])


def test_drift_strips_html_tags(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md", "## 项目 | 角色 | 2025-至今\n- 优化\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    html = ('<html><head><style>div.color{font-size:14px}</style></head>'
            '<body><div class="color">返修自动处理已上线</div></body></html>')
    _write(tmp_path / "生成物" / "简历" / "a.html", html)
    _write(tmp_path / "生成物" / "简历" / "b.html", html)

    report = mod.check(root)
    terms = [d["term"] for d in report["drift"]]
    assert "返修自动处理" in terms
    for css in ("color", "font", "size", "style", "class", "html"):
        assert css not in terms


def test_drift_respects_min_files(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md", "## 项目 | 角色 | 2025-至今\n- 优化\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    # 只在 1 个派生文件出现
    _write(tmp_path / "生成物" / "简历" / "only.md", "独有措辞返修自动处理。")

    report = mod.check(root, min_files=2)
    assert all(d["term"] != "返修自动处理" for d in report["drift"])
    report1 = mod.check(root, min_files=1)
    # 子串合并可能把词并入更长的干净段，断言包含即可
    assert any("返修自动处理" in d["term"] for d in report1["drift"])


def test_drift_skips_missing_dirs_and_empty_kb(tmp_path):
    root = str(tmp_path)  # 没有任何目录
    report = mod.check(root)
    assert report["drift"] == []
    assert report["structure_ok"] is False


def test_drift_top_limit_and_json_out(tmp_path):
    root = _make_kb(tmp_path)
    _write(tmp_path / "原始事实" / "projects.md", "## 项目 | 角色 | 2025-至今\n- 优化\n")
    _write(tmp_path / "自动生成" / "facts.yaml", '{"facts": []}')
    for i in range(5):
        t = "独有细节词%02d落地应用" % i
        _write(tmp_path / "生成物" / "简历" / "a.md", t + "。")
        _write(tmp_path / "生成物" / "简历" / "b.md", t + "。")

    out = tmp_path / "drift.json"
    report = mod.check(root, top=3, json_out=str(out))
    assert len(report["drift"]) <= 3
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["structure_ok"] is True
    assert len(data["drift"]) == len(report["drift"])
