import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import build_doc
import fragment


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
