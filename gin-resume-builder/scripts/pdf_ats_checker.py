#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_ats_checker.py — 验证 PDF 文本层对 ATS 友好（N5）。

脚本职责：解析候选人在浏览器/Word 中「打印为 PDF」或 Playwright 生成的简历 PDF，
检查文本层是否可抽取、是否出现乱码、联系方式是否完整、目标关键词是否命中。
若文本层损坏，提示改用 paged.js / weasyprint 或修正 HTML 结构。

用法:
    python3 pdf_ats_checker.py resume.pdf [--keyword python] [--keyword B2B销售] [--dump out.txt]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


class CheckError(Exception):
    """PDF 校验未通过（用于 CLI 退出码）。"""


# 常见中文乱码/替换字符信号
GARBLED_PATTERNS = [
    r"锟斤拷",                      # GBK/UTF-8 互转典型乱码
    r"Ã¢â‚¬â„¢|Ã¢â‚¬|Ã¢â‚¬",  # UTF-8 被误读为 Latin-1 后再转
    r"ï¿½",                        # U+FFFD 再编码
    r"[�]{2,}",              # 连续替换字符
    r"[-]{2,}",       # 私有区字符连续出现
]
GARBLED_RE = [re.compile(p) for p in GARBLED_PATTERNS]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.UNICODE)
PHONE_RE = re.compile(
    r"(?:\+?86[-\s]?)?"
    r"(?:1[3-9]\d{9}|"
    r"0\d{2,3}-?\d{7,8})",
    re.UNICODE,
)


