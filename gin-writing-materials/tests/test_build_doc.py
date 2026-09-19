import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import build_doc
import fragment
import session
import pytest
import subprocess
import sys


def test_build_doc_contains_sections():
    with tempfile.TemporaryDirectory() as tmp:
        fragment.create(
            material_root=tmp,
            topic="AI味",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="大众看够了悬念",
            scene="对比标题",
            interpretation=["悬念=营销味"],
            anchor="a.md",
            source="第1轮",
        )
        path = build_doc.build(
            material_root=tmp,
            topic="AI味",
            key_question="为什么AI写作总有AI味",
            scope={"读者": "普通读者", "文体": "公众号"},
            success_criteria=["读者能识别AI味来源"],
            constraints=["不搜网络"],
            hypotheses=["AI味来自材料不足"],
            judgment="AI味不是风格问题",
            reader_question="那怎么改",
        )
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "给 human-writing 的输入" in content
        assert "钩子" in content
        assert "大众看够了悬念" in content
        assert "素材 #1" in content
        assert path.endswith("03-素材文档.md")


def test_build_doc_groups_by_direction():
    with tempfile.TemporaryDirectory() as tmp:
        fragment.create(
            material_root=tmp,
            topic="分组",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="钩子原话",
            scene="开头",
            interpretation=["吸引注意"],
            anchor="h.md",
            source="第1轮",
        )
        fragment.create(
            material_root=tmp,
            topic="分组",
            domain="writing",
            method="B",
            direction="核心论证",
            confidence="confirmed",
            quote="论证原话",
            scene="正文",
            interpretation=["支撑论点"],
            anchor="c.md",
            source="第2轮",
        )
        path = build_doc.build(
            material_root=tmp,
            topic="分组",
            key_question="如何分组",
            scope={},
            success_criteria=[],
            constraints=[],
            hypotheses=[],
            judgment="可以分组",
            reader_question="然后呢",
        )
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content.index("## 钩子") < content.index("## 核心论证")
        assert "素材 #1" in content
        assert "素材 #2" in content


def test_build_doc_rejects_invalid_fragments_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        fragment.create(
            material_root=tmp,
            topic="坏文档",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="",
            scene="场景",
            interpretation=[],
            anchor="",
            source="第1轮",
        )
        with pytest.raises(ValueError, match="碎片校验失败"):
            build_doc.build(
                material_root=tmp,
                topic="坏文档",
                key_question="问题",
                scope={},
                success_criteria=[],
                constraints=[],
                hypotheses=[],
                judgment="判断",
                reader_question="追问",
            )


def test_build_doc_includes_topic_definition_constraints():
    with tempfile.TemporaryDirectory() as tmp:
        fragment.create(
            material_root=tmp,
            topic="定义输入",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["解读"],
            anchor="a.md",
            source="第1轮",
        )
        path = build_doc.build(
            material_root=tmp,
            topic="定义输入",
            key_question="问题",
            scope={"读者": "创作者", "文体": "评论", "篇幅目标": "长文", "在范围内": "经验", "不在范围内": "新闻"},
            success_criteria=["标准一"],
            constraints=["约束一"],
            hypotheses=["假设一"],
            judgment="判断",
            reader_question="追问",
        )
        content = open(path, encoding="utf-8").read()
        assert "**读者**：创作者" in content
        assert "**文体**：评论" in content
        assert "标准一" in content
        assert "约束一" in content


def test_build_doc_cli_shows_help():
    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "build_doc.py")
    result = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--material-root" in result.stdout


def test_build_doc_contains_seed_qud_and_unclassified_material():
    with tempfile.TemporaryDirectory() as tmp:
        topic = "灵感稿"
        session.set_seed(tmp, topic, "准备越充分，反而越不想开始")
        session.set_qud(tmp, topic, main_qud="为什么准备会阻碍开始？", current_qud="哪次经历最能说明它？")
        session.add_branch(tmp, topic, "B001", "另一个关于完美主义的旁支", "需要单独展开")
        session.set_closure(
            tmp,
            topic,
            knowledge="closed",
            public_material="anonymize",
            confirmed=True,
            unresolved=["还缺一个反例"],
        )
        fragment.create(
            material_root=tmp,
            topic=topic,
            domain="writing",
            method="A",
            direction="",
            confidence="confirmed",
            quote="我准备了三天，最后还是没开始。",
            scene="一次拖延",
            interpretation=["准备可能变成逃避"],
            anchor="",
            source="T001",
            source_turn="T001",
            role="core",
            relation="support",
        )
        path = build_doc.build(
            material_root=tmp,
            topic=topic,
            key_question="为什么准备会阻碍开始？",
            scope={},
            success_criteria=[],
            constraints=[],
            hypotheses=[],
            judgment="准备有时是逃避",
            reader_question="怎么识别？",
            force=True,
        )
        content = open(path, encoding="utf-8").read()
        assert "## 原始灵感" in content
        assert "准备越充分，反而越不想开始" in content
        assert "## 主线与旁支" in content
        assert "B001" in content
        assert "## 未分类素材" in content
        assert "knowledge_closure: closed" in content
        assert "public_material: anonymize" in content
        assert "还缺一个反例" in content
