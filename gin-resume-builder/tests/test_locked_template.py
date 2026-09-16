"""Check generated documents, not mere CSS/string presence."""
import copy
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import html_renderer as hr


def resume():
    return json.loads((ROOT / 'tests/fixtures/locked_resume.json').read_text())


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_complete_header_and_front_order():
    body = hr.build_body(resume())
    header = body.split('</header>')[0]
    for value in resume()['basic'].values():
        assert value in header
    assert body.index('岗位匹配') < body.index('工作经历')
    assert 'data-section="work"' in body
    assert 'data-section="projects"' in body
    assert 'data-section="competencies"' in body
    assert 'data-section="skills"' in body


@pytest.mark.parametrize('theme', ['minimal', 'bank', 'editorial'])
@pytest.mark.parametrize('editable', [False, True])
def test_theme_applied_to_actual_body_and_identical_styles(theme, editable):
    r = resume()
    source = hr.render(r, theme=theme, editable=editable)
    body = next(a for tag, a in Document(source).elements if tag == 'body')
    assert body.get('data-theme') == theme
    assert body.get('class', '') == ('' if theme == 'minimal' else 'theme-' + theme)
    assert '{{' not in source
    assert ':nth-of-type(' not in source
    assert 'localStorage.getItem(\'resume-theme\')' not in source
    for value in r['basic'].values():
        assert value in source
    styles = source.split('<style', 1)[1].split('</head>')[0]
    other = hr.render(r, theme=theme, editable=not editable)
    assert styles == other.split('<style', 1)[1].split('</head>')[0]


@pytest.mark.parametrize('key', ['姓名', '联系电话', '邮箱', '居住地', '职位', '学历', '年龄'])
def test_missing_required_header_is_reported_before_render(key):
    r = resume()
    del r['basic'][key]
    with pytest.raises(ValueError, match='缺少'):
        hr.render(r)


def test_missing_or_empty_front_section_is_error():
    for empty in (False, True):
        r = resume()
        if empty:
            r['sections'][-1]['items'] = []
        else:
            r['sections'].pop()
        with pytest.raises(ValueError, match='岗位'):
            hr.render(r)


def test_aliases_not_duplicated_and_education_section_preserved_in_header():
    r = resume()
    r['basic'].update({'电话': '13900000000', '城市': '上海', '求职意向': '商业化策略负责人'})
    del r['basic']['学历']
    r['sections'].append({'title':'教育背景','items':['示例大学 本科']})
    source = hr.render(r)
    header = source.split('<header')[1].split('</header>')[0]
    for value in ('13900000000', '上海', '商业化策略负责人', '示例大学 本科'):
        assert header.count(value) == 1


def test_escape_content_and_titles():
    r = resume()
    r['title'] = '</title><script>alert(1)</script>'
    r['sections'][0]['entries'][0].update(org='<img src=x>', org_note='<script>bad</script>')
    source = hr.render(r)
    assert '<img src=x>' not in source
    assert '<script>bad' not in source
    assert '&lt;img src=x&gt;' in source


def test_invalid_theme_rejected():
    with pytest.raises(ValueError, match='theme'):
        hr.render(resume(), theme='unknown')


def test_workspace_keeps_selected_theme(tmp_path):
    out = tmp_path / '基础简历.html'
    hr.save_workspace(resume(), {'theme':'bank'}, out)
    assert 'data-theme="bank"' in out.read_text()


def test_cli_and_structure_check(tmp_path):
    data = resume()
    src = tmp_path / 'resume.json'
    src.write_text(json.dumps(data, ensure_ascii=False))
    out = tmp_path / 'resume.html'
    result = subprocess.run([sys.executable, str(ROOT/'scripts/html_renderer.py'), '--resume', str(src), '--out', str(out), '--theme', 'editorial', '--editable'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'data-theme="editorial"' in out.read_text()
    check = subprocess.run([sys.executable, str(ROOT/'scripts/resume_structure_check.py'), '--resume', str(src)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    data['basic'].pop('年龄')
    src.write_text(json.dumps(data, ensure_ascii=False))
    previous = out.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT/'scripts/html_renderer.py'), '--resume', str(src), '--out', str(out)], capture_output=True, text=True)
    assert result.returncode == 2
    assert '年龄' in result.stderr
    assert out.read_bytes() == previous
    result = subprocess.run([sys.executable, str(ROOT/'scripts/resume_structure_check.py'), '--resume', str(src)], capture_output=True, text=True)
    assert result.returncode == 2
    assert '年龄' in result.stdout


def test_review_preview_includes_actual_render_schema():
    import resume_review_gate
    text = resume_review_gate.format_resume_text(resume())
    for value in resume()['basic'].values():
        assert value in text
    assert text.index('岗位匹配') < text.index('工作经历')
    for field in ('核心职责','关键业绩','专业能力','项目描述','职责与行动','成果与影响'):
        assert field in text


def test_inline_field_subtitles_are_retained_inside_single_content_column():
    source = hr.build_body(resume())
    assert '<span class="ability-tag">策略方法</span>：' in source
    assert '<span class="ability-tag">协作交付</span>：' in source
    assert source.count('class="field-content"') == 8
    for field in ('summary', 'description', 'impact', 'honor'):
        r = resume()
        r['sections'][0]['entries'][0][field] = '能力标签：具体内容；另一个标签:结果 32%'
        source = hr.build_body(r)
        assert '<span class="ability-tag">能力标签</span>：具体内容' in source
        assert '<span class="ability-tag">另一个标签</span>:结果 32%' in source
        assert 'class="metric"' not in source


def test_skill_groups_use_locked_two_column_layout_and_preserve_heading():
    r = resume()
    r['sections'][2]['title'] = '专业能力'
    source = hr.build_body(r)
    assert 'data-section="skills"' in source
    assert '<div class="skills-grid">' in source
    for group in r['sections'][2]['groups']:
        assert '<div class="skill-label">%s</div>' % group['label'] in source
        assert '<div class="skill-content">%s</div>' % '、'.join(group['items']) in source
    assert '>专业能力' in source


def test_invalid_workspace_does_not_overwrite_any_saved_files(tmp_path):
    out = tmp_path / '基础简历.html'
    saved = [out, tmp_path / '基础简历.md', tmp_path / '简历版式档案.md']
    for path in saved:
        path.write_text('previous approved version')
    r = resume()
    r['basic'].pop('年龄')
    with pytest.raises(ValueError):
        hr.save_workspace(r, {'theme': 'bank'}, out)
    assert all(path.read_text() == 'previous approved version' for path in saved)


def test_structured_long_subtitle_in_work_and_project_bullets(tmp_path):
    r = resume()
    tag = '跨业务线客户经营体系与数据口径统一过程中多部门协同推进的复杂项目管理能力'
    for section in r['sections'][:2]:
        section['entries'][0]['bullets'][0] = {'tag': tag, 'text': '完成 20% 改进。'}
    source = hr.build_body(r)
    assert source.count('<span class="bullet-tag">%s</span>' % tag) == 2
    assert hr._resume_to_markdown(r).count(tag + '：完成 20% 改进。') == 2
    src = tmp_path / 'resume.json'
    src.write_text(json.dumps(r, ensure_ascii=False))
    result = subprocess.run([sys.executable, str(ROOT/'scripts/resume_structure_check.py'), '--resume', str(src)], capture_output=True, text=True)
    assert 'Traceback' not in result.stderr
    assert tag in source
