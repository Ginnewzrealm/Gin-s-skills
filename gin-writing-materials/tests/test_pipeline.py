import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import fragment
import pipeline
import session
import topic_def


def test_pipeline_builds_from_topic_definition():
    with tempfile.TemporaryDirectory() as tmp:
        topic = "管线主题"
        topic_def.save(tmp, topic, key_question="核心问题", scope={"读者": "创作者"})
        session.set_closure(tmp, topic, knowledge="closed", confirmed=True)
        for i, direction in enumerate(["钩子", "核心论证", "案例支撑", "结尾升华", "钩子"]):
            fragment.create(
                material_root=tmp,
                topic=topic,
                domain="writing",
                method="A",
                direction=direction,
                confidence="confirmed",
                quote=f"原话{i}",
                scene="场景",
                interpretation=["解读"],
                anchor="a.md",
                source="第1轮",
            )
        path = pipeline.run(tmp, topic, judgment="判断", reader_question="追问")
        assert path.endswith("03-素材文档.md")
        assert "核心问题" in open(path, encoding="utf-8").read()
        state = session.load_or_create(tmp, topic)
        assert state["stage"] == "completed"
        assert state["status"] == "completed"


def test_pipeline_accepts_closed_small_idea_without_fixed_section_count():
    with tempfile.TemporaryDirectory() as tmp:
        topic = "小灵感"
        topic_def.save(tmp, topic, key_question="一个小问题")
        session.set_seed(tmp, topic, "一个还没想清楚的小灵感")
        session.set_closure(tmp, topic, knowledge="closed", confirmed=True)
        fragment.create(
            material_root=tmp,
            topic=topic,
            domain="writing",
            method="A",
            direction="",
            confidence="confirmed",
            quote="我其实想写这个，但不知道为什么。",
            scene="刚想到时",
            interpretation=["需要继续澄清"],
            anchor="",
            source="T001",
            source_turn="T001",
            role="core",
            relation="support",
        )
        path = pipeline.run(tmp, topic, judgment="这是一个待展开判断")
        assert path.endswith("03-素材文档.md")
