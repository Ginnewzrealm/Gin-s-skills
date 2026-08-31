#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""question_extractor.py — 从抓取的网页内容或搜索结果标题中提取真实问题。

要求：问题必须来自真实网页 title 或正文引用，不推断、不改写。
"""

import re
from html import unescape

from common import is_question_like, normalize_text


# 需要剔除的明显非问题模式（footer / 免责声明 / JS 代码 / 模板片段）
NON_QUESTION_PATTERNS = [
    r"本站有权",                          # 免责
    r"用户协议",
    r"隐私政策",
    r"免责声明",
    r"cookie",
    r"^[\s\W\d_]+$",                       # 纯符号
    r"^\s*$",
    r"window\.document",
    r"webdig\.js",
    r"\.js[\s？?]*$",
    r"^//",
    r"^[\(\)\{\};,\.\s]+",
    r"ICP备",                              # ICP 备案
    r"[一-龥]ICP备",              # 中文 ICP
    r"营业执照",
    r"友情链接",
    r"广告合作",
    r"联系我们",
    r"下载.*app",
    r"扫码下载",
    r"关注我们",
    r"订阅.*公众号",
    r"客服电话",
    r"工作时间",
    r"周一至周五",
    r"http[s]?://",                        # 链接
    r"www\.",
    r"\.com",
    r"\.cn",
    r"\.html",
    r"@",
]

# 段落长度上限（超过视为正文片段而非问题）
MAX_QUESTION_LEN = 60

# 最小长度
MIN_QUESTION_LEN = 6


def strip_html(html):
    """简单去除 HTML 标签。"""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text)


def is_obviously_not_question(text):
    """判断一段文本是否明显不是用户问题。"""
    t = text.strip()
    if len(t) < MIN_QUESTION_LEN:
        return True
    if len(t) > MAX_QUESTION_LEN:
        return True
    for pat in NON_QUESTION_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


# 核心减脂动作词——必须至少出现一个才算「减脂主题」
CORE_TERMS = [
    "减脂", "减肥", "减重", "瘦身", "瘦", "燃脂", "刷脂", "塑形", "塑身",
    "节食", "代餐", "轻食", "低脂",
]

# 辅助相关词——单独不够，但配合核心词可提高相关度
AUX_TERMS = [
    "体脂", "体脂率", "热量", "卡路里", "大卡", "千卡", "千焦",
    "生酮", "低碳", "辟谷", "暴食", "厌食", "食欲", "饱腹",
    "BMI", "腰围", "围度", "肌肉", "增肌",
    "经期", "姨妈", "月经", "例假", "生理期",
    "平台期", "瓶颈", "反弹", "复胖",
    "健身房", "跑步", "HIIT", "心率",
    "骗局", "智商税", "伪科学", "偏方",
    "上班族", "久坐",
    "夜宵", "奶茶", "火锅",
    "蛋白质", "蛋白",
]


def is_relevant(text):
    """判断问题是否以「减脂」为主题。

    要求：至少出现一个核心动作词。
    """
    if any(w in text for w in CORE_TERMS):
        return True
    return False


def clean_tail(text):
    """清理问题末尾的站点名 / 展开 / 分隔符尾巴。"""
    text = re.sub(r"\s*[\-–—|]\s*(民福康|百度|百度健康|薄荷|家庭医生在线|知乎|简书|新浪|网易|腾讯|凤凰|搜狐|健康之路|三九养生堂|99健康|39健康|寻医问药|杏林普康|好大夫|丁香医生|百度百科|百度文库)\s*$", "", text)
    text = re.sub(r"\s*展开\s*$", "", text)
    text = re.sub(r"\s*收起\s*$", "", text)
    text = re.sub(r"\s*[\.]{3,}\s*$", "", text)
    text = re.sub(r"\s*[\-–—\|]+\s*$", "", text)
    text = text.strip()
    return text


def clean_head(text):
    """清理问题开头的引述/反问/前缀。"""
    # 去掉前后成对引号
    text = text.strip()
    # 成对引号（含英文/中文/日文）
    pairs = [('"', '"'), ('"', '"'), ('「', '」'), ('『', '』'), ('《', '》'), ('(', ')'), ('（', '）')]
    for l, r in pairs:
        if text.startswith(l) and text.endswith(r):
            text = text[1:-1].strip()
            break
    # 去掉单边残留引号
    text = re.sub(r'^[「『《"\'\(]+', '', text)
    text = re.sub(r'[」』》"\'\)]+$', '', text)
    # 去掉常见反问/引述前缀
    text = re.sub(
        r"^(可是|但是|然而|不过|那么|反之|若是|如果|因为|由于|虽然|尽管|其实|实际上|不夸张地说|有人会说|有人说|商家说|我们说|据说|据悉)",
        "", text)
    # 去掉括号式作者/出处前缀：例如 "【光明图片】xxx"
    text = re.sub(r"^【[^】]*】", "", text)
    # 去掉"作者：xxx" "来源：xxx"
    text = re.sub(r"^(作者|来源|编辑|记者)[：:][^。]+[。,]?\s*", "", text)
    # 去掉本站/标签前缀
    text = re.sub(r"^(此刻新闻|热点新闻|首页|推荐|热门|专题)[：:、\s]*", "", text)
    # 去掉末尾残留的"?"、"？"前后多余空格
    text = text.strip()
    return text


def extract_from_title(title):
    """从页面标题中提取问题。"""
    if not title:
        return None
    title = title.strip()
    # 去掉常见的后缀，如 " - 知乎"
    title = re.sub(r"[\-–—]\s*(知乎|百度知道|Quora|Reddit|豆瓣|悟空问答|简书).*$", "", title).strip()
    title = title.strip()
    title = clean_tail(title)
    title = clean_head(title)
    if is_obviously_not_question(title):
        return None
    if is_question_like(title):
        normalized = normalize_text(title)
        if is_relevant(normalized):
            return normalized
    return None


def extract_from_content(html, source_url, max_candidates=50):
    """从 HTML 正文中提取候选问题。

    策略：
    - 从 h1/h2/h3 标题、加粗文本、独立段落中提取疑问句
    - 优先提取看起来像用户提问的句子
    - 剔除明显非问题模式（footer / 免责 / JS）
    """
    text = strip_html(html)
    candidates = []

    # 1. 提取 h1-h3 中的文本
    headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, flags=re.DOTALL)
    for h in headings:
        h = strip_html(h).strip()
        q = extract_from_title(h)
        if q and q not in candidates:
            candidates.append(q)

    # 2. 按句子切分，提取疑问句
    sentences = re.split(r"(?<=[。！？?\n])", text)
    for s in sentences:
        s = s.strip()
        if is_obviously_not_question(s):
            continue
        if is_question_like(s):
            q = normalize_text(s)
            q = clean_tail(q)
            q = clean_head(q)
            if not is_relevant(q):
                continue
            if q not in candidates:
                candidates.append(q)
        if len(candidates) >= max_candidates:
            break

    return [{"text": q, "source_url": source_url, "extracted_from": "content"} for q in candidates]


def extract_from_search_result(title, url):
    """当页面无法抓取时，使用搜索结果的页面标题作为问题来源。"""
    q = extract_from_title(title)
    if q:
        return {"text": q, "source_url": url, "extracted_from": "search_title"}
    return None


def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 question_extractor.py <html-file-or-title> [--title]")
        sys.exit(1)
    arg = sys.argv[1]
    is_title = "--title" in sys.argv
    if is_title:
        print(extract_from_title(arg))
    else:
        try:
            with open(arg, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception:
            html = arg
        results = extract_from_content(html, "https://example.com")
        for r in results[:10]:
            print(r["text"])


if __name__ == "__main__":
    main()
