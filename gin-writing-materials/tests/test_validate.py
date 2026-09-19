import os
import sys
import tempfile
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import fragment
import validate


def test_validate_session_insufficient():
    with tempfile.TemporaryDirectory() as tmp:
        # 创建 2 个 confirmed 碎片
        for i in range(2):
            fragment.create(
                material_root=tmp,
                topic="测试",
                domain="writing",
                method="A",
                direction="钩子",
                confidence="confirmed",
                quote=f"原话{i}",
                scene="场景",
                interpretation=["角度"],
                anchor="a.md",
                source="第1轮",
            )
        result = validate.validate_session(tmp, "测试")
        assert result["ok"] is False
        assert result["confirmed_count"] == 2


def test_validate_session_sufficient():
    with tempfile.TemporaryDirectory() as tmp:
        directions = ["钩子", "核心论证", "案例支撑", "结尾升华", "钩子"]
        for i, d in enumerate(directions):
            fragment.create(
                material_root=tmp,
                topic="测试",
                domain="writing",
                method="A",
                direction=d,
                confidence="confirmed",
                quote=f"原话{i}",
                scene="场景",
                interpretation=["角度"],
                anchor="a.md",
                source="第1轮",
            )
        result = validate.validate_session(tmp, "测试")
        assert result["ok"] is True
        assert result["confirmed_count"] == 5


def test_validate_session_errors_make_session_invalid():
    with tempfile.TemporaryDirectory() as tmp:
        fragment.create(
            material_root=tmp,
            topic="坏碎片",
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
        result = validate.validate_session(tmp, "坏碎片")
        assert result["ok"] is False
        assert result["errors"]


def test_completeness_score_red_and_green():
    with tempfile.TemporaryDirectory() as tmp:
        # 空会话
        score = validate.completeness_score(tmp, "空")
        assert score["素材"]["light"] == "🔴"
        assert score["章节"]["light"] == "🔴"
        # 创建足够碎片
        directions = ["钩子", "核心论证", "案例支撑", "结尾升华", "钩子"]
        for i, d in enumerate(directions):
            fragment.create(
                material_root=tmp,
                topic="满",
                domain="writing",
                method="A",
                direction=d,
                confidence="confirmed",
                quote=f"原话{i}",
                scene="场景",
                interpretation=["角度"],
                anchor="a.md",
                source="第1轮",
            )
        score = validate.completeness_score(tmp, "满")
        assert score["素材"]["light"] == "🟢"
        assert score["章节"]["light"] == "🟢"


def test_completeness_score_yellow_for_partial_sections():
    with tempfile.TemporaryDirectory() as tmp:
        # 只覆盖 1 个章节（阈值 2 的一半）→ 章节应为 🟡
        fragment.create(
            material_root=tmp,
            topic="半",
            domain="writing",
            method="A",
            direction="钩子",
            confidence="confirmed",
            quote="原话",
            scene="场景",
            interpretation=["角度"],
            anchor="a.md",
            source="第1轮",
        )
        score = validate.completeness_score(tmp, "半")
        assert score["章节"]["current"] == 1
        assert score["章节"]["light"] == "🟡"


def test_validate_cli_returns_nonzero_for_incomplete_session():
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(os.path.dirname(__file__), "..", "scripts", "validate.py")
        result = subprocess.run(
            [sys.executable, script, "--material-root", tmp, "--topic", "空"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert '"ok": false' in result.stdout
