import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import process_model as renderer


class FlowSvgTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT / 'tests/fixtures/sales-order.json').read_text())

    def svg(self, model=None):
        output = renderer.render_path_map(model or self.model)
        self.assertIn('<svg ', output, '流程图必须是连线图形，而非卡片链接列表')
        return ET.fromstring(output)

    def groups(self, svg, attribute):
        return [n for n in svg.iter() if attribute in n.attrib]

    def test_every_model_edge_is_drawn_and_each_decision_is_a_diamond(self):
        svg = self.svg()
        expected = []
        for n in self.model['nodes']:
            if 'next' in n: expected.append((n['id'], n['next']))
            for b in n.get('branches', []): expected.append((n['id'], b['target']))
        edges = self.groups(svg, 'data-edge-source')
        self.assertCountEqual([(e.get('data-edge-source'),e.get('data-edge-target')) for e in edges], expected)
        self.assertEqual(len(self.groups(svg,'data-node-id')), len(self.model['nodes']))
        for n in self.groups(svg,'data-node-id'):
            if n.get('data-kind') == 'decision':
                self.assertTrue(any(e.tag.endswith('polygon') for e in n))

    def test_four_branches_have_separate_edges_and_full_conditions(self):
        decision = next(n for n in self.model['nodes'] if n['id']=='D03')
        for i in (2,3):
            decision['branches'].append({'label':f'风险等级{i}', 'condition':f'风险分值等于{i}且没有其他限制', 'target':f'U0{i}', 'status':'unresolved','primary':False})
        svg = self.svg()
        edges = [e for e in self.groups(svg,'data-edge-source') if e.get('data-edge-source')=='D03']
        self.assertEqual(len(edges),4)
        text=''.join(svg.itertext())
        for b in decision['branches']: self.assertIn(b['condition'],text)

    def test_return_path_and_merge_keep_real_targets_without_duplicate_nodes(self):
        node = next(n for n in self.model['nodes'] if n['id']=='U01')
        node.update(type='action', owner='业务员',label='修改销售订单',next='A03',back_edge=True)
        svg=self.svg()
        self.assertTrue(any(e.get('data-edge-source')=='U01' and e.get('data-edge-target')=='A03' for e in self.groups(svg,'data-edge-source')))
        self.assertEqual(sum(n.get('data-node-id')=='J01' for n in self.groups(svg,'data-node-id')),1)

    def test_long_text_is_preserved_and_node_boxes_do_not_overlap(self):
        decision=next(n for n in self.model['nodes'] if n['id']=='D01')
        decision['question']='客户申请的付款期限是否符合该客户所属类别已经确认的现行账期规则？'
        decision['branches'][0]['condition']='客户属于已有授信且不存在逾期的老客户，并且申请期限不超过本次审批确认的三十个自然日'
        svg=self.svg()
        text=''.join(svg.itertext())
        self.assertIn(decision['question'],text)
        self.assertIn(decision['branches'][0]['condition'],text)
        nodes=self.groups(svg,'data-node-id')
        for i,a in enumerate(nodes):
            ax,ay,aw,ah=[float(a.get(k)) for k in ('data-x','data-y','data-width','data-height')]
            for b in nodes[i+1:]:
                bx,by,bw,bh=[float(b.get(k)) for k in ('data-x','data-y','data-width','data-height')]
                self.assertFalse(abs(ax-bx)<(aw+bw)/2 and abs(ay-by)<(ah+bh)/2, (a.get('data-node-id'),b.get('data-node-id')))

    def test_plain_flow_needs_no_invented_decision_or_terminal(self):
        self.model['nodes']=[{'id':'S01','type':'start','label':'收到申请','next':'A01'}, {'id':'A01','type':'action','owner':'文员','label':'登记申请','next':'U01'}, {'id':'U01','type':'unresolved','label':'后续去向未说明'}]
        svg=self.svg()
        self.assertEqual(len(self.groups(svg,'data-node-id')),3)
        self.assertFalse(any(n.get('data-kind') in {'decision','terminal'} for n in self.groups(svg,'data-node-id')))

    def test_unknown_condition_is_visible_on_the_graph(self):
        decision=next(n for n in self.model['nodes'] if n['id']=='D04')
        decision['branches'][0]['condition']='满足审批触发规则'
        decision['branches'][0]['condition_status']='unresolved'
        svg=self.svg()
        label=next(e for e in self.groups(svg,'data-label-for') if e.get('data-label-for')=='D04-0')
        self.assertIn('条件待确认',''.join(label.itertext()))

    def test_inference_status_survives_both_graph_and_details(self):
        decision=next(n for n in self.model['nodes'] if n['id']=='D04')
        branch=decision['branches'][0]
        branch.update(condition='订单金额大于二十万元，适用范围待确认',status='inferred',condition_status='inferred',target_status='inferred')
        graph=renderer.render_path_map(self.model)
        details=renderer.render_decision_details(self.model)
        self.assertIn('条件为推断',graph)
        self.assertIn('条件（推断）',details)
        self.assertIn('去向（推断）',details)

    def test_declared_return_keeps_forward_actions_below_the_decision(self):
        from flow_svg import layout_graph
        self.model['nodes']=[
            {'id':'S01','type':'start','label':'收到问题','next':'D01'},
            {'id':'D01','type':'decision','question':'能否远程解决？','owner':'技术员','branches':[
                {'label':'能','condition':'可远程解决','target':'A01','primary':True,'status':'confirmed'},
                {'label':'不能','condition':'需返厂','target':'U01','primary':False,'status':'confirmed'}]},
            {'id':'A01','type':'action','owner':'技术员','label':'指导客户操作','next':'D02'},
            {'id':'D02','type':'decision','question':'是否仍未解决？','owner':'客户','branches_complete':False,'branches':[
                {'label':'仍未解决','condition':'客户反馈未解决','target':'D01','primary':True,'status':'confirmed','back_edge':True}]},
            {'id':'U01','type':'unresolved','label':'返厂后去向未说明'}]
        nodes={n['id']:n for n in layout_graph(self.model)['nodes']}
        self.assertLess(nodes['D01']['y'],nodes['A01']['y'])
        self.assertLess(nodes['A01']['y'],nodes['D02']['y'])

if __name__=='__main__': unittest.main()
