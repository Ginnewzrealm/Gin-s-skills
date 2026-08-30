#!/usr/bin/env python3
"""trigger_classifier.py — 健身追踪技能触发意图分类器。

输入 JSON：
{
  "message": "今早体重68.5，昨晚12点睡的",
  "context": {"cron": false}
}

输出 JSON：
{
  "triggered": true,
  "mode": "reply_entry",
  "reason": "字段指纹匹配：晨起体重、入睡时间",
  "excluded_by": null
}

mode 取值：
- daily_poll：每日轮询
- reply_entry：回复录入
- makeup：补数据
- query：查询数据
- init：初始化配置
- sync：讯记同步
- null：未触发

分类优先级：否定触发 > cron > init/sync > 字面触发 > 字段指纹 > 查询 > 补数据
"""
import json
import re
import sys
from typing import Dict, List, Optional, Tuple


# 字段名与同义词映射（同义词 → 标准字段名）
FIELD_SYNONYMS: Dict[str, str] = {
    # 身体
    "晨起体重": "晨起体重",
    "体重": "晨起体重",
    "体脂率": "体脂率",
    "体脂": "体脂率",
    "BMI": "BMI",
    "bmi": "BMI",
    "腰围": "腰围",
    "臀围": "臀围",
    "腰臀比": "腰臀比",
    "睡前体重": "睡前体重",
    "早晚体重差": "早晚体重差",
    # 排便
    "大解状态": "大解状态",
    "排便": "大解状态",
    # 睡眠
    "入睡时间": "入睡时间",
    "入睡": "入睡时间",
    "睡觉": "入睡时间",
    "睡了": "入睡时间",
    "睡的": "入睡时间",
    "几点睡": "入睡时间",
    "起床时间": "起床时间",
    "起床": "起床时间",
    "几点起": "起床时间",
    "睡眠时长": "睡眠时长",
    "睡了多久": "睡眠时长",
    "晨起心率（次/分）": "晨起心率（次/分）",
    "心率": "晨起心率（次/分）",
    "入睡难度": "入睡难度",
    "半夜醒来": "半夜醒来",
    "醒来": "半夜醒来",
    "早起状态": "早起状态",
    "午后能量低谷": "午后能量低谷",
    "能量低谷": "午后能量低谷",
    "傍晚情绪状态": "傍晚情绪状态",
    "情绪": "傍晚情绪状态",
    "睡前异常清醒": "睡前异常清醒",
    # 饮食
    "起床饥饿程度": "起床饥饿程度",
    "早餐时间": "早餐时间",
    "早餐饥饿时间": "早餐饥饿时间",
    "早餐饥饿程度": "早餐饥饿程度",
    "早餐饥饿速度": "早餐饥饿速度",
    "午餐时间": "午餐时间",
    "午餐后困倦": "午餐后困倦",
    "午餐饥饿时间": "午餐饥饿时间",
    "午餐饥饿程度": "午餐饥饿程度",
    "午餐饥饿速度": "午餐饥饿速度",
    "晚餐时间": "晚餐时间",
    "总热量": "总热量",
    "热量": "总热量",
    "卡路里": "总热量",
    "卡": "总热量",
    "蛋白": "蛋白",
    "蛋白质": "蛋白",
    "碳水": "碳水",
    "碳水化合物": "碳水",
    "脂肪": "脂肪",
    "碳水渴望": "碳水渴望",
    # 训练
    "训练欲望": "训练欲望",
    "训练状态": "训练状态",
    "力量": "力量",
    "有氧": "有氧",
    # 其他
    "其他备注": "其他备注",
    "备注": "其他备注",
}

# 否定触发词/短语（出现则直接不触发）
NEGATIVE_TRIGGERS: List[str] = [
    # 周报/分析/PDCA
    "PDCA", "pdca",
    "周报", "本周总结", "本周健身总结", "减脂周报", "本周减脂总结",
    "代谢分析", "减脂分析", "跑一下周报", "周报总结",
    "复盘", "分析", "总结今天的训练",
    # 计划/训练日记
    "训练计划", "健身计划", "安排训练", "今天练", "练胸", "练背", "练腿",
    "动作", "怎么练", "注意事项", "训练日记", "日记", "训练打卡", "打卡",
    # 建议/推荐
    "推荐", "建议", "补剂", "健身房", "医疗", "诊断", "伤病", "康复",
    # 纯聊天
    "健身是什么", "怎么健身", "健身好吗", "健身有什么用",
]

# 录入动词
ENTRY_VERBS: List[str] = ["记录", "记", "补录", "填报", "填了", "报", "录入", "写"]

# 查询动词/词
QUERY_WORDS: List[str] = ["看看", "查询", "查一下", "多少", "多少了", "填了什么", "吃了什么", "怎么样", "如何"]

