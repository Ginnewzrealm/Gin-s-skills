#!/usr/bin/env python3
"""采集器 — 核心函数单元测试"""

import sys
import os
import tempfile
import zipfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import main
from scripts import chrome_launcher_adapter


class TestDetectInputType:
    """detect_input_type() 路由测试"""

    cases = [
        # (input, expected_type)
        ("https://mp.weixin.qq.com/s/abc", "weixin"),
        ("https://www.youtube.com/watch?v=xyz", "youtube"),
        ("https://youtu.be/xyz", "youtube"),
        ("https://xiaoyuzhoufm.com/episode/abc", "podcast"),
        ("https://ximalaya.com/abc", "podcast"),
        ("https://bilibili.com/video/abc", "podcast"),
        ("https://x.com/user/status/123", "x_twitter_status"),
        ("https://twitter.com/user/status/123", "x_twitter_status"),
        ("https://x.com/chuhaiqu/status/2088114146898559294?s=20", "x_twitter_status"),
        ("https://x.com/chuhaiqu/status/2084093147756527977?s=20", "x_twitter_status"),
        ("https://x.com/i/article/123", "x_twitter_article"),
        ("https://x.com/search?q=AI", "x_twitter_search"),
        ("https://x.com/chuhaiqu", "x_twitter_user"),
        ("https://twitter.com/chuhaiqu", "x_twitter_user"),
        ("https://example.com/article", "url"),
        ("/path/to/file.epub", "epub"),
        ("~/Documents/report.pdf", "document"),
        ("/tmp/data.txt", "document"),
        ("/notes/readme.md", "document"),
        ("/archive/doc.docx", "office"),
        ("/slides/presentation.pptx", "office"),
        ("/sheets/data.xlsx", "office"),
        ("/photos/image.jpg", "image"),
        ("/photos/screenshot.png", "image"),
        ("/audio/podcast.mp3", "audio"),
        ("/audio/recording.wav", "audio"),
        ("/archive/files.zip", "zip"),
    ]

    def test_url_types(self):
        for input_url, expected in self.cases:
            if input_url.startswith("http"):
                result = main.detect_input_type(input_url)
                assert result == expected, f"URL {input_url}: expected {expected}, got {result}"

    def test_file_types(self, tmp_path):
        for input_path, expected in self.cases:
            if not input_path.startswith("http"):
                if expected == "search":
                    continue  # non-existent path → search
                path = tmp_path / ("test" + input_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                result = main.detect_input_type(str(path))
                assert result == expected, f"File {input_path}: expected {expected}, got {result}"

    def test_nonexistent_path_is_search(self):
        result = main.detect_input_type("/nonexistent/keyword")
        assert result == "search"


class TestSaveContent:
    """save_content() 文件输出测试"""

    def test_saves_to_correct_subdir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COLLECTOR_DIR", str(tmp_path))
        content = "Hello world"
        result = main.save_content(content, "webpage", "Test Page", "https://example.com")

        assert tmp_path.joinpath("webpage").exists()
        assert Path(result).parent == tmp_path / "webpage"
        assert "Hello world" in Path(result).read_text(encoding="utf-8")

    def test_sanitizes_filename(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COLLECTOR_DIR", str(tmp_path))
        main.save_content("content", "webpage", "Test: Page / With | Bad * Chars?")
        files = list((tmp_path / "webpage").iterdir())
        assert len(files) == 1
        # No colon, slash, pipe, etc. in filename
        assert ":" not in files[0].name
        assert "/" not in files[0].name


class TestZipSlipProtection:
    """ZIP 路径遍历防护测试"""

    def test_zip_with_path_traversal_is_blocked(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COLLECTOR_DIR", str(tmp_path))

        malicious_zip = tmp_path / "evil.zip"
        with zipfile.ZipFile(str(malicious_zip), "w") as zf:
            zf.writestr("../../../etc/evil.txt", "should not be written here")
            zf.writestr("legitimate.txt", "normal content")

        with zipfile.ZipFile(str(malicious_zip), "r") as zf:
            extract_dir = tempfile.mkdtemp(prefix="zip_extract_")
            extract_dir_resolved = str(Path(extract_dir).resolve())
            for member in zf.namelist():
                member_path = Path(extract_dir, member)
                resolved_str = str(member_path.resolve())
                # 路径遍历条目会被跳过
                if not resolved_str.startswith(extract_dir_resolved):
                    # 验证这是那个恶意条目，而不是其他合法条目
                    assert ".." in member, f"Non-traversal path incorrectly blocked: {member}"
                    continue
                # 合法路径才走到这里
                member_path.parent.mkdir(parents=True, exist_ok=True)
                zf.extract(member, extract_dir)

            # 恶意文件不应该被写入
            assert not Path(extract_dir, "..", "..", "..", "etc", "evil.txt").exists()

    def test_normal_zip_extracts_correctly(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COLLECTOR_DIR", str(tmp_path))

        normal_zip = tmp_path / "normal.zip"
        with zipfile.ZipFile(str(normal_zip), "w") as zf:
            zf.writestr("docs/readme.txt", "hello")
            zf.writestr("docs/manual.pdf", "pdf content")

        with zipfile.ZipFile(str(normal_zip), "r") as zf:
            extract_dir = tempfile.mkdtemp(prefix="zip_extract_")
            extract_dir_resolved = str(Path(extract_dir).resolve())
            for member in zf.namelist():
                member_path = Path(extract_dir, member)
                resolved_str = str(member_path.resolve())
                assert resolved_str.startswith(extract_dir_resolved), \
                    f"Path {member} resolved to {resolved_str}, not under {extract_dir_resolved}"
                member_path.parent.mkdir(parents=True, exist_ok=True)
                zf.extract(member, extract_dir)

        assert Path(extract_dir, "docs/readme.txt").exists()
        assert Path(extract_dir, "docs/readme.txt").read_text() == "hello"


class TestGetProxy:
    """get_proxy() 配置文件读取测试"""

    def test_returns_none_when_no_config(self, monkeypatch, tmp_path):
        # Point to skill dir that doesn't exist
        monkeypatch.setattr(main, "__file__", str(tmp_path / "nonexistent.py"))
        result = main.get_proxy()
        assert result is None

    def test_returns_stripped_proxy(self, monkeypatch, tmp_path):
        # Create a mock proxy.config
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        proxy_file = skill_dir / "proxy.config"
        proxy_file.write_text("http://127.0.0.1:7890\n")

        monkeypatch.setattr(main, "__file__", str(skill_dir / "main.py"))
        result = main.get_proxy()
        assert result == "http://127.0.0.1:7890"

    def test_skips_commented_config(self, monkeypatch, tmp_path):
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        proxy_file = skill_dir / "proxy.config"
        proxy_file.write_text("# http://proxy.com:8080\n")

        monkeypatch.setattr(main, "__file__", str(skill_dir / "main.py"))
        result = main.get_proxy()
        assert result is None


class TestBrowserLauncherAdapterIntegration:
    """OpenCLI 浏览器 launcher adapter 集成测试"""

    def test_run_opencli_cmd_prepares_browser_and_cleans(self, monkeypatch):
        """run_opencli_cmd 成功路径：确保浏览器就绪、执行命令、清理"""
        calls = []

        def fake_ensure(session_name=None):
            calls.append(("ensure", session_name))
            return True, {"status": "success"}, "opencli-chrome-launcher"

        def fake_cleanup(session_name=None, source=None):
            calls.append(("cleanup", session_name, source))
            return {"status": "success"}

        def fake_subprocess_run(cmd, **kwargs):
            calls.append(("subprocess", cmd))
            class FakeResult:
                returncode = 0
                stdout = b"fake content"
                stderr = b""
            return FakeResult()

        monkeypatch.setattr(main, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(main, "cleanup_browser", fake_cleanup)
        monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

        result = main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                      "https://x.com/u/status/123")

        assert result.returncode == 0
        assert result.stdout == b"fake content"
        assert calls == [
            ("ensure", "collector"),
            ("subprocess", ["opencli", "twitter", "thread", "123"]),
            ("cleanup", "collector", "opencli-chrome-launcher"),
        ]

    def test_run_opencli_cmd_exits_when_browser_not_ready(self, monkeypatch):
        """浏览器就绪失败且不允许降级时，run_opencli_cmd 应退出"""
        def fake_ensure(session_name=None):
            return False, {"status": "failed", "message": "opencli 未安装"}, "opencli-chrome-launcher"

        def fake_cleanup(session_name=None, source=None):
            return {"status": "success"}

        monkeypatch.setattr(main, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(main, "cleanup_browser", fake_cleanup)

        with pytest.raises(SystemExit) as exc_info:
            main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                  "https://x.com/u/status/123", allow_fallback=False)
        assert exc_info.value.code == 1

    def test_run_opencli_cmd_fallback_returns_none(self, monkeypatch):
        """浏览器就绪失败但允许降级时，run_opencli_cmd 返回 None"""
        def fake_ensure(session_name=None):
            return False, {"status": "failed", "message": "opencli 未安装"}, "opencli-chrome-launcher"

        def fake_cleanup(session_name=None, source=None):
            return {"status": "success"}

        monkeypatch.setattr(main, "ensure_browser_ready", fake_ensure)
        monkeypatch.setattr(main, "cleanup_browser", fake_cleanup)

        result = main.run_opencli_cmd(["opencli", "twitter", "thread", "123"],
                                      "https://x.com/u/status/123", allow_fallback=True)
        assert result is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