def _run_tool(command):
    """运行外部命令并返回 stdout；命令缺失时抛出 CheckError。"""
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except FileNotFoundError as exc:
        raise CheckError(
            "所需命令 '%s' 未找到。请安装 pypdf（pip install pypdf）或 poppler-utils "
            "（macOS: brew install poppler；Debian/Ubuntu: apt install poppler-utils；"
            "Windows: choco install poppler）" % command[0]
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip() or "command failed"
        raise CheckError("%s 无法读取 PDF：%s" % (command[0], detail)) from exc


def _normalize_text(text):
    return " ".join(text.split())


def _extract_pypdf(pdf_path):
    """优先使用 pypdf 抽取。失败或无可读字符时返回 None。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(pdf_path))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None
    if len(_normalize_text(text)) == 0:
        return None
    return text, pages


def _extract_pdftotext(pdf_path):
    """Poppler pdftotext 回退。"""
    text = _run_tool(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])
    info = _run_tool(["pdfinfo", str(pdf_path)])
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
    pages = int(match.group(1)) if match else None
    return text, pages


def extract_text_layer(pdf_path):
    """抽取 ATS 可读文本。返回 (text, pages, extractor_name)。"""
    pypdf_result = _extract_pypdf(pdf_path)
    if pypdf_result is not None:
        return (*pypdf_result, "pypdf")
    text, pages = _extract_pdftotext(pdf_path)
    return text, pages, "pdftotext"


def detect_garbled(text):
    """返回 (是否疑似乱码, 乱码得分 0-1)。"""
    if not text:
        return False, 0.0
    total_chars = len(text)
    if total_chars == 0:
        return False, 0.0

    hits = sum(1 for pat in GARBLED_RE if pat.search(text))
    # 替换字符与私有区字符占比
    replacement_count = text.count("�")
    pua_count = sum(1 for c in text if "" <= c <= "")
    score = (hits * 0.25) + (replacement_count / max(total_chars, 1)) + (pua_count / max(total_chars, 1))
    # 只要命中典型模式即视为乱码
    return hits > 0 or score > 0.02, min(score, 1.0)


def check_contact(text):
    """检查联系方式是否可抽取。"""
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    return {
        "email": bool(email),
        "phone": bool(phone),
        "any": bool(email or phone),
        "email_value": email.group(0) if email else None,
        "phone_value": phone.group(0) if phone else None,
    }


def check_keywords(text, keywords):
    """返回每个关键词的命中情况及缺失列表（不区分大小写、忽略空白）。"""
    normalized = _normalize_text(text).lower()
    result = {}
    for kw in keywords:
        key = _normalize_text(kw).lower()
        result[kw] = key in normalized
    missing = [kw for kw in keywords if not result[kw]]
    return {"hits": result, "missing": missing, "coverage": round((len(keywords) - len(missing)) / len(keywords), 2) if keywords else 1.0}


def check_pdf(pdf_path, keywords=None, dump_text=None):
    """对 PDF 进行 ATS 文本层诊断，返回结构化结果字典。

    即使 PDF 不存在或抽取失败，也会返回可用字段（available=False），
    不会抛异常，便于上游工作流统一处理。
    """
    keywords = keywords or []
    path = Path(pdf_path)
    result = {
        "path": str(path),
        "available": False,
        "extractor": None,
        "pages": None,
        "text_sample": "",
        "char_count": 0,
        "contact": {"email": False, "phone": False, "any": False},
        "keywords": {"hits": {}, "missing": [], "coverage": 1.0},
        "garbled": False,
        "garbled_score": 0.0,
        "issues": [],
        "ok": False,
    }

    if not path.is_file():
        result["issues"].append("PDF 文件不存在")
        return result

    try:
        text, pages, extractor = extract_text_layer(path)
    except CheckError as exc:
        result["issues"].append(str(exc))
        return result
    except Exception as exc:
        result["issues"].append("抽取失败：%s" % exc)
        return result

    normalized = _normalize_text(text)
    result.update({
        "available": True,
        "extractor": extractor,
        "pages": pages,
        "text_sample": normalized[:600],
        "char_count": len(normalized),
    })

    garbled, score = detect_garbled(text)
    result["garbled"] = garbled
    result["garbled_score"] = round(score, 4)
    if garbled:
        result["issues"].append("检测到乱码或替换字符，ATS 可能无法正确识别文本")

    contact = check_contact(normalized)
    result["contact"] = contact
    if not contact["any"]:
        result["issues"].append("未抽取到邮箱或电话")

    if keywords:
        kw_result = check_keywords(normalized, keywords)
        result["keywords"] = kw_result
        if kw_result["missing"]:
            result["issues"].append("缺失关键词：%s" % ", ".join(kw_result["missing"]))

    if len(normalized) < 50:
        result["issues"].append("文本层字符数过少（%d），可能只有图片无文字" % len(normalized))

    result["ok"] = not result["issues"]

    if dump_text:
        dump_path = Path(dump_text)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        dump_path.write_text(
            text if text.endswith("\n") else text + "\n",
            encoding="utf-8",
        )

    return result


def main():
    ap = argparse.ArgumentParser(description="ATS PDF 文本层验证")
    ap.add_argument("pdf", help="PDF 路径")
    ap.add_argument("--keyword", action="append", default=[], help="目标关键词，可重复")
    ap.add_argument("--dump-text", help="将抽取文本写入指定路径")
    args = ap.parse_args()

    result = check_pdf(args.pdf, keywords=args.keyword, dump_text=args.dump_text)
    print("PDF: %s" % result["path"])
    print("可用: %s" % ("是" if result["available"] else "否"))
    print("抽取器: %s" % (result["extractor"] or "N/A"))
    print("页数: %s" % (result["pages"] or "N/A"))
    print("字符数: %d" % result["char_count"])
    print("乱码: %s（得分 %.2f）" % ("是" if result["garbled"] else "否", result["garbled_score"]))
    print("联系方式: 邮箱=%s 电话=%s" % (result["contact"]["email"], result["contact"]["phone"]))
    if args.keyword:
        print("关键词覆盖: %.0f%%" % (result["keywords"]["coverage"] * 100))
        if result["keywords"]["missing"]:
            print("缺失关键词: %s" % ", ".join(result["keywords"]["missing"]))
    if result["issues"]:
        print("问题:")
        for issue in result["issues"]:
            print("  - %s" % issue)
    sys.exit(0 if result["ok"] else 3)


if __name__ == "__main__":
    main()
