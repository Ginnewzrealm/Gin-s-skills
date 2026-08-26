import sys
import importlib.util
import time
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "update_checker", _MODULE_DIR / "update_checker.py"
)
update_checker = importlib.util.module_from_spec(_spec)
sys.modules["update_checker"] = update_checker
_spec.loader.exec_module(update_checker)


def test_check_for_updates_skips_when_recent(tmp_path):
    check_file = tmp_path / ".last-update-check"
    check_file.touch()
    # 确保时间戳是新的
    time.sleep(0.01)
    result = update_checker.check_for_updates(tmp_path)
    assert result["status"] == "skipped"


def test_check_for_updates_returns_dict(tmp_path):
    result = update_checker.check_for_updates(tmp_path)
    assert isinstance(result, dict)
    assert "status" in result
