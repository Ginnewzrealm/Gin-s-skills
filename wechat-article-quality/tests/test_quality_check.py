import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "quality_check", _MODULE_DIR / "quality_check.py"
)
quality_check = importlib.util.module_from_spec(_spec)
sys.modules["quality_check"] = quality_check
_spec.loader.exec_module(quality_check)

check_title_length = quality_check.check_title_length
check_disabled_symbols = quality_check.check_disabled_symbols
score_title = quality_check.score_title
check_l1 = quality_check.check_l1
check_l2 = quality_check.check_l2
check_l3 = quality_check.check_l3
check_l4 = quality_check.check_l4
score_article = quality_check.score_article


def test_check_title_length_pass():
    assert check_title_length("这是一个合适的标题") is True


def test_check_title_length_too_short():
    assert check_title_length("短") is False


def test_check_title_length_too_long():
    assert check_title_length("这是一个非常非常非常非常非常非常非常非常非常非常非常长长长的标题") is False


def test_check_disabled_symbols_detects_colon():
    assert check_disabled_symbols("注意：这里有个冒号") == ["："]


def test_score_title_full_marks():
    title = "转化率从 3% 涨到 12%，结果我只改了一个按钮"
    result = score_title(title, supports=["转化率", "按钮"], trigger="看结果")
    assert result["score"] == 12
    assert result["issues"] == []


def test_score_title_missing_number():
    title = "我只改了一个按钮"
    result = score_title(title, supports=["按钮"], trigger="看结果")
    assert result["score"] < 12
    assert "缺少具体数字或对比" in result["issues"]


def test_l1_passes_with_clean_text():
    title = "转化率从 3% 涨到 12%，结果我只改了一个按钮"
    text = "事情是这样的。上周我帮朋友改按钮，三天后转化率涨了。"
    fm = {"title": title, "article_type": "methodology", "emotion_tone": "看结果", "word_count": 30}
    result = check_l1(title, text, fm)
    assert result["passed"] is True
    assert result["score"] == 100


def test_l1_fails_disabled_word_and_chapter_number():
    title = "结论：转化率涨了"
    text = "首先，我们来看数据。第一章，按钮文案。"
    fm = {"title": title, "article_type": "methodology", "emotion_tone": "看结果", "word_count": 50}
    result = check_l1(title, text, fm)
    assert result["passed"] is False
    assert any("禁用符号" in i for i in result["issues"])
    assert any("章节编号" in i for i in result["issues"])
    assert any("禁用词" in i for i in result["issues"])


def test_l2_casual_phrases_and_sensory():
    text = (
        "说真的，我当时就愣住了。"
        "手里端着咖啡，耳边是他发来的语音。"
        "那一瞬间，温度好像都降了两度。"
        "你想想看，就这么一句话？"
    )
    result = check_l2(text)
    assert result["details"]["casual_phrases"] >= 2
    assert result["details"]["sensory_words"] >= 2


def test_l3_hook_and_cognitive_gap():
    text = (
        "结果我万万没想到，改了按钮文案，转化率竟然从 3% 涨到 12%。"
        "以前我也以为设计最重要，后来发现大家都错了。"
        "你可以现在就打开落地页，把按钮文案改成『先算能省多少』。"
        "这背后不只是文案，而是人对『与我有关』的本能反应。"
    )
    result = check_l3(text, template="methodology", target_word_count=200)
    assert result["passed"] is True
    assert result["details"]["hook_signals"] >= 1
    assert result["details"]["cognitive_gap_signals"] >= 2


def test_score_article_overall():
    title = "转化率从 3% 涨到 12%，结果我只改了一个按钮"
    text = (
        "事情是这样的。上周我帮朋友改落地页，当时也不确定有没有用。"
        "结果三天后，转化率从 3% 涨到 12%，我整个人都懵了。"
        "后来我翻了十几个案例，发现大多数人对按钮的理解都错了。"
        "不是设计不够好看，而是读者没看到『与我有关』。"
        "你可以现在就试试，把按钮文案改成『先算一算我能省多少』。"
        "你怎么看？"
    )
    report = score_article(
        title=title,
        text=text,
        frontmatter={
            "title": title,
            "article_type": "methodology",
            "emotion_tone": "看结果",
            "word_count": 200,
        },
        template="methodology",
        supports=["转化率", "按钮"],
        trigger="看结果",
    )
    assert "l1" in report
    assert "l4" in report
    assert isinstance(report["objective_score"], int)
