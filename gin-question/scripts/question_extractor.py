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
    r"您访问的链接即将离开",                # 政府网站跳转提示
    r"是否继续",
    r"门户网站",
    r"访问.*即将",
    r"继续访问",
    r"您即将",
    r"温馨提示",
    r"使用.*浏览器",
    r"建议使用",
    r"分辨率",
    r"主办单位",
    r"承办单位",
    r"网站地图",
    r"返回首页",
    r"首页\s*>\s*",
    r"^\^[\s\d\.]+\s",                     # 维基百科脚注引用 ^ 7.0 7.1
    r"^\s*\^[\s一-龥]",                     # ^ 后跟中文（维基脚注引用）
    r"^[\^＊\*]+\s*[一-龥]",                 # 脚注符号 + 中文
    r"\[编辑\]",                            # 维基百科编辑按钮
    r"\[来源请求\]",
    r"^\s*受[^\n]{0,50}[？?]\s*$",           # 句子片段：受...感召？
    r"^\s*直到[^\n]{0,50}[？?]\s*$",         # 句子片段：直到...
    r"^\s*当[^\n]{0,50}[？?]\s*$",           # 句子片段：当...
    r"^[【《「][^】》」\n]{0,20}[？?]\s*$",   # 配对符号内 < 20 字符
    r"^.{0,40}[〈《].{0,15}[？?]\s*$",        # 含书名号 + 短片段（"在MV〈你好嗎？"）
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

# 主题相关词集合（按主题分类）—— 主题不同时使用不同集合
TOPIC_TERMS = {
    "减脂": CORE_TERMS,
    "一棵树": [
        "树", "树木", "乔木", "灌木", "藤本", "古树", "名木", "行道树", "观赏树",
        "用材林", "防护林", "经济林", "林木", "树苗", "苗木", "树苗",
        "银杏", "松树", "柏树", "槐树", "柳树", "杨树", "梧桐", "榕树",
        "桂花", "梅花", "桃花", "樱花", "海棠", "玉兰", "紫薇",
        "石榴", "柿子", "枣树", "桔树", "黄杨", "罗汉松",
        "树根", "树干", "树皮", "树叶", "树枝", "树冠", "树龄",
        "种植", "栽培", "修剪", "移栽", "养护", "施肥", "浇水",
        "光合作用", "落叶", "常绿", "针叶", "阔叶", "木本",
        "风水", "寓意", "庭院", "绿化",
    ],
    "新能源汽车": [
        "新能源", "电动汽车", "电车", "纯电", "混动", "插混", "增程",
        "电池", "续航", "充电", "快充", "慢充", "换电",
        "比亚迪", "特斯拉", "蔚来", "小鹏", "理想", "小米",
        "SU7", "Model", "BYD", "汉", "秦", "宋", "海豹",
    ],
    "周杰伦": [
        "周杰伦", "周董", "周导", "杰伦", "Jay", "杰迷", "周式",
        "小公举", "卤蛋", "小周周", "奶茶伦", "叶湘伦",
        "杰威尔", "JVR", "亚洲流行天王",
        "中国风", "Jay式情歌", "华语乐坛",
        "哎哟不错", "瞎啦", "屁啦",
        "不能说的秘密", "天台爱情", "满城尽带黄金甲",
        "稻香", "青花瓷", "晴天", "七里香", "夜曲", "东风破", "菊花台", "霍元甲",
        "范特西", "叶惠美", "十一月的萧邦", "依然范特西",
        "昆凌", "罗密欧", "海瑟薇", "小周周", " Hathaway ",
        "方文山", "黄俊郎", "钟兴民", "洪敬尧",
        "杰威尔音乐", "超级新人", "新人王",
        "周式", "周杰", "周董", "周女郎",
        "双截棍", "龙卷风", "简单爱",
        "百度", "百度百科", "百科", "维基", "wikipedia",
    ],
    "高血压": [
        "高血压", "Hypertension", "HBP", "HTN", "血压", "血压高",
        "降压", "降压药", "降压药", "血压高", "高血压病",
        "原发性高血压", "继发性高血压", "essential hypertension", "secondary hypertension",
        "白大衣高血压", "white coat", "白大衣",
        "隐匿性高血压", "masked hypertension", "隐蔽性",
        "难治性高血压", "resistant hypertension",
        "恶性高血压", "malignant hypertension",
        "妊娠高血压", "孕期高血压",
        "儿童高血压", "青少年高血压", "小儿高血压",
        "老年高血压", "老人高血压",
        "收缩压", "舒张压", "血压值", "血压计",
        "心率", "脉搏", "动脉", "血管",
        "高血压性心脏病", "高血压肾病", "高血压脑病",
        "脑卒中", "中风", "脑出血", "脑梗", "脑梗死",
        "冠心病", "心衰", "心力衰竭", "心梗", "心肌梗死",
        "动脉粥样硬化", "动脉硬化",
        "降压药", "ACEI", "ARB", "CCB", "利尿剂", "β受体阻滞剂",
        "硝苯地平", "氨氯地平", "缬沙坦", "厄贝沙坦", "美托洛尔",
        "倍他乐克", "拜新同", "代文", "络活喜",
        "高血压并发症", "靶器官损害",
        "低盐饮食", "限盐", "减重", "肥胖", "BMI",
        "高血压饮食", "高血压运动", "高血压禁忌",
        "高血压症状", "头痛", "头晕", "心悸", "耳鸣",
        "高血压遗传", "家族史", "高血压预防",
        "高血压标准", "高血压分级", "高血压诊断",
        "三高", "高血脂", "高血糖", "糖尿病",
    ],
}


