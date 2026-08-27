import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("style_selector", _MODULE_DIR / "style_selector.py")
style_selector = importlib.util.module_from_spec(_spec)
sys.modules["style_selector"] = style_selector
_spec.loader.exec_module(style_selector)

scan_materials = style_selector.scan_materials
summarize_materials = style_selector.summarize_materials
recommend_styles = style_selector.recommend_styles
validate_template_id = style_selector.validate_template_id


def test_scan_materials_finds_text_files(tmp_path):
    (tmp_path / "a.md").write_text("hello", encoding="utf-8")
    (tmp_path / "b.txt").write_text("world", encoding="utf-8")
    (tmp_path / "c.jpg").write_text("ignore", encoding="utf-8")
    files = scan_materials(tmp_path)
    assert len(files) == 2
    assert all(f.suffix in {".md", ".txt"} for f in files)


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


def test_scan_materials_recursive_one_level(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("nested", encoding="utf-8")
    files = scan_materials(tmp_path, recursive=True)
    assert len(files) == 1
    assert files[0].name == "nested.md"


def test_summarize_materials_reads_text(tmp_path):
    (tmp_path / "a.md").write_text("这是素材内容", encoding="utf-8")
    result = summarize_materials([tmp_path / "a.md"])
    assert "这是素材内容" in result["summary_text"]


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


def test_summarize_materials_returns_full_content_dict(tmp_path):
    long_text = "这是正文。" * 1000
    expected_len = len(long_text)
    md_file = tmp_path / "long.md"
    md_file.write_text(long_text, encoding="utf-8")

    result = summarize_materials([md_file], output_dir=tmp_path / "out")

    assert result["fully_loaded"] is True
    assert result["total_files"] == 1
    assert result["total_chars"] == expected_len
    assert result["files"][0]["name"] == "long.md"
    assert result["files"][0]["chars"] == expected_len
    assert "summary_text" in result
    assert "这是正文。" in result["summary_text"]

    # 验证 materials_full.md 已生成
    full_path = tmp_path / "out" / "materials_full.md"
    assert full_path.exists()
    assert "这是正文。" in full_path.read_text(encoding="utf-8")


def test_recommend_styles_returns_ranked_list():
    templates = [
        {
            "id": "ai-product-story",
            "name": "AI产品故事型",
            "description": "适合写AI产品体验",
            "match_signals": ["素材中有 AI 产品 功能 试用 过程"],
        },
        {
            "id": "business-observation",
            "name": "商业观察型",
            "description": "适合写商业观察",
            "match_signals": ["素材有行业现象、商业思考"],
        },
    ]
    topic = "我试了一下 Claude 的新功能"
    materials_summary = "用户描述了试用 Claude 新功能的过程，包含输入输出对比。"
    result = recommend_styles(topic, materials_summary, templates)
    assert len(result) > 0
    assert result[0]["id"] == "ai-product-story"


def test_recommend_styles_respects_min_score():
    templates = [
        {
            "id": "unrelated",
            "name": "无关风格",
            "description": "完全不相关",
            "match_signals": ["素材中有量子物理实验数据"],
        }
    ]
    result = recommend_styles("我养了只猫", "猫咪日常", templates, min_score=1)
    assert result == []


def test_match_score_with_chinese_topic_and_signals():
    templates = [
        {
            "id": "shangye-guancha",
            "name": "社会切片叙事型",
            "description": "适合写社会现象、个体命运",
            "match_signals": ["上班族、打工、自己做事、个体、社会观察"],
        },
        {
            "id": "ai-product-story",
            "name": "AI产品故事型",
            "description": "适合写AI产品体验",
            "match_signals": ["AI、产品、试用、新功能"],
        },
    ]
    topic = "上班与自己做事的区别"
    materials_summary = ""
    result = recommend_styles(topic, materials_summary, templates)
    assert len(result) > 0
    assert result[0]["id"] == "shangye-guancha"
    assert result[0]["match_score"] > 0
    assert all(item["match_score"] > 0 for item in result)


def test_recommend_styles_with_real_templates_distinguishes_topic(tmp_path):
    from pathlib import Path
    import yaml

    # 使用临时模板目录，确保有可预期的 match_signals
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "shangye-guancha.yaml").write_text(
        "meta:\n"
        "  name: 商业观察型\n"
        "  id: shangye-guancha\n"
        "  description: 适合写商业观察\n"
        "  match_signals: [\"商业 观察 行业\"]\n"
        "风格核心: test\n"
        "结构参考: []\n",
        encoding="utf-8",
    )
    (template_dir / "renwu-xushi.yaml").write_text(
        "meta:\n"
        "  name: 人物叙事型\n"
        "  id: renwu-xushi\n"
        "  description: 适合写人物故事\n"
        "  match_signals: [\"人物 故事 经历\"]\n"
        "风格核心: test\n"
        "结构参考: []\n",
        encoding="utf-8",
    )

    templates = []
    for p in template_dir.glob("*.yaml"):
        template = yaml.safe_load(p.read_text(encoding="utf-8"))
        meta = template.get("meta", {})
        templates.append({
            "id": meta.get("id", p.stem),
            "name": meta.get("name", p.stem),
            "description": meta.get("description", ""),
            "match_signals": meta.get("match_signals", []),
        })

    topic = "我观察到一个商业现象"
    result = recommend_styles(topic, "", templates)
    assert len(result) > 0
    assert result[0]["match_score"] > 0
    assert result[0]["id"] == "shangye-guancha"


def test_validate_template_id_in_whitelist():
    templates = [{"id": "shangye-guancha"}, {"id": "renwu-xushi"}]
    assert validate_template_id("shangye-guancha", templates) is True


def test_validate_template_id_not_in_whitelist():
    templates = [{"id": "shangye-guancha"}, {"id": "renwu-xushi"}]
    assert validate_template_id("fake-template", templates) is False


def test_validate_template_id_empty():
    templates = [{"id": "shangye-guancha"}]
    assert validate_template_id("", templates) is False
