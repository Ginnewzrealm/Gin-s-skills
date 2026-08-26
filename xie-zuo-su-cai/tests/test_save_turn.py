import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import save_turn
import session


def test_save_turn_appends_conversation_log():
    with tempfile.TemporaryDirectory() as tmp:
        log_path, frag_path = save_turn.save_turn(
            material_root=tmp,
            topic="测试主题",
            question="你最近怎么样？",
            answer="凌晨两点还在写代码。",
        )
        assert log_path.endswith("00-需求澄清.md")
        assert os.path.exists(log_path)
        content = open(log_path, encoding="utf-8").read()
        assert "你最近怎么样？" in content
        assert "凌晨两点还在写代码。" in content
        assert frag_path is None


def test_save_turn_updates_session_rounds():
    with tempfile.TemporaryDirectory() as tmp:
        save_turn.save_turn(tmp, "r", "q1", "a1")
        save_turn.save_turn(tmp, "r", "q2", "a2")
        s = session.load_or_create(tmp, "r")
        assert s["rounds"] == 2


def test_save_turn_creates_fragment_when_confidence_given():
    with tempfile.TemporaryDirectory() as tmp:
        log_path, frag_path = save_turn.save_turn(
            material_root=tmp,
            topic="测试主题",
            question="有没有一个具体时刻？",
            answer="有一天我发了一个 skill，两周没人用。",
            method="A",
            direction="钩子",
            confidence="confirmed",
            interpretation=["反馈消失的具体表现"],
        )
        assert frag_path is not None
        assert frag_path.endswith(".md")
        assert os.path.exists(frag_path)
        content = open(frag_path, encoding="utf-8").read()
        assert "用户原始表达" in content
        assert "AI 追问" in content
        assert "有一天我发了一个 skill" in content


def test_save_turn_records_method_in_session():
    with tempfile.TemporaryDirectory() as tmp:
        save_turn.save_turn(tmp, "m", "q", "a", method="B")
        s = session.load_or_create(tmp, "m")
        assert "B" in s["methods_used"]
