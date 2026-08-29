#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_field_metadata.py — 基于字段元数据子表的类型与选项校验用户输入。

本脚本不替代 Agent 的语义理解，只负责在 Agent 从自然语言中提取字段和值之后，
按字段元数据子表的「类型」、「选项」、「填写说明」做硬校验与规范化。

输入 JSON：
{
  "field_metadata": {
    "入睡时间": {"type": "时间", "options": null, "description": "格式 HH:mm，24小时制"},
    "大解状态": {"type": "单选", "options": ["🟢正常1次", "⚠️异常无/少"], "description": "..."},
    "晨起体重": {"type": "数字", "options": null, "description": "单位 kg，保留2位小数"}
  },
  "raw_values": {
    "入睡时间": "01:00",
    "大解状态": "⚠️异常无/少",
    "晨起体重": "68.5"
  }
}

输出 JSON：
{
  "valid": {
    "入睡时间": "01:00",
    "大解状态": "⚠️异常无/少",
    "晨起体重": 68.5
  },
  "errors": {
    "某个字段": "TYPE_MISMATCH: 字段类型为「时间」，输入「晚上11点」无法解析为 HH:mm"
  }
}

支持的元数据类型：数字 / 文本 / 单选 / 多选 / 日期 / 时间 / 公式
"""
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


def _normalize_time(value: str) -> Optional[str]:
    """把时间字符串规范化为 HH:mm 或 HH:mm:ss。"""
    value = str(value).strip().replace("：", ":")
    # 支持 01:00、1:00、01:00:00
    if re.fullmatch(r"\d{1,2}:\d{2}", value):
        h, m = value.split(":")
        return f"{int(h):02d}:{int(m):02d}"
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", value):
        h, m, s = value.split(":")
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    return None


def _normalize_date(value: str) -> Optional[str]:
    """把日期字符串规范化为 YYYY-MM-DD。"""
    value = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    return None


def _parse_number(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """解析数字。支持字符串中的数字。"""
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, str):
        # 去掉前后空格和常见单位，只保留数字部分
        s = value.strip()
        # 先尝试整体解析
        try:
            return float(s), None
        except ValueError:
            pass
        # 提取第一个数字（含小数）
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        if m:
            try:
                return float(m.group()), None
            except ValueError:
                pass
    return None, f"NUMBER_FORMAT_ERROR: 无法将 '{value}' 解析为数字"


def _validate_single_select(value: Any, options: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """单选校验：值必须在选项列表中。"""
    if not options:
        return None, "CONFIG_ERROR: 单选字段缺少选项列表"
    v = str(value).strip()
    if v in options:
        return v, None
    # 若去掉 emoji、空格后匹配，也算通过（防 Agent 偶尔手误）
    def normalize(s: str) -> str:
        return re.sub(r"[^一-龥a-zA-Z0-9]", "", s)
    v_norm = normalize(v)
    for opt in options:
        if normalize(opt) == v_norm:
            return opt, None
    return None, f"INVALID_OPTION: '{value}' 不在可选值中。可选值为：{' / '.join(options)}"


def _validate_multi_select(value: Any, options: List[str]) -> Tuple[Optional[List[str]], Optional[str]]:
    """多选校验：每个元素必须在选项列表中。"""
    if not isinstance(value, list):
        # 尝试按常见分隔符拆分
        value = [x.strip() for x in re.split(r"[,，/、]", str(value)) if x.strip()]
    valid_items = []
    for item in value:
        v, err = _validate_single_select(item, options)
        if err:
            return None, err
        valid_items.append(v)
    return valid_items, None


def _validate_text(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """文本类型：直接转字符串。"""
    return str(value), None


def _validate_formula(value: Any) -> Tuple[Optional[Any], Optional[str]]:
    """公式类型：Agent 不应写入，直接跳过。"""
    return None, "FORMULA_FIELD_SKIP: 公式字段由 Sheets 自动计算，Agent 不写入"


def validate_field(field_name: str, value: Any, meta: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    """校验单个字段。返回 (规范化后的值, 错误信息)。"""
    field_type = (meta.get("type") or "").strip()
    options = meta.get("options") or []

    if field_type == "数字":
        return _parse_number(value)

    if field_type == "时间":
        normalized = _normalize_time(value)
        if normalized is None:
            return None, f"TYPE_MISMATCH: 字段「{field_name}」类型为「时间」，输入「{value}」无法解析为 HH:mm 或 HH:mm:ss"
        return normalized, None

    if field_type == "日期":
        normalized = _normalize_date(value)
        if normalized is None:
            return None, f"TYPE_MISMATCH: 字段「{field_name}」类型为「日期」，输入「{value}」无法解析为 YYYY-MM-DD"
        return normalized, None

    if field_type == "单选":
        return _validate_single_select(value, options)

    if field_type == "多选":
        return _validate_multi_select(value, options)

    if field_type == "文本":
        return _validate_text(value)

    if field_type == "公式":
        return _validate_formula(value)

    return None, f"UNKNOWN_TYPE: 字段「{field_name}」的元数据类型「{field_type}」未知"


def validate_all(field_metadata: Dict[str, Dict[str, Any]], raw_values: Dict[str, Any]) -> Dict[str, Any]:
    valid: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for field_name, value in raw_values.items():
        meta = field_metadata.get(field_name)
        if not meta:
            errors[field_name] = f"FIELD_METADATA_MISSING: 字段「{field_name}」在字段元数据子表中不存在"
            continue

        coerced, err = validate_field(field_name, value, meta)
        if err:
            errors[field_name] = err
        else:
            valid[field_name] = coerced

    return {"valid": valid, "errors": errors}


def main() -> None:
    request = json.load(sys.stdin)
    field_metadata = request.get("field_metadata", {})
    raw_values = request.get("raw_values", {})

    result = validate_all(field_metadata, raw_values)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
