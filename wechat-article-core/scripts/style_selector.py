"""风格选择器。

基于输入目录素材、选题、各风格文件的 match_signals，推荐最合适的风格。
"""

import re
from pathlib import Path
from typing import List, Optional


SUPPORTED_EXTENSIONS = {".md", ".txt", ".url"}

# 常见中文停用词 + 英文停用词
_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "这个", "那个", "之", "与", "及", "或", "而", "但是", "然而",
    "因为", "所以", "如果", "那么", "可以", "可能", "进行", "通过", "对于", "关于",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "and", "or", "but",
}


def scan_materials(input_dir: Path, recursive: bool = False) -> List[Path]:
    """扫描输入目录中的素材文件。

    默认只扫描顶层目录，避免读到无关文件。
    开启 recursive 后递归扫描所有子目录。
    """
    if not input_dir or not input_dir.exists():
        return []

    files = []
    for item in input_dir.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(item)
        elif item.is_dir() and recursive:
            files.extend(scan_materials(item, recursive=True))
    return sorted(files)


def _strip_markdown(text: str) -> str:
    """移除 Markdown 格式噪音，保留可读正文。

    - YAML frontmatter
    - 标题 #
    - 加粗/斜体 * _
    - 链接 [text](url) -> text
    - 图片 ![alt](url) -> alt
    - 行内代码 ``
    - HTML 标签
    """
    # 1. YAML frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]

    # 2. Markdown 标题
    text = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
    # 3. 链接 / 图片，保留描述文本
    text = re.sub(r"!\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    # 4. 加粗/斜体标记
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.+?)\1", r"\2", text)
    # 5. 行内代码与反引号
    text = re.sub(r"`+", "", text)
    # 6. HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 7. 折叠空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取适合匹配的关键词。

    对中文按连续汉字提取（避免英文 split 失效），对英文按单词提取，
    并过滤停用词和过短 token。
    """
    cleaned = _strip_markdown(text).lower()
    keywords = []
    # 中文连续汉字（2 字及以上）
    for token in re.findall(r"[一-龥]{2,}", cleaned):
        if token not in _STOPWORDS:
            keywords.append(token)
    # 英文/数字单词
    for token in re.findall(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", cleaned):
        if len(token) >= 2 and token not in _STOPWORDS:
            keywords.append(token)
    return keywords


def summarize_materials(
    files: List[Path],
    output_dir: Optional[Path] = None,
) -> dict:
    """完整读取文本类素材，生成结构化摘要并持久化全量内容。

    Returns:
        {
            "fully_loaded": bool,
            "total_files": int,
            "total_chars": int,
            "files": [{"name": str, "chars": int}],
            "summary_text": str,
            "materials_path": str,
        }
    """
    parts = []
    file_infos = []
    total_chars = 0
    fully_loaded = True

    for f in files:
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                raw = f.read_text(encoding="utf-8")
                cleaned = _strip_markdown(raw)
                total_chars += len(cleaned)
                file_infos.append(
                    {
                        "name": f.name,
                        "chars": len(cleaned),
                    }
                )
                parts.append(f"【{f.name}】{cleaned}")
            except Exception:
                fully_loaded = False
                file_infos.append({"name": f.name, "chars": 0, "error": "读取失败"})
                parts.append(f"【{f.name}】（读取失败）")
        else:
            file_infos.append({"name": f.name, "chars": 0, "skipped": True})
            parts.append(f"【{f.name}】（非文本文件）")

    summary_text = "\n".join(parts)
    materials_path = None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        materials_file = output_dir / "materials_full.md"
        materials_file.write_text(summary_text, encoding="utf-8")
        materials_path = str(materials_file)

    return {
        "fully_loaded": fully_loaded,
        "total_files": len(files),
        "total_chars": total_chars,
        "files": file_infos,
        "summary_text": summary_text,
        "materials_path": materials_path,
    }


def _signal_keywords(signal: str) -> List[str]:
    """把一条 match_signal 拆成可匹配的关键词列表。

    支持中文逗号、顿号、斜杠、空格、竖线等分隔符。
    """
    # 统一常见分隔符为空格
    normalized = re.sub(r"[、，,；;|/]+", " ", signal)
    tokens = normalized.split()
    keywords = []
    for token in tokens:
        token = token.strip().lower()
        if len(token) < 2:
            continue
        # 如果 token 是英文单词/短语，直接保留
        if re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", token):
            keywords.append(token)
            continue
        # 否则提取其中的中文词组
        for zh in re.findall(r"[一-龥]{2,}", token):
            if zh not in _STOPWORDS:
                keywords.append(zh)
    return keywords


def _match_score(topic: str, materials_summary: str, template: dict) -> int:
    """计算风格模板与选题+素材的匹配分数。

    规则：
    - match_signals 中每条信号按命中关键词比例给分：
      命中任意词 +2 分，每多命中一个词额外 +1 分（上限 +4）
    - template id/name/description 中的关键词命中 +1 分
    """
    score = 0
    full_text = f"{topic}\n{materials_summary}".lower()
    # 支持两种模板结构：完整 YAML（meta 嵌套）或扁平测试 fixture
    meta = template.get("meta", template)

    # 1. match_signals
    signals = meta.get("match_signals", [])
    if signals:
        for signal in signals:
            keywords = _signal_keywords(signal)
            if not keywords:
                continue
            hits = sum(1 for kw in keywords if kw in full_text)
            if hits:
                # 任意命中保底 2 分，多命中递增，但单条信号不超过 4 分
                score += min(2 + (hits - 1), 4)

    # 2. 模板自身描述信息作为 fallback
    desc_text = " ".join([
        meta.get("id", ""),
        meta.get("name", ""),
        meta.get("description", ""),
    ])
    for kw in _extract_keywords(desc_text):
        if kw in full_text:
            score += 1

    return score


def recommend_styles(
    topic: str,
    materials_summary: str,
    templates: List[dict],
    min_score: int = 1,
) -> List[dict]:
    """推荐风格模板。

    返回按匹配分数降序排列的模板列表，仅包含分数 >= min_score 的模板。
    每个结果附加 `match_score` 和 `match_reason` 字段。

    注意：输入的 templates 应由 list_all_templates() 提供，即已经在白名单内。
    本函数不会返回白名单外的模板。
    """
    scored = []
    for t in templates:
        score = _match_score(topic, materials_summary, t)
        if score >= min_score:
            item = dict(t)
            item["match_score"] = score
            item["match_reason"] = f"匹配信号命中 {score // 2} 条"
            scored.append(item)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:3]


def validate_template_id(template_id: str, templates: List[dict]) -> bool:
    """校验模板 ID 是否在可用模板白名单内。

    防止编造风格：用户直接指定的模板，或上游传递的 template_id，
    必须在 list_all_templates() 实际返回的列表中。
    """
    if not template_id:
        return False
    allowed_ids = {t.get("id") for t in templates if t.get("id")}
    return template_id in allowed_ids
