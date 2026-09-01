#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_validate_action_docs.py — 动作文档 frontmatter 校验测试。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import validate_action_docs as validator

WORDLIST = {
    "胸部": {"胸大肌上缘", "胸大肌下缘", "胸部中缝", "胸部外缘", "胸部整体厚度"},
    "背部": {"上背", "背部宽度", "背部厚度", "下背（竖脊肌）"},
    "臀腿部": {
        "臀部整体（臀大肌）",
        "臀部上缘",
        "臀部下缘",
        "侧臀（臀中肌/臀小肌）",
        "股四头肌（大腿前侧）",
        "腘绳肌（大腿后侧）",
        "大腿内侧",
        "小腿",
    },
}


def test_valid_doc_passes():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 胸大肌上缘
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推

## 一、目标肌肉

### （一）主要目标肌肉
　　胸大肌上束
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert errors == []


def test_missing_target_area_in_strict_mode_fails():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert any("目标部位" in e for e in errors)


def test_missing_target_area_in_lenient_mode_warns():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=False)
    assert all("目标部位" not in e for e in errors)


def test_empty_target_area_list_is_allowed():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位: []
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 杠铃弯举
"""
    errors = validator.validate_doc(content, "杠铃弯举.md", WORDLIST, strict=True)
    assert errors == []


def test_invalid_target_area_value_fails():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 不存在部位
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert any("不存在部位" in e for e in errors)


def test_too_many_target_area_tags_fails():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 胸大肌上缘
  - 胸大肌下缘
  - 胸部中缝
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert any("1~2 个" in e for e in errors)


def test_invalid_enum_value_fails():
    content = """---
动作类型: 无效类型
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 胸大肌上缘
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert any("动作类型" in e for e in errors)


def test_h1_mismatch_fails():
    content = """---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 胸大肌上缘
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 错误标题
"""
    errors = validator.validate_doc(content, "上斜杠铃卧推.md", WORDLIST, strict=True)
    assert any("H1" in e or "标题" in e for e in errors)


def test_validate_single_file(tmp_path):
    doc = tmp_path / "上斜杠铃卧推.md"
    doc.write_text("""---
动作类型: 复合动作
器械状态: 激活
计重方式: 总重
训练阶段: 学习期
目标部位:
  - 胸大肌上缘
最后练习: 待记录
累计训练次数: 0
估算1RM: 待记录
---

# 上斜杠铃卧推
""", encoding="utf-8")

    rules = tmp_path / "rules.md"
    rules.write_text("""### 目标部位标签词表

| 部位 | 目标部位标签 |
|---|---|
| 胸部 | 胸大肌上缘、胸大肌下缘 |
""", encoding="utf-8")

    errors = validator.validate_single_file(str(doc), str(rules), strict=True)
    assert errors == 0


def test_load_wordlist_extracts_categories():
    rules_md = """### 目标部位标签词表（唯一真源）

| 部位 | 目标部位标签（受控词表） |
|---|---|
| 胸部 | 胸大肌上缘、胸大肌下缘 |
| 背部 | 上背、背部宽度 |
"""
    wordlist = validator.load_wordlist(rules_md)
    assert wordlist["胸部"] == {"胸大肌上缘", "胸大肌下缘"}
    assert wordlist["背部"] == {"上背", "背部宽度"}
