from pathlib import Path


def test_polish_skill_input_is_human_revised_draft():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert ("人二改后" in content or "二次改写" in content), "missing human revision input description"
    assert "小标题" in content, "missing subheading mention"
