#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harvest.py — 教程采集层的工具脚本（通道调度/后处理/内容验收/落盘/manifest）。

分工：采集动作由 Agent 完成（调 firecrawl CLI / opencli / collector），
本脚本负责判断与记录——决定每个 URL 走哪个通道、剥掉站内锚点噪音、
校验正文是否够料、生成 coverage-manifest.json。
规则来自 9/2-9/3 减脂/力量训练实测：
- Docusaurus 标题锚点 [](url "直接链接") 占文件 3/4 体积 → 剥
- 外部引用链接是溯源线索 → 保留
- 正文 <500 中文字 = 抓到导航页/空页 → 判失败
- 知乎对 datacenter IP 反爬 → 域名黑名单优先于 action 标注

用法：
    python3 harvest.py channel --url "..." --action "单页采集"
    python3 harvest.py postprocess --file a.md [--site-host docs.x.com]
    python3 harvest.py validate --file a.md [--min-chars 500]
    python3 harvest.py manifest --dir <输出目录> --topic "..." [--target-words 8000]
"""
import argparse
import json
import os
import re
from urllib.parse import urlparse

# ---------- 通道调度 ----------

# 域名黑名单：反爬/登录墙站点，必须真实浏览器，firecrawl 必撞验证码。
# 匹配规则：netloc == h 或 netloc 以 ".h" 结尾（防 example-x.com 误伤）
OPENCLI_HOSTS = ("zhihu.com", "weibo.com", "x.com",
                 "twitter.com", "linux.do")
# 路径级黑名单：B站专栏走 opencli，B站视频走 collector，按域名分不开
OPENCLI_PATHS = ("bilibili.com/read",)
# collector 通道：PDF / 公众号 / 视频页
COLLECTOR_HINTS = (".pdf", "mp.weixin.qq.com", "youtube.com", "bilibili.com/video",
                   "b23.tv")
BOOK_ACTIONS = ("找电子版/购书",)
DOWNLOAD_ACTIONS = ("整站扒取",)


def pick_channel(url, action, firecrawl_available=True):
    """返回通道：firecrawl-scrape / firecrawl-download / opencli / collector / skip-book。

    优先级：域名黑名单 > action 标注 > 扩展名 > 默认。
    firecrawl_available=False 时 firecrawl-download 降级为 firecrawl-scrape
    （download 需要 key，scrape 免 key）。
    """
    netloc = urlparse(url).netloc.lower()
    host = (netloc + urlparse(url).path).lower()

    # 1) 黑名单最优先——action 标错也不能硬撞反爬。
    #    域名匹配用真后缀（example-x.com 不得误伤 x.com）
    if any(netloc == h or netloc.endswith("." + h) for h in OPENCLI_HOSTS):
        return "opencli"
    if any(h in host for h in OPENCLI_PATHS):
        return "opencli"

    # 2) action 显式标注
    if action in BOOK_ACTIONS:
        return "skip-book"
    if action in DOWNLOAD_ACTIONS:
        return "firecrawl-download" if firecrawl_available else "firecrawl-scrape"

    # 3) 扩展名/内容类型
    if any(h in host for h in COLLECTOR_HINTS):
        return "collector"

    # 4) 默认
    return "firecrawl-scrape"


# ---------- 后处理 ----------

# Markdown 链接 [text](url "title")，text 可空（Docusaurus 锚点）
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _host_of(url):
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def postprocess_markdown(text, site_host=None):
    """剥站内链接噪音，保留外部引用链接。

    - 空显示文本的锚点 [](url "…")：整段移除
    - 站内链接 [text](site-url)：剥 URL 留 text（阅读流不断）
    - 外部链接：原样保留（溯源线索）
    - site_host=None：不剥任何 URL，只剥空锚点
    """
    site_host = (site_host or "").lower().removeprefix("www.")

    def _repl(m):
        label, target = m.group(1), m.group(2)
        if not label:
            return ""  # 空锚点（Docusaurus 标题直接链接）→ 移除
        if site_host and site_host in _host_of(target):
            return label  # 站内 → 留文本
        return m.group(0)  # 外部 → 保留

    return _MD_LINK.sub(_repl, text)


# ---------- 内容验收 ----------

_CJK = re.compile(r"[一-鿿]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")


def count_chinese_chars(text):
    return len(_CJK.findall(text))


def count_content_units(text):
    """内容量 = 中文字数 + 英文词数。语言政策：教材级源不限语言，
    英文权威源（WHO/arXiv）同样是有效素材，不得按中文字数误杀。"""
    return len(_CJK.findall(text)) + len(_LATIN_WORD.findall(text))


def is_valid_content(text, min_chars=500):
    """正文 ≥ min_chars 个内容单位（中文字+英文词）才算采到真内容（防导航页/空页）。"""
    return count_content_units(text) >= min_chars


# ---------- 验收门槛 ----------

def check_acceptance(total_chars, target_words, coverage):
    """素材验收：总量 ≥ 3×目标成稿字数；每个 TOP 问题 ≥2 独立来源。

    coverage: {问题: 已覆盖来源数}
    返回 {"material_ok": bool, "coverage_gaps": [...], "needed_chars": int}
    """
    needed = target_words * 3
    gaps = [q for q, n in coverage.items() if n < 2]
    return {
        "material_ok": total_chars >= needed,
        "coverage_gaps": gaps,
        "needed_chars": max(0, needed - total_chars),
        "达标线": needed,
    }


# ---------- 落盘 ----------

_BAD_FILENAME = re.compile(r'[\\/:*?"<>|？?！!，,。.\s]+')


def organize_path(output_dir, layer, title):
    """按层分目录落盘：<output_dir>/<layer>/<安全文件名>.md"""
    safe = _BAD_FILENAME.sub("_", title).strip("_")[:60] or "untitled"
    d = os.path.join(output_dir, layer)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, safe + ".md")


def manifest_entry(url, layer, title, path, words, channel, status, retries, covers):
    return {"url": url, "layer": layer, "title": title, "path": path,
            "字数": words, "channel": channel, "status": status,
            "重试次数": retries, "覆盖问题": covers}


def write_manifest(output_dir, entries, topic, target_words, total_chars,
                   coverage=None):
    """写 coverage-manifest.json：逐条记录 + 验收结论，可被下游原子技能读取。"""
    coverage = coverage or {}
    acc = check_acceptance(total_chars, target_words, coverage)
    data = {
        "topic": topic,
        "target_words": target_words,
        "总字数": total_chars,
        "entries": entries,
        "观察哨": [e["url"] for e in entries if e.get("value") == "unknown"],
        "验收": acc,
    }
    p = os.path.join(output_dir, "coverage-manifest.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="教程采集层工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("channel", help="决定 URL 走哪个采集通道")
    c.add_argument("--url", required=True)
    c.add_argument("--action", default="单页采集")
    c.add_argument("--no-firecrawl-key", action="store_true",
                   help="无 firecrawl key（download 降级为 scrape）")

    pp = sub.add_parser("postprocess", help="剥站内锚点链接噪音")
    pp.add_argument("--file", required=True)
    pp.add_argument("--site-host", default=None)

    v = sub.add_parser("validate", help="校验正文是否够料")
    v.add_argument("--file", required=True)
    v.add_argument("--min-chars", type=int, default=500)

    m = sub.add_parser("manifest", help="汇总输出 coverage-manifest.json")
    m.add_argument("--dir", required=True)
    m.add_argument("--topic", required=True)
    m.add_argument("--target-words", type=int, default=8000)

    args = ap.parse_args()

    if args.cmd == "channel":
        ch = pick_channel(args.url, args.action,
                          firecrawl_available=not args.no_firecrawl_key)
        print(json.dumps({"channel": ch}, ensure_ascii=False))
    elif args.cmd == "postprocess":
        text = open(args.file, encoding="utf-8").read()
        out = postprocess_markdown(text, site_host=args.site_host)
        open(args.file, "w", encoding="utf-8").write(out)
        print(json.dumps({"stripped_to": len(out)}, ensure_ascii=False))
    elif args.cmd == "validate":
        text = open(args.file, encoding="utf-8").read()
        n = count_chinese_chars(text)
        print(json.dumps({"chinese_chars": n, "valid": is_valid_content(text, args.min_chars)},
                         ensure_ascii=False))
    elif args.cmd == "manifest":
        # 扫输出目录既有 .md 汇总 manifest（Agent 采集完跑这个收口）
        entries, total = [], 0
        for root, _dirs, files in os.walk(args.dir):
            for fn in sorted(files):
                if not fn.endswith(".md"):
                    continue
                p = os.path.join(root, fn)
                text = open(p, encoding="utf-8").read()
                words = count_content_units(text)
                total += words
                entries.append(manifest_entry(
                    url="", layer=os.path.basename(root), title=fn[:-3],
                    path=os.path.relpath(p, args.dir), words=words,
                    channel="", status="ok", retries=0, covers=[]))
        write_manifest(args.dir, entries, args.topic, args.target_words, total)
        print(json.dumps({"total_chars": total, "files": len(entries)},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
