#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gin-tutorial-source-scan 质量分级、层级分类、收敛判定、去重的 TDD 测试。

基线证据（9/2 减脂实测）：搜索结果前 20 条约一半是微商软文/内容农场，
无技能的 Agent 容易照单全收——grade_source 的规则来自那批真实被拒样本。
"""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "source_scan", Path(__file__).parent.parent / "scripts" / "source_scan.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["source_scan"] = mod
spec.loader.exec_module(mod)


# ---------- grade_source：质量分级 ----------

def test_reject_product_spam_brand_principle():
    """产品品牌+原理分析话术 = 拒绝（9/2 实测样本：MOOSOR·9S小魔原理分析）。"""
    v, reason = mod.grade_source("MOOSOR·9S小魔原理分析", "https://example.com/moosor", "")
    assert v == "reject"
    assert reason


def test_reject_weight_loss_product_site():
    """瘦身产品名 + 营销话术 = 拒绝（9/2 实测样本：伊简梅健康瘦身原理）。"""
    v, _ = mod.grade_source("伊简梅健康瘦身原理与效果", "https://www.yijianmei.com/a/1", "")
    assert v == "reject"


def test_reject_ecommerce_link():
    v, _ = mod.grade_source("某教程", "https://item.taobao.com/item.htm?id=1", "")
    assert v == "reject"


def test_reject_mlm_recruitment():
    v, _ = mod.grade_source("减脂代理加盟，月入过万", "https://example.com/join", "")
    assert v == "reject"


def test_high_official_gov():
    v, _ = mod.grade_source("国家卫健委《体重管理指导原则（2024版）》",
                            "https://www.nhc.gov.cn/xxx.htm", "")
    assert v == "high"


def test_high_international_org():
    v, _ = mod.grade_source("WHO Physical Activity Fact Sheet",
                            "https://www.who.int/news-room/fact-sheets/detail/physical-activity", "")
    assert v == "high"


def test_high_docs_site():
    v, _ = mod.grade_source("健身减肥完全指南（17章）",
                            "https://docs.fitness.ninthfeast.com/docs/handbook", "")
    assert v == "high"


def test_medium_personal_blog():
    v, _ = mod.grade_source("我的减脂经验分享", "https://hisuper.com.au/blog/post-1", "")
    assert v == "medium"


def test_unknown_ugc_needs_review():
    """知乎等高价值 UGC 站点不因域名误杀，标 unknown 待人工/Agent 复核。"""
    v, _ = mod.grade_source("知乎高赞回答：如何科学减脂",
                            "https://www.zhihu.com/question/123/answer/456", "")
    assert v in ("unknown", "medium")


def test_official_keyword_cannot_override_spam():
    """标题蹭官方词但链向电商仍拒绝——信号优先级：拒绝 > 高。"""
    v, _ = mod.grade_source("国家认证的减肥茶正品旗舰店",
                            "https://detail.tmall.com/item.htm?id=9", "")
    assert v == "reject"


# ---------- classify_layer：六层资料地图 ----------

def test_layer_classification():
    cases = {
        "https://www.nhc.gov.cn/a": "L1",
        "https://www.who.int/b": "L1",
        "https://github.com/awesome/awesome-claude-code": "L2",
        "https://github.com/docs/cli": "L2",
        "https://www.zhihu.com/question/1": "L3",
        "https://juejin.cn/post/1": "L3",
        "https://sspai.com/post/1": "L3",
        "https://medium.com/@user/post": "L4",
        "https://dev.to/user/post": "L4",
        "https://www.reddit.com/r/fitness/comments/1/x": "L5",
        "https://news.ycombinator.com/item?id=1": "L5",
        "https://www.v2ex.com/t/1": "L5",
        "https://arxiv.org/abs/1234.5678": "L6",
        "https://www.sciencedirect.com/science/article/pii/X": "L6",
    }
    for url, layer in cases.items():
        assert mod.classify_layer(url) == layer, url


def test_layer_unknown_falls_back():
    assert mod.classify_layer("https://random-blog.example.com/post") == "L3"


# ---------- saturation：收敛信号 ----------

def test_saturation_when_three_of_top_ten_seen():
    assert mod.is_saturated(seen=3, round_total=10) is True
    assert mod.is_saturated(seen=2, round_total=10) is False
    assert mod.is_saturated(seen=5, round_total=8) is True


# ---------- sources.json 管理 ----------

def _tmp_json(tmp_path, initial=None):
    p = tmp_path / "sources.json"
    p.write_text(json.dumps(initial or {"topic": "减脂", "sources": [], "rejected": []},
                            ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_add_source_dedupes_by_normalized_url(tmp_path):
    path = _tmp_json(tmp_path)
    mod.add_source(path, {"title": "A", "url": "https://x.com/a/?utm_source=tw&utm_medium=social",
                          "layer": "L3", "lang": "zh", "value": "medium", "note": ""})
    mod.add_source(path, {"title": "A副本", "url": "https://x.com/a", "layer": "L3",
                          "lang": "zh", "value": "medium", "note": ""})
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert len(data["sources"]) == 1


def test_add_source_records_rejected(tmp_path):
    path = _tmp_json(tmp_path)
    mod.add_rejected(path, {"title": "微商软文", "url": "https://spam.com/x",
                            "reason": "产品营销文"})
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert len(data["rejected"]) == 1
    assert data["sources"] == []


def test_coverage_check_counts(tmp_path):
    path = _tmp_json(tmp_path, {
        "topic": "减脂",
        "sources": [
            {"title": "a", "url": "https://a.com", "note": "减脂原理"},
            {"title": "b", "url": "https://b.com", "note": "饮食方案"},
            {"title": "c", "url": "https://c.com", "note": "减脂原理 饮食方案"},
        ],
        "rejected": [],
    })
    report = mod.coverage_report(path, ["减脂原理", "饮食方案", "训练计划"])
    assert report["已覆盖来源数"]["减脂原理"] == 2
    assert report["已覆盖来源数"]["饮食方案"] == 2
    assert report["已覆盖来源数"]["训练计划"] == 0
    assert "训练计划" in report["gap"]


# ---------- 配置：训记模式的 key 管理 ----------

def test_config_roundtrip_and_fallback(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(mod, "CONFIG_PATH", cfg)
    assert mod.load_config() == {}
    mod.save_config({"tavily_api_key": "tvly-test-123"})
    assert mod.load_config()["tavily_api_key"] == "tvly-test-123"
    assert mod.search_channel() == "tavily"
    # 清空 key → 回退到 agent-websearch
    mod.save_config({})
    assert mod.search_channel() == "agent-websearch"