def is_relevant(text, topic=None):
    """判断问题是否与指定主题相关。

    topic 为 None 时使用减脂核心词。
    要求：至少出现一个核心词。
    """
    terms = TOPIC_TERMS.get(topic, CORE_TERMS)
    if any(w in text for w in terms):
        return True
    return False

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


def clean_tail(text):
    """清理问题末尾的站点名 / 展开 / 分隔符尾巴。"""
    text = re.sub(r"\s*[\-–—|]\s*(民福康|百度|百度健康|薄荷|家庭医生在线|知乎|简书|新浪|网易|腾讯|凤凰|搜狐|健康之路|三九养生堂|99健康|39健康|寻医问药|杏林普康|好大夫|丁香医生|百度百科|百度文库|湖南省林业局|安徽省林业局|国家林业和草原局|北京市园林绿化局|科普中国|生命教育|问诊|林业局)\s*$", "", text)
    text = re.sub(r"\s*展开\s*$", "", text)
    text = re.sub(r"\s*收起\s*$", "", text)
    text = re.sub(r"\s*[\.]{3,}\s*$", "", text)
    text = re.sub(r"\s*[\-–—\|]+\s*$", "", text)
    # 末尾的"！"或"!": 视为感叹/修辞 → 改为问号（如有疑问词则保留）
    # 但感叹号结尾的内容大多是修辞句，让 judge_questions 处理
    text = text.strip()
    return text


