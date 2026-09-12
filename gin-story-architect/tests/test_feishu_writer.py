"""feishu_writer.py 纯逻辑单元测试：链接解析、schema 校验、键提取、字段定义。

不含任何网络调用；示例数据沿用 references/example.json 的契约。
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import feishu_writer as fw  # noqa: E402

EXAMPLE_JSON = Path(__file__).resolve().parent.parent / "references" / "example.json"


# ---------------------------------------------------------------------------
# parse_base_url
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expect", [
    ("https://abc.feishu.cn/base/XyZ123AbC?table=tbl1", "XyZ123AbC"),
    ("https://feishu.cn/base/bascnAbCdEf123", "bascnAbCdEf123"),
    ("https://tenant.larksuite.com/base/BaseToken123", "BaseToken123"),
])
def test_parse_base_url_ok(url, expect):
    assert fw.parse_base_url(url) == expect


@pytest.mark.parametrize("url", [
    "https://abc.feishu.cn/sheets/shtcn123",   # 电子表格
    "https://abc.feishu.cn/docx/doxcn123",     # 文档
    "not-a-url",
])
def test_parse_base_url_rejects_non_base(url):
    with pytest.raises(fw.FeishuError):
        fw.parse_base_url(url)


# ---------------------------------------------------------------------------
# validate_and_normalize
# ---------------------------------------------------------------------------

def _valid_episode_row(**overrides):
    row = {
        "集号": 1, "任务编号": "A-1", "挂载主线": "A", "单元事件": "e",
        "数据产出": "p", "产出物编号": "P-01", "状态更新": "s",
        "人物代价": "c", "结尾钩子": "h", "主线浓度": "中",
    }
    row.update(overrides)
    return row


def test_normalize_valid_data():
    out = fw.validate_and_normalize({
        "剧集总表": [_valid_episode_row()],
        "主线与分支线总表": [{"编号": "A", "模块名": "情报线"}],
        "总纲面板": [{"项目": "一句话故事", "内容": "x"}],
    })
    assert out["剧集总表"][0]["集号"] == 1
    assert out["剧集总表"][0]["挂载主线"] == "A"


def test_unknown_table_rejected():
    with pytest.raises(fw.FeishuError, match="未知表名"):
        fw.validate_and_normalize({"不存在的表": []})


def test_unknown_field_rejected():
    with pytest.raises(fw.FeishuError, match="未知字段"):
        fw.validate_and_normalize({"总纲面板": [{"项目": "x", "乱写字段": "y"}]})


def test_missing_key_field_rejected():
    with pytest.raises(fw.FeishuError, match="缺少关键字段"):
        fw.validate_and_normalize({"剧集总表": [_valid_episode_row(任务编号="")]})


def test_duplicate_key_rejected():
    with pytest.raises(fw.FeishuError, match="重复"):
        fw.validate_and_normalize({"总纲面板": [
            {"项目": "同一项", "内容": "1"},
            {"项目": "同一项", "内容": "2"},
        ]})


def test_invalid_select_value_rejected():
    with pytest.raises(fw.FeishuError, match="不在选项"):
        fw.validate_and_normalize({"剧集总表": [_valid_episode_row(挂载主线="Z")]})


def test_number_field_coerces_string():
    out = fw.validate_and_normalize({"剧集总表": [_valid_episode_row(集号="3", 回收集数="5")]})
    assert out["剧集总表"][0]["集号"] == 3.0
    assert out["剧集总表"][0]["回收集数"] == 5.0


def test_number_field_bad_value_rejected():
    with pytest.raises(fw.FeishuError, match="应为数字"):
        fw.validate_and_normalize({"剧集总表": [_valid_episode_row(集号="第三集")]})


def test_none_fields_are_dropped_not_stringified():
    """JSON null 不应被 str() 成字符串 "None" 写入飞书。"""
    out = fw.validate_and_normalize({"剧集总表": [_valid_episode_row(回收方式=None)]})
    assert "回收方式" not in out["剧集总表"][0]


def test_optional_fields_empty_string_allowed():
    out = fw.validate_and_normalize(
        {"剧集总表": [_valid_episode_row(波及主线="", 助力还是麻烦="", 反派同步动作="")]}
    )
    row = out["剧集总表"][0]
    # 空串不报错即可；是否落 record 不影响写入语义
    assert row.get("波及主线", "") == ""


def test_example_json_conforms_to_contract():
    """references/example.json 必须始终通过校验（契约样本回归）。"""
    data = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    out = fw.validate_and_normalize(data)
    assert set(out) == set(fw.TABLE_SCHEMAS)


# ---------------------------------------------------------------------------
# extract_key（update 模式的记录定位）
# ---------------------------------------------------------------------------

def test_extract_key_flattens_richtext():
    fields = {"任务编号": [{"type": "text", "text": "A-1"}], "集号": 3}
    assert fw.extract_key(fields, ["任务编号"]) == ("A-1",)


def test_extract_key_plain_value():
    assert fw.extract_key({"项目": "一句话故事"}, ["项目"]) == ("一句话故事",)


# ---------------------------------------------------------------------------
# build_field_defs
# ---------------------------------------------------------------------------

def test_build_field_defs_types_and_options():
    defs = fw.build_field_defs(fw.TABLE_SCHEMAS["剧集总表"])
    by_name = {d["field_name"]: d for d in defs}
    assert by_name["集号"]["type"] == 2                       # number
    assert by_name["任务编号"]["type"] == 1                   # text
    assert by_name["挂载主线"]["type"] == 3                   # select
    options = [o["name"] for o in by_name["挂载主线"]["property"]["options"]]
    assert options == ["A", "B", "C", "D", "E"]
    zh_options = [o["name"] for o in by_name["主线浓度"]["property"]["options"]]
    assert zh_options == ["低", "中", "高"]
