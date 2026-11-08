"""Delivery contract: one business process, one continuous tree, one file."""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('single_flow_model', ROOT/'scripts/process_model.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class SingleMarkdownTests(unittest.TestCase):
    def model(self):
        return json.loads((ROOT/'tests/fixtures/sales-order.json').read_text())

    def test_render_writes_only_one_markdown_with_questions_inside(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = renderer.render_files(self.model(), Path(tmp))
            self.assertEqual([p.name for p in outputs], ['03 销售订单-流程说明.md'])
            self.assertEqual(list(Path(tmp).iterdir()), outputs)
            content = outputs[0].read_text()
            self.assertIn('## 待确认问题', content)
            self.assertIn('Q08', content)

    def test_phase_metadata_does_not_cut_paths_or_duplicate_common_tail(self):
        model = self.model()
        for i, node in enumerate(model['nodes']):
            node['phase'] = i  # Every node has a different presentation phase.
        content = renderer.render_markdown(model)
        flow = content.split('## 流程图', 1)[1].split('## 关键决策节点', 1)[0]
        self.assertEqual(flow.count('```text'), 1)
        self.assertNotIn('### ', flow)
        for node in model['nodes']:
            self.assertIn(node['id'], flow)
            for branch in node.get('branches', []):
                self.assertIn(branch['condition'], flow)
        definitions = [line for line in flow.splitlines() if '汇入' not in line and '返回' not in line]
        for node in model['nodes']:
            self.assertEqual(sum(bool(re.search(r'\b'+node['id']+r'\b', line)) for line in definitions), 1,
                             f"{node['id']} must have one definition in the full tree")
        self.assertIn('汇入 J01', flow)
        self.assertNotIn('转至', flow)

    def test_multiple_process_payload_is_rejected(self):
        model = self.model()
        model['processes'] = [dict(model['process']), dict(model['process'], name='采购')]
        errors = renderer.validate_model(model)
        self.assertTrue(any('一个流程' in error for error in errors), errors)

    def test_unpositioned_known_actions_stay_with_questions(self):
        model = self.model()
        model['pending_questions'][0]['text'] = '已知：售后拍摄质检视频。尚未说明：与寄回的先后？'
        content = renderer.render_markdown(model)
        flow, questions = content.split('## 待确认问题', 1)
        self.assertNotIn('拍摄质检视频', flow)
        self.assertIn('拍摄质检视频', questions)
        self.assertEqual(content.count('```text'), 1)

    def known_fact_model(self):
        model = self.model()
        quote = '售后会拍摄修好的产品视频并发给客户，具体操作时点未说明。'
        model['source_materials'].append({'id':'VIDEO', 'text':quote})
        model['evidence'].append({'id':'E_VIDEO','source_id':'VIDEO','quote':quote,'kind':'current'})
        model['pending_questions'][0]['known_facts'] = [{'text':quote,'evidence_refs':['E_VIDEO']}]
        return model

    def test_known_facts_render_only_below_questions_without_second_tree(self):
        model = self.known_fact_model()
        content = renderer.render_markdown(model)
        flow, questions = content.split('## 待确认问题', 1)
        self.assertNotIn('拍摄修好的产品视频', flow)
        self.assertIn('拍摄修好的产品视频', questions)
        self.assertEqual(content.count('```text'), 1)

    def test_known_facts_cannot_silently_use_future_plans(self):
        model = self.known_fact_model()
        model['evidence'][-1]['kind'] = 'goal'
        self.assertTrue(any('known_facts' in e for e in renderer.validate_model(model)))

    def test_inferred_order_requires_question_and_visible_marker(self):
        model = self.model()
        node = next(n for n in model['nodes'] if n['id']=='A01')
        node['next_status'] = 'inferred'
        model['pending_questions'] = [q for q in model['pending_questions'] if 'A01' not in q['related_nodes']]
        self.assertTrue(any('A01' in e for e in renderer.validate_model(model)))
        self.assertIn('衔接待核',renderer.render_tree(model))

    def test_independent_natural_language_case_keeps_lifecycle_return_and_merge(self):
        model = json.loads((ROOT/'tests/fixtures/coffee-repair.json').read_text())
        self.assertEqual(renderer.validate_model(model), [])
        with tempfile.TemporaryDirectory() as tmp:
            outputs = renderer.render_files(model, Path(tmp))
            self.assertEqual(len(outputs), 1)
            text = outputs[0].read_text()
            self.assertEqual(text.count('```text'), 1)
            tree = text.split('```text\n', 1)[1].split('\n```', 1)[0]
            for outcome in ('能直接维修', '配件缺货', '完全无法维修', '测试通过', '测试不通过'):
                self.assertIn('【'+outcome+'】', tree)
            self.assertIn('↩ 返回 A05', tree)
            self.assertIn('↪ 汇入 A05', tree)
            self.assertNotIn('文具', tree)
            self.assertNotIn('自动', tree)
            self.assertNotIn('视频', tree)
            self.assertIn('维修员现在会拍测试视频', text.split('## 待确认问题', 1)[1])

    def test_branch_uncertainty_survives_tree_and_details_even_with_path_note(self):
        for field, heading in [('condition_status', '条件'), ('target_status', '去向')]:
            for status, label in [('inferred', '推断'), ('unresolved', '待确认')]:
                with self.subTest(field=field, status=status):
                    model = self.model()
                    decision = next(n for n in model['nodes'] if n['id'] == 'D03')
                    branch = decision['branches'][0]
                    branch.update(condition_status='confirmed', target_status='confirmed',
                                  status=status, path_note='已有路径说明')
                    branch[field] = status
                    self.assertEqual(renderer.validate_model(model), [])
                    text = renderer.render_markdown(model)
                    tree = text.split('```text\n', 1)[1].split('\n```', 1)[0]
                    detail = text.split('### D03 ', 1)[1].split('### D04 ', 1)[0]
                    for section in [tree, detail]:
                        self.assertIn(heading+'：'+label, section)
                    self.assertIn('已有路径说明', tree)
                    self.assertIn('已有路径说明', detail)


if __name__ == '__main__':
    unittest.main()
