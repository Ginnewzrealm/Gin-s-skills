import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import common
import session


def test_load_or_create_creates_default_state():
    with tempfile.TemporaryDirectory() as tmp:
        s = session.load_or_create(tmp, "测试主题")
        assert s["topic"] == "测试主题"
        assert s["rounds"] == 0
        assert s["methods_used"] == []
        assert s["domain"] is None
        assert s["fragments"] == []
        assert s["key_variables"] == []
        assert s["sections_covered"] == []
        assert s["status"] == "active"
        expected_path = os.path.join(
            tmp, f"{common.today_str()}-测试主题", "01-会话状态.json"
        )
        assert os.path.exists(expected_path)


def test_load_or_create_reads_existing():
    with tempfile.TemporaryDirectory() as tmp:
        session.set_domain(tmp, "另一主题", "面试")
        s = session.load_or_create(tmp, "另一主题")
        assert s["domain"] == "面试"


def test_increment_round():
    with tempfile.TemporaryDirectory() as tmp:
        session.increment_round(tmp, "r")
        session.increment_round(tmp, "r")
        s = session.load_or_create(tmp, "r")
        assert s["rounds"] == 2


def test_record_method_dedupes():
    with tempfile.TemporaryDirectory() as tmp:
        session.record_method(tmp, "m", "A")
        session.record_method(tmp, "m", "A")
        session.record_method(tmp, "m", "B")
        s = session.load_or_create(tmp, "m")
        assert s["methods_used"] == ["A", "B"]


def test_record_fragment_tracks_id_and_direction():
    with tempfile.TemporaryDirectory() as tmp:
        session.record_fragment(tmp, "f", "id-1", "困境", 0.8)
        session.record_fragment(tmp, "f", "id-1", "转折", 0.9)
        session.record_fragment(tmp, "f", "id-2", "困境", 0.7)
        s = session.load_or_create(tmp, "f")
        assert s["fragments"] == ["id-1", "id-2"]
        assert sorted(s["sections_covered"]) == ["困境", "转折"]


def test_set_domain():
    with tempfile.TemporaryDirectory() as tmp:
        session.set_domain(tmp, "d", "演讲稿")
        s = session.load_or_create(tmp, "d")
        assert s["domain"] == "演讲稿"


def test_mark_completed():
    with tempfile.TemporaryDirectory() as tmp:
        session.mark_completed(tmp, "c")
        s = session.load_or_create(tmp, "c")
        assert s["status"] == "completed"