def clean_head(text):
    """清理问题开头的引述/反问/前缀。"""
    # 去掉前后成对引号
    text = text.strip()
    # 成对引号（含英文/中文/日文 + Unicode 引号）
    pairs = [
        ('"', '"'), ('“', '”'),  # 直双引号 + 弯双引号
        ("'", "'"), ('‘', '’'),  # 直单引号 + 弯单引号
        ('「', '」'), ('『', '』'),
        ('《', '》'),
        ('(', ')'), ('（', '）'),
    ]
    for l, r in pairs:
        if text.startswith(l) and text.endswith(r):
            text = text[1:-1].strip()
            break
    # 去掉单边残留引号
    text = re.sub(r'^[「『《"\'\(]+', '', text)
    text = re.sub(r'[」』》"\'\)]+$', '', text)
    # 去掉常见反问/引述前缀
    text = re.sub(
        r"^(可是|但是|然而|不过|那么|反之|若是|如果|因为|由于|虽然|尽管|其实|实际上|不夸张地说|有人会说|有人说|商家说|我们说|据说|据悉|笔者|笔者认为|笔者觉得|笔者通过|笔者结合|笔者在|作者认为|有人认为|有人说|很多人说|据了解|据专家|据介绍|据悉)",
        "", text)
    # 去掉括号式作者/出处前缀：例如 "【光明图片】xxx"
    text = re.sub(r"^【[^】]*】", "", text)
    # 去掉"作者：xxx" "来源：xxx"
    text = re.sub(r"^(作者|来源|编辑|记者|笔者|整理|摘录)[：:][^。]+[。,]?\s*", "", text)
    # 去掉本站/标签前缀
    text = re.sub(r"^(此刻新闻|热点新闻|首页|推荐|热门|专题|正文|导读|摘要)[：:、\s]*", "", text)
    # 去掉导航前缀
    text = re.sub(r"^(上一篇|下一篇|上一条|下一条|相关阅读|延伸阅读|相关推荐|推荐阅读|猜你喜欢)[：:、\s]*", "", text)
    # 去掉 FAQ 标记前缀（多轮，直到无变化）
    for _ in range(5):
        prev = text
        # 多种常见 FAQ/导航/章节前缀
        text = re.sub(
            r"^(常见问题FAQ|常见问题|FAQ|问题|Q&A|Q|A|目录|章节|章|节|第\d+[章节]|Chapter|Topic)"
            r"[：:、\.\s]*",
            "", text)
        # 数字编号前缀
        text = re.sub(r"^\d{1,3}[、\.\)\s]+", "", text)
        if text == prev:
            break
    # 中文数字编号前缀：一、二、三、（一）(一)
    text = re.sub(r"^[（(]?[一二三四五六七八九十百零]+[）)]?[、\.\s]+", "", text)
    # 列表符号前缀：· • ● ○ ▪ ▫
    text = re.sub(r"^[·•●○▪▫\-\*•]+\s*", "", text)
    # 「人民号平台下载客户端」等客户端前缀
    text = re.sub(r"^(人民号平台下载客户端|客户端|下载.*客户端|打开.*App|扫码下载|扫码关注|关注我们)", "", text)
    # 参考资料
    text = re.sub(r"^参考资料[：:]\s*", "", text)
    text = re.sub(r"\[\d+\]", "", text)  # [1] [2] 引用标记
    # 去掉陈述句前缀：所以 / 因此 / 总之 / 综合 / 看来 / 也就是说 / 简单来说
    text = re.sub(r"^(所以|因此|总之|综合|看来|也就是说|简单来说|简言之|换言之|其实|可见到|结果|可见|那么说|看得出来)[，,\s]*", "", text)
    # 去掉逗号/顿号开头的残缺
    text = re.sub(r"^[，,、；;:\s]+", "", text)
    # 去掉末尾残留的"?"、"？"前后多余空格
    text = text.strip()
    return text


def extract_from_title(title, topic=None):
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
    # 标题也要求严格：问号/吗/呢结尾
    if not (title.endswith("？") or title.endswith("?") or title.endswith("吗") or title.endswith("呢")):
        return None
    if is_question_like(title):
        normalized = normalize_text(title)
        if is_relevant(normalized, topic=topic):
            return normalized
    return None


def extract_from_content(html, source_url, topic=None, max_candidates=50):
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
        q = extract_from_title(h, topic=topic)
        if q and q not in candidates:
            candidates.append(q)

    # 2. 按句子切分，提取疑问句
    # 在 。！？? \n 以及各种成对引号/括号后切分
    sentences = re.split(r"(?<=[。！？?\n“”‘’「」『』()（）])", text)
    for s in sentences:
        s = s.strip()
        if is_obviously_not_question(s):
            continue
        # 严格过滤：必须以问号、问号词结尾
        if not (s.endswith("？") or s.endswith("?") or s.endswith("吗") or s.endswith("呢") or s.endswith("啊？") or s.endswith("？")):
            continue
        if is_question_like(s):
            q = normalize_text(s)
            q = clean_tail(q)
            q = clean_head(q)
            if not is_relevant(q, topic=topic):
                continue
            if q not in candidates:
                candidates.append(q)
        if len(candidates) >= max_candidates:
            break

    return [{"text": q, "source_url": source_url, "extracted_from": "content"} for q in candidates]


def extract_from_search_result(title, url, topic=None):
    """当页面无法抓取时，使用搜索结果的页面标题作为问题来源。"""
    q = extract_from_title(title, topic=topic)
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
