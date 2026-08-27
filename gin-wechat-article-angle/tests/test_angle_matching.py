import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "angle_matcher", _MODULE_DIR / "angle_matcher.py"
)
angle_matcher = importlib.util.module_from_spec(_spec)
sys.modules["angle_matcher"] = angle_matcher
_spec.loader.exec_module(angle_matcher)

match_angles = angle_matcher.match_angles


def test_match_angles_pain_and_number():
    signals = {"痛点", "数字"}
    result = match_angles(signals)
    assert result["primary"] == "A1"
    assert result["secondary"] == "A2"
    assert result["emotion_primary"] == "找共鸣"


def test_match_angles_only_story():
    signals = {"故事"}
    result = match_angles(signals)
    assert result["primary"] == "A4"
    assert result["count"] == 1
