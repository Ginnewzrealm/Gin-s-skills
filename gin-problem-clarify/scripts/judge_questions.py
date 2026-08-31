#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""judge_questions.py — 问题判定四关卡（方法论第四步）。

四关串行执行，任一关不通过即终止：
1. 信息需求：去情绪词后仍有可回答的信息需求
2. 答案空间：能用研究/数据/共识回答，非价值观判断
3. 行动指向：回答后可推导行动建议
4. 频次门槛：≥2 跨来源 OR ≥5 单来源 → passed；
   单来源且仅 1 次 → rejected；其他 → degraded

输入：{"text", "frequency", "source_count"}
输出：{"gate1", "gate2", "gate3", "gate4", "status", "reasons"}
status: passed | degraded | rejected
"""
import re


EMOTION_WORDS = {"啊", "哎", "唉", "难", "烦", "愁", "苦", "累", "崩溃"}


def _gate1(text):
    """关卡 1：去掉情绪词后仍有信息需求，且不是纯宽泛问题。"""
    stripped = text
    for w in EMOTION_WORDS:
        stripped = stripped.replace(w, "")
    stripped = stripped.strip("，。？?！! ")
    # 宽泛问题：回答只需重复主题词本身（"X 是什么" 单独出现，无具体子概念）
    # 判定：去掉"是什么/为什么/怎么"等引导词后剩余 < 2 个有效实词
    guides = re.sub(r"是什么|为什么|怎么|如何|怎样|哪些|哪个|多少|几个|吗|呢", "", stripped).strip()
    content_words = re.findall(r"[一-鿿]+", guides)
    if len(content_words) <= 1 and len(content_words[0]) <= 4:
        # 实质内容只剩一个 ≤4 字词，视为宽泛
        return "rejected"
    # 含疑问助词或求答动词
    ask_markers = {"吗", "呢", "怎么", "为什么", "什么", "哪", "是否", "要不要", "该不该", "能", "可不可以", "是否"}
    if any(m in stripped for m in ask_markers):
        return "passed"
    if re.search(r"是|什么|多少|如何|怎样|哪些|几个|哪个", stripped):
        return "passed"
    return "rejected"


VALUE_JUDGMENT_PATTERNS = [
    r"有没有意义",
    r"值不值",
    r"该不该活",
    r"人生追求",
    r"该不该",
]
NON_FALSIFIABLE = ["最好的时代"]


def _gate2(text):
    """关卡 2：能用研究/数据/共识回答。"""
    for pat in VALUE_JUDGMENT_PATTERNS:
        if re.search(pat, text):
            return "rejected"
    for nf in NON_FALSIFIABLE:
        if nf in text:
            return "rejected"
    # 「哪个更好/适合」类比较型：可用研究回答
    return "passed"


PURE_THEORY_PATTERNS = [
    r"最早是谁提出",
    r"谁发明",
    r"历史",
    r"原理在物理学上",
]
OFF_TOPIC_PATTERNS = [
    r"人类为什么",
    r"宇宙",
]


def _gate3(text):
    """关卡 3：回答后可指导行动。"""
    for pat in PURE_THEORY_PATTERNS:
        if re.search(pat, text):
            return "rejected"
    for pat in OFF_TOPIC_PATTERNS:
        if re.search(pat, text):
            return "rejected"
    return "passed"


def _gate4(frequency, source_count):
    """关卡 4：频次门槛量化。"""
    if source_count >= 2 and frequency >= 2:
        return "passed"
    if source_count == 1 and frequency >= 5:
        return "passed"
    if source_count == 1 and frequency == 1:
        return "rejected"
    return "degraded"


def judge(question):
    """主入口：四关卡串行判定。"""
    text = question["text"]
    freq = question.get("frequency", 1)
    src_n = question.get("source_count", 1)
    gates = {
        "gate1": _gate1(text),
        "gate2": _gate2(text),
        "gate3": _gate3(text),
        "gate4": _gate4(freq, src_n),
    }
    # 任一关卡 rejected → 终止
    for k in ("gate1", "gate2", "gate3", "gate4"):
        if gates[k] == "rejected":
            status = "rejected"
            break
    else:
        # 全 passed → passed；任一 degraded → degraded
        if "degraded" in gates.values():
            status = "degraded"
        else:
            status = "passed"
    return {"gate1": gates["gate1"], "gate2": gates["gate2"],
            "gate3": gates["gate3"], "gate4": gates["gate4"],
            "status": status}


if __name__ == "__main__":
    import sys, json
    data = json.load(sys.stdin)
    print(json.dumps(judge(data), ensure_ascii=False, indent=2))