#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_url.py — 网页抓取：优先直接 HTTP，失败后尝试 OpenCLI，最后返回 None。

注意：本脚本不做问题提取，只负责获取网页原始 HTML/Markdown。
"""

import shutil
import subprocess
import urllib.request
from urllib.error import HTTPError, URLError


def fetch_http(url, timeout=15):
    """使用 urllib 直接抓取网页。"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError) as e:
        return {"error": str(e), "method": "http"}
    except Exception as e:
        return {"error": str(e), "method": "http"}


def fetch_opencli(url, timeout=60):
    """使用 OpenCLI browser 抓取网页。

    要求环境已安装 opencli 并配置好浏览器扩展。
    """
    if not shutil.which("opencli"):
        return {"error": "opencli not installed", "method": "opencli"}
    try:
        cmd = [
            "opencli", "browser", "goto", url,
            "--window", "background",
            "--keep-tab", "false",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout
        return {"error": result.stderr or "opencli failed", "method": "opencli"}
    except subprocess.TimeoutExpired:
        return {"error": "opencli timeout", "method": "opencli"}
    except Exception as e:
        return {"error": str(e), "method": "opencli"}


def fetch(url, use_opencli=True):
    """尝试多种方式抓取 URL。

    返回：
        - str: 成功时的网页内容
        - dict: 失败时的错误信息 {error, method}
    """
    # 1. 直接 HTTP
    result = fetch_http(url)
    if isinstance(result, str):
        return result

    # 2. OpenCLI 兜底
    if use_opencli:
        result2 = fetch_opencli(url)
        if isinstance(result2, str):
            return result2
        # 合并错误信息
        return {
            "error": f"http: {result.get('error')}; opencli: {result2.get('error')}",
            "method": "all_failed",
        }

    return result


def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 fetch_url.py <url> [--no-opencli]")
        sys.exit(1)
    url = sys.argv[1]
    use_opencli = "--no-opencli" not in sys.argv
    out = fetch(url, use_opencli=use_opencli)
    if isinstance(out, str):
        print(out[:2000])  # 只打印前 2000 字符避免刷屏
    else:
        print(out)


if __name__ == "__main__":
    main()
