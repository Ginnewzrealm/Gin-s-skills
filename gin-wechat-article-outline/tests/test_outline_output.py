from pathlib import Path


def test_outline_skill_requires_ranked_candidates():
    skill_md = Path(__file__).parent.parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    required = ["推荐排序", "推荐理由", "适用场景", "风险点"]
    for item in required:
        assert item in content, f"{item} missing from outline SKILL.md"
