"""Career investment audit skill structure checks.

These tests intentionally exercise the contract of the Markdown skill rather than
implementation details.  They are kept dependency-free so the repository's test
runner can execute them with the Python standard library.
"""

from pathlib import Path
import re
import unittest


SKILL_PATH = Path(__file__).parents[1] / "SKILL.md"


class CareerInvestmentAuditSkillStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_PATH.read_text(encoding="utf-8")

    def test_frontmatter_identifies_skill_and_has_trigger_description(self):
        self.assertTrue(self.text.startswith("---\n"))
        frontmatter = self.text.split("---\n", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name:\s*career-investment-audit\s*$")
        self.assertRegex(frontmatter, r"(?m)^description:\s*.+")

    def test_skill_is_concise_and_describes_three_review_stages(self):
        self.assertLessEqual(len(self.text.splitlines()), 500)
        for phrase in ("面试前初审", "生成验证问题", "面试后复审"):
            self.assertIn(phrase, self.text)

    def test_keeps_evidence_layers_separate(self):
        for phrase in ("事实", "用户解释", "AI 推测", "待验证"):
            self.assertIn(phrase, self.text)
        for label in ("[事实]", "[用户解释]", "[AI推测]", "[待验证]"):
            self.assertIn(label, self.text)
        self.assertIn("证据层级", self.text)

    def test_covers_investment_and_return_dimensions(self):
        for phrase in ("时间", "精力", "通勤", "加班", "机会成本", "健康", "合同风险"):
            self.assertIn(phrase, self.text)
        for phrase in ("现金流", "能力", "作品", "方法论", "认知", "品牌", "人脉", "成就点"):
            self.assertIn(phrase, self.text)

    def test_achievement_labels_and_evaluation_dimensions_are_explicit(self):
        for label in ("机会", "承诺", "形成", "兑现"):
            self.assertIn(label, self.text)
        for dimension in ("可核验性", "可分离性", "可复用性", "可兑现性", "个人贡献确定度"):
            self.assertIn(dimension, self.text)
        self.assertRegex(self.text, r"主观分数.{0,20}(客观|真理)|客观.{0,20}主观分数")

    def test_interview_question_policy_is_bounded_and_prioritized(self):
        self.assertRegex(self.text, r"最多.{0,8}5 个")
        self.assertIn("不承诺一轮覆盖全部维度", self.text)
        self.assertIn("后续问题", self.text)
        for phrase in ("决策影响", "不确定性", "工作强度", "权限", "绩效", "成果归属", "证据可携带性", "团队稳定性"):
            self.assertIn(phrase, self.text)

    def test_fixed_output_and_policy_boundaries_are_present(self):
        for phrase in ("当前结论", "投入审计", "回报审计", "成就点表", "证据缺口", "风险", "置信度", "下一步"):
            self.assertIn(phrase, self.text)
        self.assertIn("移民", self.text)
        self.assertIn("法律", self.text)
        self.assertIn("财税", self.text)
        self.assertRegex(self.text, r"核验(具体规则|当地规则|适用规则)")

    def test_cross_reference_names_existing_skill_without_copying_it(self):
        self.assertIn("achievement-point-coach", self.text)
        self.assertIn("已发生项目是否具备成就资格", self.text)
        self.assertIn("回填到本审计报告", self.text)
        self.assertIn("gin-resume-builder", self.text)
        self.assertIn("生成面试验证问题", self.text)
        # The companion skill may be reused by name and dimensions only; this
        # file should remain a concise audit skill rather than a copied manual.
        self.assertLess(len(re.findall(r"严格一问一答", self.text)), 2)


if __name__ == "__main__":
    unittest.main()
