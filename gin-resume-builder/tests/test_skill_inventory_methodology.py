from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_inventory_methodology_defines_the_four_candidate_types():
    text = (ROOT / "references" / "skill-inventory-methodology.md").read_text()

    for term in ("能力", "技能", "经验", "资源"):
        assert term in text


def test_skill_inventory_methodology_requires_goal_and_evidence_before_writeback():
    text = (ROOT / "references" / "skill-inventory-methodology.md").read_text()

    assert "目标卡" in text
    assert "证据" in text
    assert "用户确认" in text
    assert "skills.md" in text


def test_router_and_inventory_standard_expose_skill_inventory_mode():
    router = (ROOT / "SKILL.md").read_text()
    standard = (ROOT / "references" / "skills-inventory-standard.md").read_text()

    assert "技能盘点" in router
    assert "skill-inventory-methodology.md" in router
    assert "资源不等于技能" in standard
