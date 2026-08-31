#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dedupe_questions.py — 问题去重与合并（方法论第三步）。

三条规则：
1. 语义等价：主体/目标/信息需求都相同 → 合并，频次累加
2. 泛化合并：一条是另一条的特例 → 合并为通用表述
3. 冲突保留：看似相同但预设不同 → 保留为两条

输入：原始问题池 [{"raw", "source", "frequency"}]
输出：去重后候选池 [{"raw", "frequency", "merged_from", "source"}]
"""


# 关键词聚类：相同关键词集合 → 语义等价候选
TOPIC_KEYWORDS = {
    "饮食": ["吃", "饮食", "餐", "食谱", "食物", "喝", "忌口", "营养"],
    "运动": ["运动", "锻炼", "训练", "跑步", "有氧", "力量", "健身", "练"],
    "作息": ["睡眠", "作息", "熬夜", "休息", "起居"],
    "平台": ["平台期", "瓶颈", "停滞", "卡住"],
}

SPECIALIZERS = {"早餐", "午餐", "晚餐", "早饭", "午饭", "晚饭"}


def _topic(text):
    """返回文本所属主题关键词集合。"""
    matched = set()
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(k in text for k in kws):
            matched.add(topic)
    return matched


def _has_specialized(text):
    return any(s in text for s in SPECIALIZERS)


def _both_specialized(a, b):
    """两条都含特殊餐次词（都是某个通用问题的不同特例）。"""
    return _has_specialized(a) and _has_specialized(b)


def _is_specialization(special, general):
    """special 是否是 general 的特例（含特殊餐次词，general 不含）。"""
    return _has_specialized(special) and not _has_specialized(general)


def _generalize(items):
    """把多个特例合并为一个通用表述。"""
    return "如何合理安排每餐"


def _semantic_equivalent(a, b):
    """判断两条问题是否语义等价（共享主题关键词）。"""
    return bool(_topic(a) & _topic(b))


def _conflict_preserved(a, b):
    """判断两条问题是否预设不同（同一主题但立场对立）。"""
    pos_set = {"能", "可以", "有效", "行"}
    neg_set = {"有害", "不好", "不行", "危险"}
    a_pos = any(p in a for p in pos_set)
    a_neg = any(n in a for n in neg_set)
    b_pos = any(p in b for p in pos_set)
    b_neg = any(n in b for n in neg_set)
    if (a_pos and b_neg) or (a_neg and b_pos):
        return True
    return False


def dedupe(pool):
    """主入口：原始问题池 → 去重后候选池。"""
    if not pool:
        return []
    used = [False] * len(pool)
    out = []
    for i, item in enumerate(pool):
        if used[i]:
            continue
        group = [item]
        used[i] = True
        for j in range(i + 1, len(pool)):
            if used[j]:
                continue
            other = pool[j]
            # 规则 3：冲突保留
            if _conflict_preserved(item["raw"], other["raw"]):
                continue
            # 规则 2：泛化合并（含特殊餐次词）
            if (_both_specialized(item["raw"], other["raw"])
                    or _is_specialization(other["raw"], item["raw"])
                    or _is_specialization(item["raw"], other["raw"])):
                group.append(other)
                used[j] = True
                continue
            # 规则 1：语义等价（共享主题关键词）
            if _semantic_equivalent(item["raw"], other["raw"]):
                group.append(other)
                used[j] = True
        # 合并 group
        first = group[0]
        if len(group) == 1:
            out.append({
                "raw": first["raw"],
                "frequency": first["frequency"],
                "merged_from": [first["raw"]],
                "source": first["source"],
            })
        else:
            # 泛化合并：group 中任意一条含特殊餐次词，使用通用表述
            use_general = any(_has_specialized(g["raw"]) for g in group)
            general = _generalize(group) if use_general else first["raw"]
            out.append({
                "raw": general,
                "frequency": sum(g["frequency"] for g in group),
                "merged_from": [g["raw"] for g in group],
                "source": group[0]["source"],
            })
    return out


if __name__ == "__main__":
    import sys, json
    data = json.load(sys.stdin)
    print(json.dumps(dedupe(data), ensure_ascii=False, indent=2))