#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_drift_check.py — 派生物↔源 漂移巡检。

定位「单点信息漂移」：某些细节只存在于派生物（面试素材/、生成物/），
而源（原始事实/ + 自动生成/）里没有——按规范清理生成物时这些细节会永久丢失。

方法：抽取派生文件中的 distinctive 词（中文 3-8 字 n-gram + 英文技术词），
含停用词的 n-gram 直接丢弃，HTML/CSS 标签先行剥离；
剩余候选词逐词在源文本中做子串比对，
报告「出现于 ≥ --min-files 个派生文件、但源里没有」的待回流清单。

用法：
    python3 scripts/kb_drift_check.py --kb <路径> [--top 30] [--min-files 2] [--json-out drift.json]

退出码：0 = 巡检完成（有漂移也是 0，本工具是报告不是闸门）。
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

CJK = re.compile(r"[一-鿿]+")
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9][A-Za-z0-9+.\-]{0,14}")
HTML_STYLE_SCRIPT = re.compile(r"<(style|script)[^>]*>.*?</\1>", re.S | re.I)
HTML_TAG = re.compile(r"<[^>]+>")
MD_LINK = re.compile(r"!?\[[^\]]*\]\([^)]*\)")

# 停用词：功能词（含单字，作子串过滤用——任何含功能字的 n-gram 都丢弃）
# + 求职领域高频泛词（派生文件里到处都有、无判别力）+ HTML/CSS 噪音词
STOPWORDS = set("""
我们 你们 他们 自己 以及 或者 但是 因为 所以 如果 通过 进行 相关 并且 其中 之后 之前
期间 以上 以下 包括 基于 对于 关于 根据 随着 由于 不仅 同时 另外 此外 因此 然后 等
可以 能够 需要 没有 已经 正在 将会 可能 应该 必须 之一 一系列 一定程度 一直以来 等
工作 项目 公司 岗位 简历 面试 求职 经历 经验 能力 技能 业务 客户 用户 产品 部门 团队
负责 参与 主导 管理 协调 沟通 推动 完成 实现 落地 提升 建立 搭建 提供 支持
发展 行业 领域 方向 目标 成果 业绩 职责 职位 企业 单位 机会 挑战 流程 方案 需求 问题
这个 那个 一个 一些 各种 多项 多个 大幅 显著 有效 成功 顺利 高效 全面 深入 持续 阶段
年月 至今 任职 入职 离职 担任 汇报 期间 主要负责 工作职责 工作描述 项目描述 核心
个人 本人 职业 专业 熟悉 具备 拥有 丰富 年 经验 以上 以下 一名 一名名
candidate resume career profile summary experience education skills
project projects company position responsible achievement achievements email phone
address date objective employment history reference references available upon request
div span style class color font size width height margin padding border background table align
href http https www com html head body meta charset utf script link rel title page column strong
and the for with from font-family font-size sans-serif helvetica apple-system antialiased arial
absolute relative fixed after before hover focus active none block inline flex grid center left
right bold normal auto important content display position overflow cursor pointer text-decoration
transform transition animation opacity zindex letter-spacing white-space nowrap break-word radius
shadow solid hidden visible px rem em pdf
取消 勾选 请点击 点击 展开 收起 编辑 下载 打印 导出
修改 极简 页眉 页脚 预览 默认 边距 切换 主题 即为 所选 风格 选择
了 的 在 是 有 和 与 及 对 把 被 让 向 从 到 于 之 其 该 此 各 每 本 你 我 他 她 它 这 那
或 且 而 很 更 最 不 无 未 已 正 将 可 能 会 要 想 说 看 用 做 搞 拿 给 过 也 都 就 还 但 并
""".split())
STOPWORD_LENS = sorted({len(w) for w in STOPWORDS}, reverse=True)

MAX_N = 8          # n-gram 窗口上限
SPAN_MAX = 12      # 干净段 ≤12 字整体成词；更长才滑窗
MIN_N = 3
DERIVED_EXTS = {".md", ".markdown", ".html", ".htm", ".txt"}
SOURCE_EXTS = {".md", ".markdown", ".txt", ".yaml", ".yml", ".json"}


def _iter_files(root, exts):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(dirpath, name)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _has_stopword(t):
    return any(sw in t for sw in STOPWORDS if len(sw) >= 2) or any(
        c in STOPWORDS for c in t if len(c) == 1
    )


def _clean_spans(run):
    """按停用词边界把连续汉字切成「干净段」：段内不含任何停用词。"""
    spans = []
    buf = []
    L = len(run)
    i = 0
    while i < L:
        hit = None
        for n in STOPWORD_LENS:
            if n <= L - i and run[i:i + n] in STOPWORDS:
                hit = n
                break
        if hit:
            if buf:
                spans.append("".join(buf))
                buf = []
            i += hit
        else:
            buf.append(run[i])
            i += 1
    if buf:
        spans.append("".join(buf))
    return spans


