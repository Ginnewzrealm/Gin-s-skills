from pathlib import Path


def test_khazix_writer_outputs_draft_for_human_revision():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "二次改写" in content, "missing human revision mention"
    assert "初稿" in content, "missing draft mention"
