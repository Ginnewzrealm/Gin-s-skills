import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "state_persistence", _MODULE_DIR / "state_persistence.py"
)
state_persistence = importlib.util.module_from_spec(_spec)
sys.modules["state_persistence"] = state_persistence
_spec.loader.exec_module(state_persistence)


def test_save_and_load_progress(tmp_path):
    state_persistence.save_progress(
        tmp_path,
        stage="angle_diagnosed",
        decisions={"template": "social-slice"},
        risks=["素材不足"],
    )
    progress = state_persistence.load_progress(tmp_path)
    assert progress["stage"] == "angle_diagnosed"
    assert progress["decisions"]["template"] == "social-slice"
    assert "素材不足" in progress["risks"]


def test_save_and_load_blocked(tmp_path):
    state_persistence.save_blocked(tmp_path, ["确认素材", "补充真实经历"])
    items = state_persistence.load_blocked(tmp_path)
    assert "确认素材" in items
    assert "补充真实经历" in items


def test_load_missing_returns_empty(tmp_path):
    assert state_persistence.load_progress(tmp_path) is None
    assert state_persistence.load_blocked(tmp_path) == []
