from pathlib import Path


def test_quality_skill_outputs_report_for_human_final_review():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "终审" in content, "missing final review mention"
    assert "修改建议" in content, "missing revision suggestion mention"
