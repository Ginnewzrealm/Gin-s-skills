"""质量检查脚本。

执行 references/quality-checklist.md 中的客观检查项。
目前覆盖 L1（硬性规则）、L2（风格一致性）、L3（内容质量）中可自动化检查的部分，
以及 L4（活人感）的主观检查框架。
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# 常量：禁用词、禁用标点、套话、口语化词组、感官词、文化参照词、反常识词等
# ---------------------------------------------------------------------------

DISABLED_WORDS = [
    "说白了",
    "意味着什么",
    "这意味着",
    "本质上",
    "换句话说",
    "不可否认",
    "综上所述",
    "总的来说",
    "首先",
    "其次",
    "最后",
    "值得注意的是",
    "不难发现",
    "让我们来看看",
    "接下来让我们",
    "在当今",
    "随着",
    "的发展",
]

DISABLED_SYMBOLS = ["：", "——", '"', '"', "‘", "’", "“", "”"]

CHEAP_WORDS = ["震惊", "必看", "惊呆了", "99%", "重磅", "重磅消息", "绝密"]

TEXTBOOK_STARTS = [
    "在当今",
    "随着",
    "近年来",
    "现如今",
    "众所周知",
    "不可否认的是",
    "随着社会的发展",
]

ABSOLUTE_WORDS = ["一定", "全部", "绝对", "彻底", "必然", "永远", "完全"]

SENSORY_WORDS = [
    "看到", "听见", "闻到", "尝到", "摸到", "眼前", "耳边", "手里",
    "脚底", "空气", "味道", "声音", "光线", "阴影", "温度", "触感",
]

CULTURE_WORDS = [
    "历史", "哲学", "文化", "时代", "社会", "人性", "文明", "传统",
    "现代性", "异化", "资本", "技术伦理", "存在主义",
]

EMPATHY_WORDS = ["理解", "承认", "我也", "我懂", "换成我", "设身处地"]

COGNITIVE_UPDATE_WORDS = ["以前", "之前", "曾经以为", "后来", "现在觉得", "推翻"]

IMPERFECTION_WORDS = ["失败", "踩坑", "折腾", "卡壳", "犹豫", "纠结", "试错", "没搞懂"]

OPEN_ENDING_WORDS = ["你怎么看", "你觉得呢", "可以试试看", "也许", "不妨"]

TRIGGER_KEYWORDS = {
    "找共鸣": ["你", "我", "我们", "也是", "一样"],
    "当嘴替": ["其实", "从来", "根本", "不就是", "凭什么"],
    "纠错欲": ["不是", "错了", "误区", "真相", "假的"],
    "辨真伪": ["真的", "假的", "真相", "辟谣", "查证"],
    "看结果": ["结果", "最后", "终于", "变成", "涨到", "跌到"],
    "当军师": ["怎么办", "怎么选", "建议", "方法", "攻略"],
    "看翻车": ["挑战", "失败", "翻车", "踩坑", "惨痛"],
}

CASUAL_PHRASES = [
    "坦率的讲", "说真的", "我是真的觉得", "反正我觉得", "怎么说呢", "其实吧",
    "你想想看", "我跟你说", "这块需要注意一下", "顺着上面的再聊聊", "我有时候觉得",
    "我一直觉得", "这话听着有点刺耳但", "不是说", "不行而是说", "我自己的感受是",
    "我始终坚信", "我觉得还是挺重要的", "说实话我也不确定", "我自己也还在摸索",
    "可能有些想法还不成熟", "这个事儿我也踩过坑", "愚钝如我", "说实话我们还差得远",
    "这种感觉太爽了", "我当时就愣住了", "想想就觉得兴奋", "我真的被震撼到了",
    "搞得我现在还有点懵", "太离谱了", "给我一下子整不会了", "一时间无语凝噎",
    "鬼使神差的", "你敢信", "很多朋友可能不知道", "可能有小伙伴纳闷",
    "你如果关注这个领域的话", "大家也都知道", "这玩意", "不是哥们", "我寻思了一下",
    "有个屁的", "真的就是一声叹息", "太牛逼了", "比较骚的事",
]

VAGUE_TOOL_NAMES = ["AI 工具", "某个模型", "相关技术", "AI 产品", "某工具"]


# ---------------------------------------------------------------------------
# 标题检查（原有接口，保持兼容）
# ---------------------------------------------------------------------------


def check_title_length(title: str, min_len: int = 8, max_len: int = 30) -> bool:
    """检查标题长度是否在指定范围内。"""
    return min_len <= len(title) <= max_len


def check_disabled_symbols(text: str) -> list:
    """检测禁用标点符号。"""
    return [s for s in DISABLED_SYMBOLS if s in text]


def score_title(title: str, supports: list, trigger: str) -> dict:
    """对标题进行客观评分。"""
    score = 0
    issues = []

    # 字数 8-30
    if check_title_length(title):
        score += 2
    else:
        issues.append("标题长度不在 8-30 字之间")

    # 含具体数字或对比
    if re.search(r"\d+", title):
        score += 2
    else:
        issues.append("缺少具体数字或对比")

    # 含身份标签或痛点词（简化：检查 supports 中是否有词出现）
    if any(word in title for word in supports):
        score += 2
    else:
        issues.append("缺少身份标签或痛点词")

    # 不含廉价词
    if not any(word in title for word in CHEAP_WORDS):
        score += 2
    else:
        issues.append("包含廉价词")

    # 能从正文找到支撑（由调用方提供 supports 验证）
    if supports:
        score += 2
    else:
        issues.append("缺少正文支撑信息")

    # 与情绪触发点一致
    keywords = TRIGGER_KEYWORDS.get(trigger, [])
    if any(kw in title for kw in keywords):
        score += 2
    else:
        issues.append(f"标题未体现情绪触发点 '{trigger}'")

    return {"score": score, "issues": issues}


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------


def _count_occurrences(text: str, patterns: list) -> int:
    """统计文本中命中任一模式的次数（不重复计数同一位置，取首个匹配）。"""
    total = 0
    for pat in patterns:
        total += len(re.findall(re.escape(pat), text))
    return total


def _has_any(text: str, patterns: list) -> bool:
    return any(p in text for p in patterns)


def _split_paragraphs(text: str) -> list:
    """按空行分段。"""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_sentences(text: str) -> list:
    """简单按中文句号/问号/感叹号分句。"""
    return [s.strip() for s in re.split(r"[。！？]+", text) if s.strip()]


# ---------------------------------------------------------------------------
# L1 硬性规则检查
# ---------------------------------------------------------------------------


def check_l1(title: str, text: str, frontmatter: dict[str, Any] | None = None) -> dict:
    """L1 硬性规则检查。返回通过项、不通过项、命中明细。"""
    issues = []
    details = {}

    # L1-1 标题字数
    if not check_title_length(title):
        issues.append("L1-1 标题字数不在 8-30 字之间")
    details["title_length"] = len(title)

    # L1-2 禁用符号
    symbols = check_disabled_symbols(title + text)
    if symbols:
        issues.append(f"L1-2 发现禁用符号：{set(symbols)}")
    details["disabled_symbols"] = list(set(symbols))

    # L1-3 禁用词
    found_words = [w for w in DISABLED_WORDS if w in title + text]
    if found_words:
        issues.append(f"L1-3 发现禁用词：{set(found_words)}")
    details["disabled_words"] = list(set(found_words))

    # L1-4 结构性套话
    textbook = [s for s in TEXTBOOK_STARTS if text.startswith(s) or title.startswith(s)]
    bullet_list = len(re.findall(r"^\s*[-*]\s+", text, re.M)) > 3
    heavy_bold = len(re.findall(r"\*\*.+?\*\*", text)) > 5
    if textbook:
        issues.append(f"L1-4 发现教科书式开头：{textbook}")
    if bullet_list:
        issues.append("L1-4 连续 bullet point 罗列观点超过 3 处")
    if heavy_bold:
        issues.append("L1-4 大段加粗过多（>5 处）")

    # L1-5 frontmatter 完整
    required_fm = {"title", "article_type", "emotion_tone", "word_count"}
    fm = frontmatter or {}
    missing_fm = required_fm - set(fm.keys())
    if missing_fm:
        issues.append(f"L1-5 frontmatter 缺失字段：{missing_fm}")
    details["missing_frontmatter"] = list(missing_fm)

    # L1-6 字数达标（目标字数 ±15%）
    target = fm.get("word_count") or fm.get("target_word_count")
    word_count = len(text.replace(" ", "").replace("\n", ""))
    details["word_count"] = word_count
    if target:
        low, high = int(target * 0.85), int(target * 1.15)
        if not (low <= word_count <= high):
            issues.append(f"L1-6 正文字数 {word_count} 不在目标 {target} 的 ±15% 区间 [{low}, {high}]")

    # L1-7 段落长度
    paragraphs = _split_paragraphs(text)
    long_paragraphs = [i for i, p in enumerate(paragraphs, 1) if len(p) > 300]
    if long_paragraphs:
        issues.append(f"L1-7 以下段落超过 300 字：{long_paragraphs}")
    details["long_paragraphs"] = long_paragraphs

    # L1-8 空泛工具名
    vague = [v for v in VAGUE_TOOL_NAMES if v in text]
    if vague:
        issues.append(f"L1-8 使用空泛工具名：{set(vague)}")
    details["vague_tool_names"] = list(set(vague))

    # L1-9 标题情绪触发点
    emotion_tone = fm.get("emotion_tone") or ""
    keywords = TRIGGER_KEYWORDS.get(emotion_tone, [])
    if keywords and not any(kw in title for kw in keywords):
        issues.append(f"L1-9 标题未体现情绪触发点 '{emotion_tone}'")

    # L1-10 章节编号禁令
    if re.search(r"第[一二三四五12345]+[章节]|[第一二三四五12345][，、.]", text):
        issues.append("L1-10 发现章节编号（第一章/第一 等）")

    hard_fail = bool(issues)
    return {
        "passed": not hard_fail,
        "score": 100 if not hard_fail else max(0, 100 - len(issues) * 10),
        "issues": issues,
        "details": details,
    }


# ---------------------------------------------------------------------------
# L2 风格一致性检查
# ---------------------------------------------------------------------------


def check_l2(text: str) -> dict:
    """L2 风格一致性检查。"""
    issues = []
    details = {}

    sentences = _split_sentences(text)
    paragraphs = _split_paragraphs(text)

    # L2-1 开头
    if _has_any(text[:60], TEXTBOOK_STARTS):
        issues.append("L2-1 开头使用了教科书式套话")
    if not re.search(r"[我你他这那昨今明]|\d", text[:30]):
        issues.append("L2-1 开头不够具体，缺少场景/人物/时间/数字")

    # L2-2 节奏与结构
    sentence_lengths = [len(s) for s in sentences if s]
    alternating = any(
        sentence_lengths[i] > 40 and sentence_lengths[i + 1] < 20
        for i in range(len(sentence_lengths) - 1)
    )
    if not alternating:
        issues.append("L2-2 长短句交替不明显")

    one_liner = [p for p in paragraphs if len(p) < 15]
    details["one_liners"] = len(one_liner)
    if len(one_liner) < 3:
        issues.append("L2-2 一句话独立成段的断裂效果不足（<3 处）")

    if "?" not in text and "？" not in text:
        issues.append("L2-2 缺少疑问句节奏")

    # L2-3 口语化
    casual_hits = [p for p in CASUAL_PHRASES if p in text]
    details["casual_phrases"] = len(casual_hits)
    if len(casual_hits) < 5:
        issues.append(f"L2-3 口语化词组使用不足（仅 {len(casual_hits)} 处）")

    self_mockery = _has_any(text, ["我也不确定", "我也还在摸索", "踩过坑", "愚钝"])
    if not self_mockery:
        issues.append("L2-3 缺少自嘲或承认不足")

    emotion_punct = _has_any(text, ["。。。", "？？？", "= =", "！！", ".."])
    if not emotion_punct:
        issues.append("L2-3 缺少情绪标点（。。。？？？= =）")

    # L2-4 标点禁令二次确认
    symbols = check_disabled_symbols(text)
    if symbols:
        issues.append(f"L2-4 仍存在禁用符号：{set(symbols)}")

    # L2-5 五感画面写实
    sensory_hits = _count_occurrences(text, SENSORY_WORDS)
    details["sensory_words"] = sensory_hits
    if sensory_hits < 3:
        issues.append(f"L2-5 感官细节不足（仅 {sensory_hits} 处）")

    # L2-6 认知灰度
    absolutes = [w for w in ABSOLUTE_WORDS if w in text]
    if absolutes:
        issues.append(f"L2-6 使用绝对化词汇：{set(absolutes)}")

    passed = len(issues) <= 2
    return {
        "passed": passed,
        "score": 100 if passed else max(0, 100 - len(issues) * 5),
        "issues": issues,
        "details": details,
    }


# ---------------------------------------------------------------------------
# L3 内容质量检查
# ---------------------------------------------------------------------------


def check_l3(text: str, template: str = "", target_word_count: int = 0) -> dict:
    """L3 内容质量检查（可自动化部分）。"""
    issues = []
    details = {}

    # L3-1 观点支撑：检查是否有具体数字
    numbers = re.findall(r"\d+(?:\.\d+)?%?", text)
    details["number_count"] = len(numbers)
    if len(numbers) < 2:
        issues.append("L3-1 缺少具体数字/数据支撑观点")

    # L3-3 文化升维
    culture_hits = _count_occurrences(text, CULTURE_WORDS)
    details["culture_words"] = culture_hits
    if culture_hits < 1:
        issues.append("L3-3 未自然连接到更大的文化/哲学/历史参照物")

    # L3-4 对立面与同理心
    empathy_hits = _count_occurrences(text, EMPATHY_WORDS)
    details["empathy_words"] = empathy_hits
    if empathy_hits < 1:
        issues.append("L3-4 缺少对对方立场的理解或承认")

    # L3-5 文章类型专项检查（简化）
    if template == "methodology":
        if not re.search(r"(?:你可以|试试|第一步|第二步|第三步|操作|执行)", text):
            issues.append("L3-5 方法论分享型缺少可执行行动建议")
    elif template == "tool-sharing":
        if not re.search(r"(?:打开|输入|复制|粘贴|设置|选择|点击)", text):
            issues.append("L3-5 工具分享型缺少操作演示")
    elif template == "investigation":
        if not re.search(r"(?:我试|我测|我查|我去|我跑|我花了)", text):
            issues.append("L3-5 调查实验型缺少亲自下场叙事")

    # L3-7 钩子强度
    hook_text = text[:100]
    hook_signals = re.findall(r"\d+|反转|没想到|竟然|结果|翻车|真相|错了|挑战", hook_text)
    details["hook_signals"] = len(hook_signals)
    if len(hook_signals) < 1:
        issues.append("L3-7 开头 100 字内缺少痛点/数字/反常识/故事/身份标签")

    # L3-8 证据密度
    total_chars = len(text)
    expected_evidence = max(1, total_chars // 800)
    details["expected_evidence"] = expected_evidence
    details["actual_numbers"] = len(numbers)
    if len(numbers) < expected_evidence:
        issues.append(f"L3-8 证据密度不足（约每 800 字需 1 个案例/数据/观察）")

    # L3-10 身份共鸣
    if "你" not in text[:500]:
        issues.append("L3-10 前 500 字未明确称呼或代入目标读者")

    # L3-12 核心情绪触发点
    if not any(k in text for k in TRIGGER_KEYWORDS.keys()):
        # 放宽：检查是否有情绪关键词本身出现
        pass

    # L3-14 结尾开放性
    ending = text[-80:]
    if not _has_any(ending, OPEN_ENDING_WORDS) and not re.search(r"[?？]", ending):
        issues.append("L3-14 结尾缺少开放性/提问/行动号召")

    # L3-15 认知迭代坦诚感
    if not _has_any(text, COGNITIVE_UPDATE_WORDS):
        issues.append("L3-15 缺少认知迭代/坦诚感表达")

    # L3-16 细节瑕疵留存感
    if not _has_any(text, IMPERFECTION_WORDS):
        issues.append("L3-16 缺少真实卡顿/失败/试错痕迹")

    # L3-17 表达效率（粗略：段落平均字数不过高）
    paragraphs = _split_paragraphs(text)
    avg_para_len = sum(len(p) for p in paragraphs) / max(1, len(paragraphs))
    details["avg_paragraph_length"] = round(avg_para_len, 1)
    if avg_para_len > 250:
        issues.append("L3-17 段落平均过长，可能存在表达效率问题")

    # L3-18 认知落差（检查反常识/冲突词）
    gap_words = ["其实", "不是", "错了", "没想到", "反而", "真相", "颠覆"]
    gap_hits = _count_occurrences(text, gap_words)
    details["cognitive_gap_signals"] = gap_hits
    if gap_hits < 2:
        issues.append("L3-18 认知落差信号不足，缺少读者不知道的视角")

    passed = len(issues) <= 3
    return {
        "passed": passed,
        "score": 100 if passed else max(0, 100 - len(issues) * 5),
        "issues": issues,
        "details": details,
    }


# ---------------------------------------------------------------------------
# L4 活人感终审（主观框架）
# ---------------------------------------------------------------------------


def check_l4(text: str) -> dict:
    """L4 活人感终审。

    自动化脚本只能给出检查框架和部分信号统计，最终判断交给 LLM/人。
    """
    issues = []
    details = {}

    # 体感记忆 vs 知识性描述
    body_memory = _count_occurrences(text, ["愣住", "鼻子一酸", "手抖", "心跳", "脑子一片空白", "后背发凉"])
    knowledge_desc = _count_occurrences(text, ["感到非常", "感到十分", "我意识到", "我认识到"])
    details["body_memory_signals"] = body_memory
    details["knowledge_description_signals"] = knowledge_desc
    if body_memory < 1 and knowledge_desc >= 3:
        issues.append("L4-1 情绪表达偏知识性描述，缺少体感记忆")

    # 独特性：第一人称具体动作
    personal_action = len(re.findall(r"我[去看来做试跑查花找买吃用玩]", text))
    details["personal_actions"] = personal_action
    if personal_action < 3:
        issues.append("L4-2 个人独特动作/经历信号偏弱")

    # 姿态检查：导师腔
    mentor_tone = _count_occurrences(text, ["你要记住", "你必须", "你应该", "我告诉你", "听我的"])
    details["mentor_tone_signals"] = mentor_tone
    if mentor_tone >= 2:
        issues.append("L4-3 可能出现导师教学生姿态")

    # 心流：断裂符号/长段落预警
    paragraphs = _split_paragraphs(text)
    long_paras = sum(1 for p in paragraphs if len(p) > 250)
    details["long_paragraphs_for_flow"] = long_paras
    if long_paras >= 3:
        issues.append("L4-4 长段落较多，可能存在心流断点")

    # L4 不进入客观计分，仅作为整体参考
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "details": details,
        "note": "L4 为活人感终审，建议由人或 LLM 通读全文后做最终判断。",
    }


# ---------------------------------------------------------------------------
# 完整文章评分入口
# ---------------------------------------------------------------------------


def score_article(
    title: str,
    text: str,
    frontmatter: dict[str, Any] | None = None,
    template: str = "",
    supports: list | None = None,
    trigger: str = "",
) -> dict:
    """对文章执行 L1-L4 四层自检，返回完整报告。"""
    fm = frontmatter or {}
    emotion_tone = trigger or fm.get("emotion_tone", "")
    title_score = score_title(title, supports or [], emotion_tone)
    l1 = check_l1(title, text, fm)
    l2 = check_l2(text)
    l3 = check_l3(text, template, fm.get("word_count", 0))
    l4 = check_l4(text)

    # 客观总分（不含 L4）
    objective_score = round(
        title_score["score"] * 0.15
        + l1["score"] * 0.30
        + l2["score"] * 0.25
        + l3["score"] * 0.30
    )

    # 任一 hard-fail（L1 不通过）则整体不通过
    passed = l1["passed"] and l2["passed"] and l3["passed"]

    return {
        "title_score": title_score,
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "l4": l4,
        "objective_score": objective_score,
        "passed": passed,
        "verdict": "通过" if passed else "不通过，需返工",
    }


if __name__ == "__main__":
    import json

    demo_title = "转化率从 3% 涨到 12%，结果我只改了一个按钮"
    demo_text = (
        "事情是这样的。"
        "上周我帮一个朋友看落地页，他跟我说流量没少花，转化就是上不去。"
        "我当时也没多想，随手把按钮文案从『立即提交』改成了『先算一算我能省多少』。"
        "结果三天后他发来截图，转化率从 3% 涨到 12%。"
        "我整个人都懵了。"
        "就这么一句话，差别真的有这么大？"
        "后来我翻了十几个案例，发现大多数人对按钮的理解都错了。"
        "不是设计不够好看，而是读者没看到『与我有关』。"
        "你说奇不奇怪？"
    )
    report = score_article(
        title=demo_title,
        text=demo_text,
        frontmatter={
            "title": demo_title,
            "article_type": "methodology",
            "emotion_tone": "看结果",
            "word_count": 2500,
        },
        template="methodology",
        supports=["转化率", "按钮"],
        trigger="看结果",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