# 日期词
DATE_WORDS: List[str] = [
    "昨天", "前天", "大前天", "今天", "今日", "昨晚",
    "上周一", "上周二", "上周三", "上周四", "上周五", "上周六", "上周日", "上周",
]

# 时段词
PERIOD_WORDS: List[str] = ["早上", "上午", "中午", "下午", "晚上", "睡前", "晨间", "午间", "晚间"]


def _normalize(text: str) -> str:
    return text.strip()


def _contains_any(text: str, words: List[str]) -> Tuple[bool, Optional[str]]:
    for w in words:
        if w in text:
            return True, w
    return False, None


def _has_value_indicator(text: str) -> bool:
    """是否包含数值、时间、emoji 选项或录入动词等数据信号。"""
    if re.search(r"\d", text):
        return True
    if re.search(r"\d{1,2}:\d{2}", text):
        return True
    if _contains_any(text, ENTRY_VERBS)[0]:
        return True
    # 单选选项常见 emoji
    if re.search(r"[🟢⚠️🔴🐻🏋️‍♂️💪🦵]", text):
        return True
    return False


def _has_query_indicator(text: str) -> bool:
    return _contains_any(text, QUERY_WORDS)[0] or "?" in text or "？" in text


def _detect_date(text: str) -> bool:
    has_date_word, _ = _contains_any(text, DATE_WORDS)
    if has_date_word:
        return True
    # 简单日期模式 YYYY-MM-DD 或 MM/DD
    if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        return True
    return False


def _detect_period(text: str) -> bool:
    return _contains_any(text, PERIOD_WORDS)[0]


def _match_field_fingerprints(text: str) -> List[str]:
    """返回匹配到的标准字段名列表（去重）。"""
    matched = []
    # 按长度降序匹配，避免短同义词覆盖长字段名
    for syn, field in sorted(FIELD_SYNONYMS.items(), key=lambda x: -len(x[0])):
        if syn in text and field not in matched:
            matched.append(field)
    return matched


def classify(message: str, cron: bool = False) -> Dict[str, Optional[str]]:
    text = _normalize(message)

    # 1. cron 触发
    if cron:
        return {"triggered": True, "mode": "daily_poll", "reason": "cron:daily_poll", "excluded_by": None}

    # 空消息不触发
    if not text:
        return {"triggered": False, "mode": None, "reason": "空消息", "excluded_by": None}

    # 2. 否定触发词优先
    negative, neg_word = _contains_any(text, NEGATIVE_TRIGGERS)
    if negative:
        return {"triggered": False, "mode": None, "reason": "命中否定触发词", "excluded_by": neg_word}

    # 3. 显式配置
    if "健身追踪配置" in text or "配置健身" in text or "初始化健身追踪" in text:
        return {"triggered": True, "mode": "init", "reason": "显式配置触发", "excluded_by": None}

    # 4. 显式同步
    if "同步讯记" in text:
        return {"triggered": True, "mode": "sync", "reason": "显式同步触发", "excluded_by": None}

    # 5. 字面触发：健身追踪
    if "健身追踪" in text:
        if _has_value_indicator(text) or _match_field_fingerprints(text):
            return {"triggered": True, "mode": "reply_entry", "reason": "字面触发 + 数据字段/值", "excluded_by": None}
        if _detect_date(text):
            return {"triggered": True, "mode": "makeup", "reason": "字面触发 + 日期", "excluded_by": None}
        return {"triggered": True, "mode": "daily_poll", "reason": "字面触发", "excluded_by": None}

    # 6. 字段指纹
    fields = _match_field_fingerprints(text)
    if fields:
        if not _has_query_indicator(text):
            return {"triggered": True, "mode": "reply_entry", "reason": f"字段指纹匹配：{', '.join(fields)}", "excluded_by": None}
        # 含字段名但带查询词 → 查询
        return {"triggered": True, "mode": "query", "reason": f"字段查询：{', '.join(fields)}", "excluded_by": None}

    # 7. 查询意图（无字段名但含查询词 + 健身/数据/饮食语境）
    if _has_query_indicator(text) and ("健身" in text or "数据" in text or "记录" in text or "吃了" in text or "喝了" in text):
        return {"triggered": True, "mode": "query", "reason": "查询意图", "excluded_by": None}

    # 8. 补数据
    if "补数据" in text or "补一下" in text:
        if _detect_date(text) or _match_field_fingerprints(text):
            return {"triggered": True, "mode": "makeup", "reason": "补数据意图", "excluded_by": None}
        return {"triggered": False, "mode": None, "reason": "补数据意图但缺少日期/字段", "excluded_by": None}

    # 9. 默认不触发
    return {"triggered": False, "mode": None, "reason": "未匹配任何触发信号", "excluded_by": None}


def main() -> None:
    request = json.load(sys.stdin)
    message = request.get("message", "")
    cron = request.get("context", {}).get("cron", False)
    result = classify(message, cron)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
