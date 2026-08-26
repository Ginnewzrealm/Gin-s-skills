import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import common
import fragment


def test_create_and_list_fragments():
    with tempfile.TemporaryDirectory() as tmp:
        fid = fragment.create(
            material_root=tmp,
            topic="测试主题",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["角度1"],
            anchor="anchor.md",
            source="第1轮",
        )
        frags = fragment.list_fragments(tmp, "测试主题")
        assert len(frags) == 1
        assert frags[0].endswith(".md")
        assert frags[0] == fid


def test_create_fragment_uses_date_seq_filename():
    with tempfile.TemporaryDirectory() as tmp:
        fid = fragment.create(
            material_root=tmp,
            topic="测试主题",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["角度1"],
            anchor="anchor.md",
            source="第1轮",
        )
        basename = os.path.basename(fid)
        assert basename.startswith(common.today_str())
        assert re.match(r"^\d{8}-\d{3}\.md$", basename)


def test_fragment_seq_resets_per_date():
    with tempfile.TemporaryDirectory() as tmp:
        # 模拟旧日期的碎片
        d = common.fragment_dir(tmp, "测试主题")
        with open(os.path.join(d, "20260822-001.md"), "w") as f:
            f.write("---\ntopic: 测试主题\n---\n")
        with open(os.path.join(d, "20260822-002.md"), "w") as f:
            f.write("---\ntopic: 测试主题\n---\n")

        # 今天创建新碎片，序号应从 001 开始
        fid = fragment.create(
            material_root=tmp,
            topic="测试主题",
            domain="writing",
            method="B",
            direction="核心论证",
            confidence="confirmed",
            quote="今天的原话",
            scene="今天",
            interpretation=["角度"],
            anchor="b.md",
            source="第2轮",
        )
        assert os.path.basename(fid).endswith("-001.md")


def test_validate_fragment():
    with tempfile.TemporaryDirectory() as tmp:
        fid = fragment.create(
            material_root=tmp,
            topic="测试主题",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["角度1"],
            anchor="anchor.md",
            source="第1轮",
        )
        errors = fragment.validate(fid)
        assert errors == []


def test_read_parses_frontmatter_and_body():
    with tempfile.TemporaryDirectory() as tmp:
        fid = fragment.create(
            material_root=tmp,
            topic="测试主题",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["角度1"],
            anchor="anchor.md",
            source="第1轮",
        )
        fm, body = fragment.read(fid)
        assert fm["topic"] == "测试主题"
        assert fm["method"] == "A"
        assert fm["confidence"] == "confirmed"
        assert "## 原话" in body
        assert "原话" in body
