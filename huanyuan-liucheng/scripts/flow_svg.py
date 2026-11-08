# Copyright (c) 2026 Gin. All rights reserved. See LICENSE in the skill root.
"""Sized text + pinned local Dagre layout -> static, offline SVG."""
import html
import json
from pathlib import Path
import shutil
import subprocess
import unicodedata


ROOT = Path(__file__).resolve().parent


def esc(value):
    return html.escape(str(value), quote=True)


def text_width(text, size):
    # Conservative widths include padding for platform font variation.
    return sum(size * (1.02 if unicodedata.east_asian_width(c) in 'WFA' else .66) for c in text)


def wrap(text, width, size):
    lines = ['']
    for char in text:
        if char == '\n':
            lines.append('')
        elif lines[-1] and text_width(lines[-1] + char, size) > width:
            lines.append(char)
        else:
            lines[-1] += char
    return lines


def make_graph(model):
    nodes, edges = [], []
    for n in model['nodes']:
        kind = n['type']
        title = n.get('question', n.get('label', ''))
        lines = wrap(title, 235 if kind == 'decision' else 275, 15)
        owner = n.get('owner', '')
        owner_lines = wrap(owner, 235 if kind == 'decision' else 275, 12) if owner else []
        if kind == 'join':
            width = height = 16
            lines, owner_lines = [], []
        else:
            content_w = max([text_width(t, 15) for t in lines] + [text_width(t, 12) for t in owner_lines] + [70])
            content_h = len(lines) * 22 + len(owner_lines) * 18 + 22
            if kind == 'decision':
                width = max(340, 2 * (content_w + 28))
                height = max(132, 2 * (content_h + 12))
            else:
                width = max(270, content_w + 44)
                height = content_h + 24
        nodes.append({'id':n['id'],'kind':kind,'width':width,'height':height,'lines':lines,'owner_lines':owner_lines,'title':title})
        routes = n.get('branches', []) if kind == 'decision' else ([{'target':n['next'], 'back_edge':n.get('back_edge',False)}] if kind in {'start','action','join'} and 'next' in n else [])
        for i, route in enumerate(routes):
            lines_label = wrap(route.get('label',''),230,13)
            condition = route.get('condition','')
            lines_condition = wrap(condition,230,12)
            if route.get('condition_status',route.get('status')) == 'inferred':
                lines_condition.append('条件为推断')
            elif route.get('condition_status',route.get('status')) != 'confirmed' and condition and not any(word in condition for word in ('待确认','未说明','未知')):
                lines_condition.append('条件待确认')
            if route.get('target_status') == 'inferred':
                lines_condition.append('去向为推断')
            elif route.get('target_status') == 'unresolved' and not any(word in str(route.get('label',''))+condition for word in ('去向待确认','去向未说明')):
                lines_condition.append('去向待确认')
            labelled = kind == 'decision'
            lines_all = lines_label + lines_condition if labelled else []
            width_label = max([text_width(s,13) for s in lines_label]+[text_width(s,12) for s in lines_condition]+[0]) + 20 if labelled else 0
            edges.append({'id':f"{n['id']}-{i}",'source':n['id'],'target':route['target'],
                'width':width_label,'height':len(lines_all)*19+16 if labelled else 0,
                'labelpos':'r','labeloffset':14,'weight':1 if route.get('back_edge') else 50 if route.get('primary',not labelled) else 10,
                'back_edge':route.get('back_edge',False),'primary':route.get('primary',not labelled),
                'status':route.get('status','confirmed'),'lines_label':lines_label if labelled else [],
                'lines_condition':lines_condition if labelled else []})
    return {'nodes':nodes,'edges':edges}


def layout_graph(model):
    if not shutil.which('node'):
        raise ValueError('生成流程图需要 Node.js；请安装 Node.js 后重试，不能改为卡片列表交付。')
    result = subprocess.run(['node',str(ROOT/'layout.cjs')],input=json.dumps(make_graph(model),ensure_ascii=False),text=True,capture_output=True,timeout=40)
    if result.returncode:
        raise ValueError('流程图布局失败：'+result.stderr[-1200:])
    return json.loads(result.stdout)


def intersect(node, point):
    dx, dy = point['x']-node['x'], point['y']-node['y']
    a, b = node['width']/2, node['height']/2
    if not dx and not dy:
        return {'x':node['x'],'y':node['y']+b}
    ratio = abs(dx)/a+abs(dy)/b if node['kind']=='decision' else max(abs(dx)/a,abs(dy)/b)
    return {'x':node['x']+dx/ratio,'y':node['y']+dy/ratio}


