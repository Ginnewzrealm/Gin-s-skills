import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import version_bump


def test_bump_patch():
    with tempfile.TemporaryDirectory() as tmp:
        changelog = os.path.join(tmp, "CHANGELOG.md")
        with open(changelog, "w") as f:
            f.write("# CHANGELOG\n## 2026-08-22 · v0.1.0 · 新增\n- 初版\n")
        version_bump.bump(changelog, "patch", "fix bug")
        with open(changelog) as f:
            log = f.read()
        assert "0.1.1" in log
        assert "fix bug" in log


def test_bump_minor():
    with tempfile.TemporaryDirectory() as tmp:
        changelog = os.path.join(tmp, "CHANGELOG.md")
        with open(changelog, "w") as f:
            f.write("# CHANGELOG\n## 2026-08-22 · v0.1.0 · 新增\n- 初版\n")
        version_bump.bump(changelog, "minor", "new feature")
        with open(changelog) as f:
            log = f.read()
        assert "0.2.0" in log


def test_bump_from_empty_changelog():
    with tempfile.TemporaryDirectory() as tmp:
        changelog = os.path.join(tmp, "CHANGELOG.md")
        with open(changelog, "w") as f:
            f.write("# CHANGELOG\n")
        version_bump.bump(changelog, "patch", "first release")
        with open(changelog) as f:
            log = f.read()
        assert "0.0.1" in log
        assert "first release" in log
