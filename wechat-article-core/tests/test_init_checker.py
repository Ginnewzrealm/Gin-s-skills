import sys
import importlib.util
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("init_checker", _MODULE_DIR / "init_checker.py")
init_checker = importlib.util.module_from_spec(_spec)
sys.modules["init_checker"] = init_checker
_spec.loader.exec_module(init_checker)

needs_initial_config = init_checker.needs_initial_config
validate_paths = init_checker.validate_paths
resolve_paths_from_config = init_checker.resolve_paths_from_config
parse_user_paths_reply = init_checker.parse_user_paths_reply


def test_needs_initial_config_when_value_empty():
    config = {
        "paths": {
            "input_dir": {"value": ""},
            "output_dir": {"value": "/valid/path"},
            "user_templates_dir": {"value": "/valid/path"},
        }
    }
    assert needs_initial_config(config) is True


def test_needs_initial_config_when_value_missing():
    config = {
        "paths": {
            "input_dir": {},
            "output_dir": {"value": "/valid/path"},
            "user_templates_dir": {"value": "/valid/path"},
        }
    }
    assert needs_initial_config(config) is True


def test_needs_initial_config_when_all_configured():
    config = {
        "paths": {
            "input_dir": {"value": "/a"},
            "output_dir": {"value": "/b"},
            "user_templates_dir": {"value": "/c"},
        }
    }
    assert needs_initial_config(config) is False


def test_resolve_paths_from_config_uses_value():
    config = {
        "paths": {
            "input_dir": {"value": "/custom/input", "env": "X", "default": "~/default"},
            "output_dir": {"value": "/custom/output", "env": "Y", "default": "~/default"},
            "user_templates_dir": {"value": "/custom/templates", "env": "Z", "default": "~/default"},
        }
    }
    paths = resolve_paths_from_config(config)
    assert str(paths["input_dir"]) == "/custom/input"
    assert str(paths["output_dir"]) == "/custom/output"
    assert str(paths["user_templates_dir"]) == "/custom/templates"


def test_validate_paths_creates_output_and_templates(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"  # not exist
    templates_dir = tmp_path / "templates"  # not exist

    paths = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "user_templates_dir": templates_dir,
    }
    resolved, messages = validate_paths(paths)
    assert output_dir.exists()
    assert templates_dir.exists()
    assert resolved["output_dir"] == output_dir
    assert resolved["user_templates_dir"] == templates_dir
    assert resolved["input_dir"] == input_dir


def test_validate_paths_reports_missing_input_dir(tmp_path):
    output_dir = tmp_path / "output"
    templates_dir = tmp_path / "templates"

    paths = {
        "input_dir": tmp_path / "does_not_exist",
        "output_dir": output_dir,
        "user_templates_dir": templates_dir,
    }
    resolved, messages = validate_paths(paths)
    assert resolved["input_dir"] is None
    assert any("输入目录不存在" in m for m in messages)


def test_parse_user_paths_reply_confirm_uses_defaults():
    config = {
        "paths": {
            "input_dir": {"default": "~/a"},
            "output_dir": {"default": "~/b"},
            "user_templates_dir": {"default": "~/c"},
        }
    }
    result = parse_user_paths_reply("确认", config)
    assert result["input_dir"] == "~/a"
    assert result["output_dir"] == "~/b"
    assert result["user_templates_dir"] == "~/c"


def test_parse_user_paths_reply_custom_paths():
    config = {
        "paths": {
            "input_dir": {"default": "~/a"},
            "output_dir": {"default": "~/b"},
            "user_templates_dir": {"default": "~/c"},
        }
    }
    result = parse_user_paths_reply("输入=/x, 输出=/y, 模板=/z", config)
    assert result["input_dir"] == "/x"
    assert result["output_dir"] == "/y"
    assert result["user_templates_dir"] == "/z"