def text_block(x,y,lines,size,fill,weight=400,anchor='middle',step=22):
    return ''.join(f'<text x="{x:.2f}" y="{y+i*step:.2f}" text-anchor="{anchor}" font-size="{size}" fill="{fill}" font-weight="{weight}">{esc(line)}</text>' for i,line in enumerate(lines))


def render_svg(model):
    graph = layout_graph(model)
    nodes = {n['id']:n for n in graph['nodes']}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="process-svg" width="{graph["width"]:.2f}" height="{graph["height"]:.2f}" viewBox="0 0 {graph["width"]:.2f} {graph["height"]:.2f}" role="img" aria-label="{esc(model["process"]["name"])}流程图">',
        '<defs><marker id="arrow-blue" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#1565c0"/></marker><marker id="arrow-orange" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#c65b17"/></marker></defs>']
    # Connectors first; labels and nodes then remain crisp above paths.
    for e in graph['edges']:
        points = e['points']
        points[0] = intersect(nodes[e['source']],points[1])
        points[-1] = intersect(nodes[e['target']],points[-2])
        color = 'blue' if e['primary'] and not e['back_edge'] else 'orange'
        d = 'M'+' L'.join(f"{p['x']:.2f},{p['y']:.2f}" for p in points)
        out.append(f'<g data-edge-source="{esc(e["source"])}" data-edge-target="{esc(e["target"])}" data-edge-id="{esc(e["id"])}" data-back-edge="{str(e["back_edge"]).lower()}"><path d="{d}" fill="none" stroke="{ "#1565c0" if color=="blue" else "#c65b17"}" stroke-width="2" marker-end="url(#arrow-{color})"/></g>')
    for e in graph['edges']:
        if not e['lines_label']: continue
        x,y,w,h = e['x'],e['y'],e['width'],e['height']
        color = '#155798' if e['primary'] else '#a34712'
        out.append(f'<g data-label-for="{esc(e["id"])}" data-x="{x:.2f}" data-y="{y:.2f}" data-width="{w:.2f}" data-height="{h:.2f}"><rect x="{x-w/2:.2f}" y="{y-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" fill="white" rx="4"/>')
        ty = y-h/2+20
        out.append(text_block(x-w/2+10,ty,e['lines_label'],13,color,650,'start',19))
        out.append(text_block(x-w/2+10,ty+len(e['lines_label'])*19,e['lines_condition'],12,'#57606c',400,'start',19))
        out.append('</g>')
    for n in graph['nodes']:
        x,y,w,h = n['x'],n['y'],n['width'],n['height']
        kind = n['kind']
        out.append(f'<g id="path-{esc(n["id"])}" data-node-id="{esc(n["id"])}" data-kind="{kind}" data-x="{x:.2f}" data-y="{y:.2f}" data-width="{w:.2f}" data-height="{h:.2f}">')
        if kind == 'decision':
            out.append(f'<polygon points="{x},{y-h/2} {x+w/2},{y} {x},{y+h/2} {x-w/2},{y}" fill="#fff6de" stroke="#d1a510" stroke-width="1.8"/>')
        elif kind == 'join':
            out.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#1565c0"><title>{esc(n["id"])} {esc(n["title"])}</title></circle></g>')
            continue
        else:
            bg,bd,radius = ('#fffbeb','#d7ad50',9) if kind=='unresolved' else ('#e8f5e9','#7fb285',h/2) if kind in {'start','terminal'} else ('#ffffff','#9ec3ee',9)
            dash = ' stroke-dasharray="5 4"' if kind=='unresolved' else ''
            out.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="{radius}" fill="{bg}" stroke="{bd}" stroke-width="1.7"{dash}/>')
            if kind=='action': out.append(f'<path d="M{x-w/2+2},{y-h/2+12} V{y+h/2-12}" stroke="#1565c0" stroke-width="4"/>')
        content_h = 18 + len(n['lines'])*22 + len(n['owner_lines'])*18
        top = y-content_h/2+12
        out.append(text_block(x,top,[n['id']],11,'#747d88',500,step=18))
        out.append(text_block(x,top+22,n['lines'],15,'#725400' if kind=='decision' else '#202c3b',600))
        out.append(text_block(x,top+22+len(n['lines'])*22,n['owner_lines'],12,'#667085',400,step=18))
        out.append('</g>')
    return ''.join(out)+'</svg>'