def _tokens(text):
    text = HTML_STYLE_SCRIPT.sub(" ", text)
    text = HTML_TAG.sub(" ", text)
    text = MD_LINK.sub(" ", text)
    out = set()
    for m in CJK.finditer(text):
        for span in _clean_spans(m.group(0)):
            L = len(span)
            if L < 2:
                continue
            if L <= SPAN_MAX:
                out.add(span)
            cap = min(MAX_N, SPAN_MAX, L)
            for i in range(L):
                for n in range(cap, MIN_N - 1, -1):
                    if i + n <= L:
                        out.add(span[i:i + n])
    for m in LATIN.finditer(text):
        t = m.group(0).lower()
        if t not in STOPWORDS and not t.isdigit() and t not in out:
            out.add(t)
    return out


def check(root, min_files=2, top=30, json_out=None):
    """返回巡检报告 dict：{"structure_ok", "derived_scanned", "min_files", "drift": [...]}"""
    structure_ok = common.kb_structure_ok(root)
    raw_dir = os.path.join(root, common.DIR_RAW)
    auto_dir = os.path.join(root, common.DIR_AUTO)
    derived_dirs = [
        os.path.join(root, common.DIR_INTERVIEW),
        os.path.join(root, common.DIR_OUTPUT),
    ]

    source_text = ""
    for d, exts in ((raw_dir, SOURCE_EXTS), (auto_dir, SOURCE_EXTS)):
        if os.path.isdir(d):
            for p in _iter_files(d, exts):
                source_text += _read(p) + "\n"
    source_text_l = source_text.lower()

    term_files = defaultdict(set)
    term_count = defaultdict(int)
    derived_scanned = 0
    for d in derived_dirs:
        if not os.path.isdir(d):
            continue
        for p in _iter_files(d, DERIVED_EXTS):
            derived_scanned += 1
            for t in _tokens(_read(p)):
                term_files[t].add(p)
                term_count[t] += 1

    drift = []
    # 出现于过半数派生文件的词是模板词（简历板块标题等），不构成漂移
    template_threshold = max(min_files, derived_scanned // 2)
    for t, files in term_files.items():
        if len(files) < min_files or len(files) > template_threshold:
            continue
        if t in source_text or t in source_text_l:
            continue
        drift.append({
            "term": t,
            "count": term_count[t],
            "files": sorted(files),
        })
    # 子串合并：短词的文件集合被长词覆盖时，只留长词（消滑窗边界碎片）
    dropped = set()
    for a in drift:
        for b in drift:
            if a is b or a["term"] in dropped or b["term"] in dropped:
                continue
            if len(a["term"]) < len(b["term"]) and a["term"] in b["term"]:
                if set(a["files"]).issubset(set(b["files"])):
                    dropped.add(a["term"])
    drift = [d for d in drift if d["term"] not in dropped]
    drift.sort(key=lambda d: (-len(d["files"]), -d["count"], d["term"]))
    drift = drift[:top]

    report = {
        "structure_ok": structure_ok,
        "derived_scanned": derived_scanned,
        "min_files": min_files,
        "drift": drift,
    }
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    ap = argparse.ArgumentParser(description="派生物↔源 漂移巡检")
    ap.add_argument("--kb", default=None)
    ap.add_argument("--min-files", type=int, default=2, help="词至少出现在 N 个派生文件才报告（默认 2）")
    ap.add_argument("--top", type=int, default=30, help="最多输出 N 条（默认 30）")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    root = common.kb_root(args.kb)
    report = check(root, min_files=args.min_files, top=args.top, json_out=args.json_out)

    print("漂移巡检报告（派生物 → 源）")
    print("=" * 40)
    if not report["structure_ok"]:
        print("⚠️  知识库结构不完整（缺 原始事实/ 或 自动生成/），结果仅供参考")
    print("扫描派生物文件: %d 个" % report["derived_scanned"])
    if report["drift"]:
        print("\n待回流清单（派生物有、源没有，按出现文件数排序）：")
        for i, d in enumerate(report["drift"], 1):
            names = "、".join(os.path.relpath(p, root) for p in d["files"][:3])
            more = " 等 %d 个文件" % len(d["files"]) if len(d["files"]) > 3 else ""
            print("  %2d. %s —— 出现于 %s%s" % (i, d["term"], names, more))
        print("\n建议：把以上细节回写进 原始事实/ 对应文件后，重跑 facts_parser.py 重建 facts.yaml。")
    else:
        print("\n未发现漂移：派生物的关键词在源中均有覆盖 ✅")
    print("漂移项共 %d 个" % len(report["drift"]))


if __name__ == "__main__":
    main()
