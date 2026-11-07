import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTICE = "Copyright (c) 2026 Gin. All rights reserved."


class CopyrightNoticeTests(unittest.TestCase):
    def test_license_is_explicitly_proprietary(self):
        license_path = ROOT / "LICENSE"

        self.assertTrue(license_path.is_file(), "skill must include its own LICENSE")
        text = license_path.read_text(encoding="utf-8")
        self.assertIn(NOTICE, text)
        self.assertIn("No permission is granted", text)
        for restriction in ("copy", "modify", "distribute", "commercial", "artificial intelligence"):
            self.assertIn(restriction, text.lower())

    def test_skill_and_renderer_point_to_the_same_notice(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        script_text = (ROOT / "scripts" / "process_model.py").read_text(encoding="utf-8")

        self.assertIn(NOTICE, skill_text)
        self.assertIn("See [LICENSE](LICENSE)", skill_text)
        self.assertIn(NOTICE, script_text)
        self.assertIn("See LICENSE in the skill root", script_text)

    def test_generated_business_documents_do_not_claim_gin_copyright(self):
        fixture = ROOT / "tests" / "fixtures" / "sales-order.json"
        script = ROOT / "scripts" / "process_model.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(script), "render", str(fixture), "--output-dir", tmp],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            for path in Path(tmp).iterdir():
                if path.suffix in {".md", ".html"}:
                    self.assertNotIn(NOTICE, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
