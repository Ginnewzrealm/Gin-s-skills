"""角度匹配器。

根据素材信号组合匹配切入角度和情绪触发点。
"""

MATCH_RULES = [
    ({"痛点", "数字"}, "A1", "A2", "找共鸣", "当嘴替"),
    ({"痛点", "故事"}, "A1", "A4", "找共鸣", "当军师"),
    ({"反常识", "数字"}, "A3", "A2", "纠错欲", "辨真伪"),
    ({"故事", "身份"}, "A4", "A5", "找共鸣", "当嘴替"),
    ({"身份", "教程"}, "A5", "A6", "找共鸣", "当军师"),
    ({"数字", "教程"}, "A2", "A6", "看结果", "当军师"),
    ({"痛点"}, "A1", None, "找共鸣", None),
    ({"故事"}, "A4", None, "找共鸣", None),
    ({"反常识"}, "A3", None, "纠错欲", None),
    ({"教程"}, "A6", None, "当军师", None),
]


def match_angles(signals: set) -> dict:
    """根据素材信号匹配角度和情绪触发点。"""
    for rule in MATCH_RULES:
        if signals >= rule[0]:
            return {
                "primary": rule[1],
                "secondary": rule[2],
                "emotion_primary": rule[3],
                "emotion_secondary": rule[4],
                "count": 2 if rule[2] else 1,
            }
    return {"primary": None, "secondary": None, "count": 0}
