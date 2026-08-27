import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import common
import init


def test_init_creates_config_and_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "config.yaml")
        backup_dir = os.path.join(tmp, "tools")
        backup_path = common.tools_config_path(backup_dir)
        result = init.run_init(
            material_root=tmp,
            cfg_path=cfg_path,
            tools_backup_dir=backup_dir,
        )
        assert result is not None
        assert os.path.exists(cfg_path)
        assert os.path.exists(backup_path)
        with open(cfg_path) as f:
            content = f.read()
        assert f"material_root: {tmp}" in content
        with open(backup_path) as f:
            backup_content = f.read()
        assert f"material_root: {tmp}" in backup_content
        assert os.path.isdir(os.path.join(tmp, "成品"))
        assert os.path.isdir(tmp)


def test_init_warns_about_legacy_structure(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        legacy = os.path.join(tmp, ".gin-writing-materials")
        os.makedirs(legacy)
        cfg_path = os.path.join(tmp, "config.yaml")
        result = init.run_init(material_root=tmp, cfg_path=cfg_path)
        assert result is not None
        captured = capsys.readouterr()
        assert "旧版数据目录" in captured.out


def test_init_skips_backup_when_tools_dir_not_provided():
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "config.yaml")
        result = init.run_init(material_root=tmp, cfg_path=cfg_path)
        assert result is not None
        assert os.path.exists(cfg_path)
        assert common.tools_config_path() is None


def test_init_returns_none_when_material_root_not_writable():
    # 用一个不存在的深层路径的父目录也不存在的情况来模拟失败
    with tempfile.TemporaryDirectory() as tmp:
        bad_root = os.path.join(tmp, "nonexistent_parent", "material_root")
        # 把父目录设为只读（在 Unix 上）
        os.chmod(tmp, 0o555)
        try:
            result = init.run_init(material_root=bad_root)
            assert result is None
        finally:
            os.chmod(tmp, 0o755)


def test_check_input_materials():
    with tempfile.TemporaryDirectory() as tmp:
        existing = os.path.join(tmp, "existing.md")
        with open(existing, "w") as f:
            f.write("test")
        missing = os.path.join(tmp, "missing.md")
        assert init.check_input_materials([existing]) is True
        assert init.check_input_materials([missing]) is False
        assert init.check_input_materials([existing, missing]) is False


def test_check_env_passes_with_valid_root():
    with tempfile.TemporaryDirectory() as tmp:
        ok, warnings = init.check_env(material_root=tmp)
        assert ok is True
        assert "downstream_skill" not in warnings


def test_check_env_fails_with_bad_root():
    with tempfile.TemporaryDirectory() as tmp:
        bad_root = os.path.join(tmp, "bad")
        os.chmod(tmp, 0o555)
        try:
            ok, _ = init.check_env(material_root=bad_root)
            assert ok is False
        finally:
            os.chmod(tmp, 0o755)


def test_python_version_check():
    assert init.check_python_version(min_major=3, min_minor=0) is True


def test_pypinyin_check():
    # 当前环境应该已安装 pypinyin
    assert init.check_pypinyin() is True
