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


def test_skill_inventory_methodology_matches_existing_knowledge_base_fields():
    methodology = (ROOT / "references" / "skill-inventory-methodology.md").read_text()
    structure = (ROOT / "references" / "knowledge-structure.md").read_text()
    router = (ROOT / "SKILL.md").read_text()

    assert "四维详情" in methodology
    assert "事实佐证" in methodology
    assert "行为证据沿用 source/confidence" in methodology
    assert "资源线索不单独建技能条目" in methodology
    assert "证书只能证明学习或通过考试，不能单独支持技能确认" in methodology
    assert "盘点结束快照" in methodology
    assert "四维详情 + 反事实校验" in structure
    assert "四维详情 + 反事实校验" in router
