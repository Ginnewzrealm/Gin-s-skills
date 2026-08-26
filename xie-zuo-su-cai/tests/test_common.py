import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import common


def test_slugify_simple():
    assert common.slugify("为什么AI写作总有AI味") == "wei-shen-me-ai-xie-zuo-zong-you-ai-wei"


def test_slugify_with_punctuation():
    assert common.slugify("主题：测试！") == "zhu-ti-ce-shi"


def test_today_str_format():
    s = common.today_str()
    assert len(s) == 8 and s.isdigit()


def test_load_config_reads_yaml():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("material_root: /tmp/test\nanchor_dir: 成品\n")
        path = f.name
    try:
        cfg = common.load_config(path)
        assert cfg["material_root"] == "/tmp/test"
        assert cfg["anchor_dir"] == "成品"
    finally:
        os.unlink(path)


def test_tools_config_path_uses_tools_dir():
    with tempfile.TemporaryDirectory() as tmp:
        path = common.tools_config_path(tmp)
        assert path is not None
        assert path.startswith(tmp)
        assert path.endswith("xie-zuo-su-cai/config.yaml")


def test_tools_config_path_returns_none_without_tools_dir():
    assert common.tools_config_path() is None


def test_load_config_with_fallback_reads_backup_when_primary_missing():
    with tempfile.TemporaryDirectory() as tmp:
        primary = os.path.join(tmp, "primary.yaml")
        backup_dir = tmp
        backup_path = common.tools_config_path(backup_dir)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w") as f:
            f.write("material_root: /backup/root\n")
        cfg = common.load_config_with_fallback(primary, tools_dir=backup_dir)
        assert cfg["material_root"] == "/backup/root"


def test_load_config_with_fallback_prefers_primary():
    with tempfile.TemporaryDirectory() as tmp:
        primary = os.path.join(tmp, "primary.yaml")
        backup_dir = tmp
        backup_path = common.tools_config_path(backup_dir)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(primary, "w") as f:
            f.write("material_root: /primary/root\n")
        with open(backup_path, "w") as f:
            f.write("material_root: /backup/root\n")
        cfg = common.load_config_with_fallback(primary, tools_dir=backup_dir)
        assert cfg["material_root"] == "/primary/root"


def test_resolve_material_root_uses_backup_when_primary_missing():
    with tempfile.TemporaryDirectory() as tmp:
        backup_dir = tmp
        backup_path = common.tools_config_path(backup_dir)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w") as f:
            f.write(f"material_root: {tmp}\n")
        # 指定一个不存在的 primary，让 fallback 生效
        primary = os.path.join(tmp, "missing.yaml")
        root = common.resolve_material_root(cfg_path=primary, tools_dir=backup_dir)
        assert root == tmp


def test_sanitize_topic_name_removes_illegal_chars():
    assert common.sanitize_topic_name("A/B 测试：主题？") == "A-B-测试-主题"


def test_topic_to_folder_name_uses_date_and_clean_topic():
    name = common.topic_to_folder_name("为什么AI写作总有AI味", "20260823")
    assert name == "20260823-为什么AI写作总有AI味"


def test_project_dir_creates_new_folder_for_new_topic():
    with tempfile.TemporaryDirectory() as tmp:
        d = common.project_dir(tmp, "新主题", date_str="20260823")
        assert d.endswith("20260823-新主题")
        assert os.path.isdir(d)


def test_project_dir_reuses_existing_folder():
    with tempfile.TemporaryDirectory() as tmp:
        first = common.project_dir(tmp, "已有主题", date_str="20260822")
        second = common.project_dir(tmp, "已有主题", date_str="20260823")
        assert first == second


def test_session_path_inside_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        path = common.session_path(tmp, "测试主题")
        assert path.endswith("01-会话状态.json")
        assert "测试主题" in path


def test_fragment_dir_inside_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        d = common.fragment_dir(tmp, "测试主题")
        assert d.endswith("02-素材碎片")
        assert os.path.isdir(d)


def test_material_doc_path_inside_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        path = common.material_doc_path(tmp, "测试主题")
        assert path.endswith("03-素材文档.md")
