import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "requirements_check", _MODULE_DIR / "requirements_check.py"
)
requirements_check = importlib.util.module_from_spec(_spec)
sys.modules["requirements_check"] = requirements_check
_spec.loader.exec_module(requirements_check)

assess_materials = requirements_check.assess_materials
validate_requirements = requirements_check.validate_requirements


def _complete_requirements():
    return {
        "topic": "AI 工具对自由职业者的影响",
        "target_reader": "自由职业者",
        "core_points": ["AI 降低了接单门槛", "但放大了报价内卷"],
        "word_count": 2500,
        "materials": ["采访记录.md"],
        "materials_sufficient": True,
        "materials_gap": [],
        "speaker_position": {
            "who": "观察者",
            "credential": "采访了 10 位自由职业者",
            "trigger": "近期身边朋友纷纷转用 AI 接单",
        },
    }


def test_assess_materials_empty():
    result = assess_materials(0)
    assert result["materials_sufficient"] is False
    assert len(result["materials_gap"]) > 0


def test_assess_materials_not_provided():
    result = assess_materials(5000, user_provided_materials=False)
    assert result["materials_sufficient"] is False


def test_assess_materials_sufficient():
    result = assess_materials(12580)
    assert result["materials_sufficient"] is True
    assert result["materials_gap"] == []


def test_validate_requirements_complete():
    assert validate_requirements(_complete_requirements()) == []


def test_validate_requirements_missing_fields():
    errors = validate_requirements({"topic": "x"})
    for field in ("target_reader", "core_points", "word_count", "materials", "speaker_position"):
        assert any(field in err for err in errors)


def test_validate_requirements_speaker_position_incomplete():
    req = _complete_requirements()
    req["speaker_position"] = {"who": "亲历者"}
    errors = validate_requirements(req)
    assert any("credential" in err for err in errors)
    assert any("trigger" in err for err in errors)


def test_validate_requirements_empty_input():
    assert validate_requirements({}) != []
