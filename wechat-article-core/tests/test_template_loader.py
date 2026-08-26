import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "template_loader", _MODULE_DIR / "template_loader.py"
)
template_loader = importlib.util.module_from_spec(_spec)
sys.modules["template_loader"] = template_loader
_spec.loader.exec_module(template_loader)

load_template = template_loader.load_template
validate_template = template_loader.validate_template
validate_template_completeness = template_loader.validate_template_completeness
validate_sections_coverage = template_loader.validate_sections_coverage
list_templates = template_loader.list_templates
find_template = template_loader.find_template

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_DEFAULT_TEMPLATE_ID = "shangye-guancha"


def test_load_template_returns_dict():
    template = load_template(_TEMPLATE_DIR / f"{_DEFAULT_TEMPLATE_ID}.yaml")
    assert isinstance(template, dict)
    assert template["meta"]["id"] == _DEFAULT_TEMPLATE_ID


def test_validate_template_valid():
    template = load_template(_TEMPLATE_DIR / f"{_DEFAULT_TEMPLATE_ID}.yaml")
    errors = validate_template(template)
    # 只检查是否有阻塞性错误（不以"[建议补充]"开头的错误）
    blocking_errors = [e for e in errors if not e.startswith("[建议补充]")]
    assert blocking_errors == []


def test_validate_template_missing_meta():
    errors = validate_template({})
    assert any("meta" in err and not err.startswith("[建议补充]") for err in errors)


def test_validate_template_missing_style_core():
    errors = validate_template({"meta": {"name": "x", "id": "x", "description": "x"}})
    assert any("风格核心" in err for err in errors)


def test_list_templates_discovers_all():
    templates = list_templates(_TEMPLATE_DIR)
    ids = {t["id"] for t in templates}
    assert "shangye-guancha" in ids
    assert "renwu-xushi" in ids
    assert "chanpin-gushi" in ids
    assert "xianxiang-jiedu" in ids
    assert "diaocha-shiyan" in ids


def test_find_template_default_dir():
    path = find_template(_DEFAULT_TEMPLATE_ID, _TEMPLATE_DIR)
    assert path.exists()
    assert path.name == f"{_DEFAULT_TEMPLATE_ID}.yaml"


def test_find_template_with_user_dir(tmp_path):
    user_dir = tmp_path / "user_templates"
    user_dir.mkdir()
    custom_file = user_dir / "travel-diary.yaml"
    custom_file.write_text(
        "meta:\n  name: 旅行日记型\n  id: travel-diary\n  description: test\n"
        "风格核心: test\n结构参考: {}\n",
        encoding="utf-8",
    )

    path = find_template("travel-diary", _TEMPLATE_DIR, user_dir)
    assert path == custom_file


def test_find_template_not_found():
    try:
        find_template("not-exist-template", _TEMPLATE_DIR)
        assert False, "应该抛出 FileNotFoundError"
    except FileNotFoundError:
        pass


def test_list_all_templates_merges_default_and_user(tmp_path):
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "custom.yaml").write_text(
        "meta:\n  name: 自定义\n  id: custom\n  description: test\n"
        "风格核心: test\n结构参考: []\n",
        encoding="utf-8",
    )

    all_templates = template_loader.list_all_templates(_TEMPLATE_DIR, user_dir)
    ids = {t["id"] for t in all_templates}
    assert "shangye-guancha" in ids
    assert "custom" in ids


def test_list_all_templates_user_overrides_default(tmp_path):
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "shangye-guancha.yaml").write_text(
        "meta:\n  name: 用户社会切片型\n  id: shangye-guancha\n  description: user\n"
        "风格核心: user\n结构参考: []\n",
        encoding="utf-8",
    )

    all_templates = template_loader.list_all_templates(_TEMPLATE_DIR, user_dir)
    inv = [t for t in all_templates if t["id"] == "shangye-guancha"][0]
    assert inv["name"] == "用户社会切片型"


def test_extract_narrative_protocol_from_social_slice():
    template = load_template(_TEMPLATE_DIR / "shangye-guancha.yaml")
    protocol = template_loader.extract_narrative_protocol(template)

    assert protocol["derived_from"] == "shangye-guancha"
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


def test_validate_template_completeness_missing_sections():
    errors = validate_template_completeness({"meta": {"id": "test"}})
    assert any("结构参考" in err for err in errors)


def test_validate_template_completeness_empty_sections():
    errors = validate_template_completeness({"meta": {"id": "test"}, "结构参考": []})
    assert any("结构参考" in err for err in errors)


def test_validate_template_completeness_section_without_name():
    errors = validate_template_completeness({
        "meta": {"id": "test"},
        "结构参考": [{"purpose": "test"}],
    })
    assert any("section 名称" in err for err in errors)


def test_validate_template_completeness_valid():
    template = load_template(_TEMPLATE_DIR / f"{_DEFAULT_TEMPLATE_ID}.yaml")
    errors = validate_template_completeness(template)
    assert errors == []


def test_extract_narrative_protocol_records_fully_loaded():
    template = load_template(_TEMPLATE_DIR / f"{_DEFAULT_TEMPLATE_ID}.yaml")
    protocol = template_loader.extract_narrative_protocol(template)
    assert protocol["fully_loaded"] is True
    assert protocol["completeness_errors"] == []


def test_extract_narrative_protocol_records_not_fully_loaded():
    protocol = template_loader.extract_narrative_protocol({
        "meta": {"id": "test"},
        "结构参考": [],
    })
    assert protocol["fully_loaded"] is False
    assert len(protocol["completeness_errors"]) > 0


def test_validate_sections_coverage_complete():
    narrative_protocol = {
        "fully_loaded": True,
        "sections": [{"name": "开头"}, {"name": "展开"}, {"name": "结尾"}],
    }
    outline_sections = [{"name": "开头"}, {"name": "展开"}, {"name": "结尾"}]
    errors = validate_sections_coverage(outline_sections, narrative_protocol)
    assert errors == []


def test_validate_sections_coverage_missing():
    narrative_protocol = {
        "fully_loaded": True,
        "sections": [{"name": "开头"}, {"name": "展开"}, {"name": "结尾"}],
    }
    outline_sections = [{"name": "开头"}, {"name": "结尾"}]
    errors = validate_sections_coverage(outline_sections, narrative_protocol)
    assert any("展开" in err for err in errors)


def test_validate_sections_coverage_not_fully_loaded():
    narrative_protocol = {
        "fully_loaded": False,
        "completeness_errors": ["模板缺少结构参考"],
        "sections": [],
    }
    errors = validate_sections_coverage([], narrative_protocol)
    assert any("模板缺少结构参考" in err for err in errors)
