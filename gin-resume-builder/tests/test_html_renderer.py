#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_html_renderer.py — HTML 渲染器测试。"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("html_renderer", _MODULE_DIR / "html_renderer.py")
hr = importlib.util.module_from_spec(_spec)
sys.modules["html_renderer"] = hr
_spec.loader.exec_module(hr)

render = hr.render


def _resume():
    return {
        "title": "李明-高级销售经理-简历",
        "basic": {
            "姓名": "李明",
            "电话": "13800000000",
            "邮箱": "liming@example.com",
            "城市": "杭州",
            "求职意向": "高级销售经理",
        },
        "sections": [
            {
                "title": "岗位胜任",
                "items": [{"tag": "大客户销售", "text": "5 年 B2B 销售经验，擅长复杂合同谈判。"}],
            },
            {
                "title": "工作经历",
                "entries": [
                    {
                        "org": "示例科技",
                        "role": "销售总监",
                        "period": "2020-2025",
                        "summary": "负责华东区大客户拓展与团队管理。",
                        "bullets": ["主导 560 万合同商务谈判并签约落地"],
                    }
                ],
            },
        ],
    }


def test_render_default_html():
    html = render(_resume())
    assert "李明" in html
    assert "示例科技" in html
    assert "13800000000" in html


def test_render_editable_html():
    html = render(_resume(), editable=True)
    assert "contenteditable" in html
    assert "生成 PDF" in html


from html.parser import HTMLParser
import pytest


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)


def visible_text(markup):
    parser = TextParser()
    parser.feed(markup)
    return ''.join(parser.text)


@pytest.mark.parametrize('bullet', ['业绩增长：提升20%', '业绩增长:提升20%', '“业绩增长”：提升20%'])
def test_bullet_separator_appears_once(bullet):
    text = visible_text(hr.rich_bullet(bullet))
    assert text.count('：') + text.count(':') == 1
    assert ('“' in text) == ('“' in bullet)


def test_explicit_tag_trailing_colon_is_not_duplicated():
    assert visible_text(hr.rich_item({'tag': '业绩增长：', 'text': '提升'})) == '业绩增长：提升'


@pytest.mark.parametrize('education', [
    ['测试大学｜计算机｜本科｜2018-2022'],
    [{'school': '测试大学', 'major': '计算机', 'degree': '本科', 'period': '2018-2022'}],
])
def test_top_level_education_is_rendered_without_losing_fields(education):
    text = visible_text(hr.build_body({'education': education}))
    for value in ['测试大学', '计算机', '本科', '2018-2022']:
        assert value in text


def test_basic_education_preserves_multiple_degrees_and_details():
    value = '测试大学 计算机 本科 2018-2022；示例大学 软件 硕士 2022-2025'
    assert value in visible_text(hr.build_body({'basic': {'教育背景': value}}))


def test_education_section_preserves_all_entries():
    resume = {'sections': [{'title': '教育背景', 'entries': [
        {'org': '测试大学', 'role': '计算机 本科', 'period': '2018-2022'},
        {'org': '示例大学', 'role': '软件 硕士', 'period': '2022-2025'},
    ]}]}
    text = visible_text(hr.build_body(resume))
    for value in ['测试大学', '计算机 本科', '2018-2022', '示例大学', '软件 硕士']:
        assert value in text


def test_contact_fields_are_editable():
    markup = hr._make_editable(hr.build_body({'basic': {'教育背景': '测试大学 本科'}}))
    class Parser(HTMLParser):
        editable = False
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if 'contact-item' in attrs.get('class', '').split():
                self.editable = attrs.get('contenteditable') == 'true'
    parser = Parser()
    parser.feed(markup)
    assert parser.editable


def test_workspace_markdown_retains_top_level_education():
    text = hr._resume_to_markdown({'education': [
        {'school': '测试大学', 'degree': '本科', 'major': '计算机', 'period': '2018-2022'}]})
    for value in ['测试大学', '本科', '计算机', '2018-2022']:
        assert value in text


def test_education_section_takes_precedence_without_mutating_input():
    resume = {'education': ['旧学校'], 'basic': {'教育背景': '旧摘要'},
              'sections': [{'title': '教育背景', 'items': ['已确认大学 本科']} ]}
    before = json.dumps(resume, ensure_ascii=False)
    text = visible_text(hr.build_body(resume))
    assert text.count('已确认大学') == 1
    assert '旧学校' not in text and '旧摘要' not in text
    assert json.dumps(resume, ensure_ascii=False) == before
