import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import topic_def


def test_topic_def_save_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = topic_def.save(
            material_root=tmp,
            topic="测试主题",
            key_question="为什么要测试",
            scope={"读者": "开发者"},
            success_criteria=["能生成文件"],
            constraints=["不联网"],
            hypotheses=["测试能发现问题"],
        )
        assert path.endswith("00-主题定义.md")
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "测试主题" in content
        assert "为什么要测试" in content
        assert "开发者" in content
        assert "能生成文件" in content


def test_topic_def_save_uses_defaults_for_empty_fields():
    with tempfile.TemporaryDirectory() as tmp:
        path = topic_def.save(tmp, "空主题")
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "空主题" in content
        assert "（待补充）" in content
