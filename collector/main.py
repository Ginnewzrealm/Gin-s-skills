#!/usr/bin/env python3
"""采集器 - 多源内容采集器
自动识别输入类型，从多种来源采集内容，保存到 COLLECTOR_DIR 指定目录
支持：网页（含付费墙绕过）、微信公众号、播客、X/Twitter、YouTube、PDF、EPUB、Office文档等
"""

import sys
import os
import subprocess
import tempfile
import json
import time
import re
import socket
from pathlib import Path


# ---------- OpenCLI 浏览器生命周期管理 ----------

from scripts.chrome_launcher_adapter import ensure_browser_ready, cleanup_browser


def run_opencli_cmd(cmd, input_arg, allow_fallback=False):
    """
    在浏览器就绪后执行 OpenCLI 命令，并在 finally 中清理。

    浏览器就绪优先由 opencli-chrome-launcher 负责；launcher 未安装时
    降级使用 collector 自带的 scripts/browser_manager.py。

    参数：
        cmd: 已构造好的 OpenCLI 命令列表（含 opencli 路径）
        input_arg: 原始输入，仅用于错误信息
        allow_fallback: 浏览器就绪失败时是否返回 None 而非退出
    返回：
        subprocess.CompletedProcess 或 None（仅在 allow_fallback=True 且失败时）
    """
    ok, result, source = ensure_browser_ready(session_name="collector")
    if not ok:
        if allow_fallback:
            cleanup_browser(session_name="collector", source=source)
            return None
        print(f"❌ {result.get('message', '浏览器就绪失败')}", file=sys.stderr)
        sys.exit(1)

    try:
        print("   通过 OpenCLI 获取内容...")
        return subprocess.run(cmd, capture_output=True, timeout=60)
    finally:
        cleanup_browser(session_name="collector", source=source)


# ---------- 输入识别 ----------

def detect_input_type(input_path):
    """检测输入类型"""
    if input_path.startswith('http'):
        if 'mp.weixin.qq.com' in input_path:
            return 'weixin'
        elif 'youtube.com' in input_path or 'youtu.be' in input_path:
            return 'youtube'
        elif 'xiaoyuzhoufm.com' in input_path or 'ximalaya.com' in input_path or 'bilibili.com' in input_path:
            return 'podcast'
        elif 'x.com' in input_path or 'twitter.com' in input_path:
            # 细分 X/Twitter 三种子类型
            if '/i/article/' in input_path:
                return 'x_twitter_article'
            elif '/search?' in input_path or 'search=' in input_path:
                return 'x_twitter_search'
            elif '/status/' in input_path:
                # 单条推文/帖子 URL：例如 /chuhaiqu/status/123456...
                return 'x_twitter_status'
            else:
                return 'x_twitter_user'
        else:
            return 'url'

    path = Path(input_path).expanduser()
    if not path.exists():
        return 'search'

    suffix = path.suffix.lower()
    if suffix == '.epub':
        return 'epub'
    elif suffix in ['.pdf', '.txt', '.md']:
        return 'document'
    elif suffix in ['.docx', '.pptx', '.xlsx']:
        return 'office'
    elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return 'image'
    elif suffix in ['.mp3', '.wav']:
        return 'audio'
    elif suffix == '.zip':
        return 'zip'
    else:
        return 'unknown'


def get_output_dir():
    """获取输出目录（COLLECTOR_DIR 环境变量 > 技能目录 output_dir.config > 默认 ~/CollectorOutput）

    首次运行时（无环境变量且无配置文件）会提示用户确认输出目录，并写入 output_dir.config。
    非交互环境下自动使用默认目录并记录。
    """
    output_dir = os.getenv('COLLECTOR_DIR')
    if output_dir:
        return os.path.abspath(os.path.expanduser(output_dir))

    config_path = Path(__file__).parent / 'output_dir.config'
    if config_path.exists():
        lines = config_path.read_text(encoding='utf-8').strip().splitlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                output_dir = line
                return os.path.abspath(os.path.expanduser(output_dir))

    # 首次运行：提示确认或自动使用默认
    return configure_output_dir()


def configure_output_dir():
    """首次运行时确认输出目录并写入 output_dir.config。"""
    default_dir = os.path.abspath(os.path.expanduser('~/CollectorOutput'))
    config_path = Path(__file__).parent / 'output_dir.config'

    if not sys.stdin.isatty():
        # 非交互环境（如 Claude 自动执行、测试）：使用默认目录并记录
        config_path.write_text(f"{default_dir}\n", encoding='utf-8')
        return default_dir

    print("首次运行采集器，请确认输出目录。")
    print(f"默认目录: {default_dir}")
    print("直接回车使用默认目录，或输入新路径：")
    try:
        user_input = input("> ").strip()
    except EOFError:
        user_input = ""

    output_dir = user_input if user_input else default_dir
    output_dir = os.path.abspath(os.path.expanduser(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    config_path.write_text(f"{output_dir}\n", encoding='utf-8')
    print(f"✅ 输出目录已记录到 {config_path}")
    return output_dir


def get_proxy():
    """读取技能目录下的 proxy.config 文件获取代理地址（可选）"""
    config_path = Path(__file__).parent / 'proxy.config'
    if config_path.exists():
        proxy = config_path.read_text(encoding='utf-8').strip()
        if proxy and not proxy.startswith('#'):
            return proxy
    return None


def is_overseas_url(url):
    """判断 URL 是否为海外网站（非 .cn 域名）"""
    try:
        host = url.split('://')[1].split('/')[0]
        # 去掉端口号
        host = host.split(':')[0]
        # 如果域名以 .cn 结尾，视为国内网站
        if host.endswith('.cn'):
            return False
        # 常见的国内域名后缀
        domestic_suffixes = ('.cn', '.com.cn', '.net.cn', '.org.cn', '.gov.cn')
        for suffix in domestic_suffixes:
            if host.endswith(suffix):
                return False
        return True
    except Exception:
        return False


def check_proxy_connectivity(proxy_url, timeout=3):
    """检查代理端口是否可连通"""
    try:
        # 解析代理地址，如 http://127.0.0.1:6696
        proxy_host = proxy_url.replace('http://', '').replace('https://', '').split(':')[0]
        proxy_port = int(proxy_url.replace('http://', '').replace('https://', '').split(':')[1])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((proxy_host, proxy_port))
        sock.close()
        return result == 0
    except Exception:
        return False


def resolve_opencli_path():
    """动态检测 OpenCLI 路径，优先从 PATH 中查找"""
    # 优先从 PATH 中查找
    result = subprocess.run(['which', 'opencli'], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    # 尝试常见的本地安装路径
    common_paths = [
        '/Users/fubo/.openclaw/workspace-angie/node_modules/.bin/opencli',
        str(Path.home() / '.openclaw' / 'workspace-angie' / 'node_modules' / '.bin' / 'opencli'),
        '/usr/local/bin/opencli',
        '/opt/homebrew/bin/opencli',
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path
    return 'opencli'  # 最后 fallback 到 PATH 中的 opencli


def save_content(content, source_type, title, source_url=None):
    """将采集的内容保存到输出目录

    目录结构: {COLLECTOR_DIR}/{source_type}/{sanitized_title}[_N].md
    文件名冲突时追加序号 _1, _2...
    """
    output_base = get_output_dir()

    # 按来源类型建子目录
    type_dir = os.path.join(output_base, source_type)
    os.makedirs(type_dir, exist_ok=True)

    # 生成安全的文件名（去除非法字符，截断至60字符）
    safe_title = re.sub(r'[：:/\\?|<>*"\']', '_', title).strip('_')[:60]

    # 检查文件名冲突，追加序号
    base_filename = f"{safe_title}.md"
    output_path = os.path.join(type_dir, base_filename)

    serial = 1
    while os.path.exists(output_path):
        serial += 1
        base_filename = f"{safe_title}_{serial}.md"
        output_path = os.path.join(type_dir, base_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"- **来源**: {source_url or '本地文件'}\n")
        f.write(f"- **来源类型**: {source_type}\n")
        f.write(f"- **采集时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n---\n\n")
        f.write(content)

    print(f"\n✅ 已保存: {output_path}")
    print(f"   ({len(content)} 字符)")
    return output_path


def extract_epub_to_txt(epub_path):
    """提取 EPUB 为纯文本"""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(epub_path))
    content = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            content.append(soup.get_text())

    return '\n\n'.join(content)


def fetch_url_fallback(url, proxy=None):
    """当 fetch_url.sh 失败时的兜底方案：直接 curl + 简单文本提取"""
    env = {}
    if proxy:
        env['https_proxy'] = proxy
        env['http_proxy'] = proxy
    result = subprocess.run(
        ['curl', '-sL', '--max-time', '15',
         '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
         url],
        capture_output=True, text=True, timeout=20, env={**os.environ, **env}
    )
    if result.returncode != 0 or len(result.stdout) < 100:
        return None

    html = result.stdout
    title_match = __import__('re').search(r'<title[^>]*>([^<]+)</title>', html, __import__('re').IGNORECASE)
    title = title_match.group(1).strip() if title_match else ''

    text = __import__('re').sub(r'<script[^>]*>.*?</script>', '', html, flags=__import__('re').DOTALL | __import__('re').IGNORECASE)
    text = __import__('re').sub(r'<style[^>]*>.*?</style>', '', text, flags=__import__('re').DOTALL | __import__('re').IGNORECASE)
    text = __import__('re').sub(r'<[^>]+>', ' ', text)
    text = __import__('re').sub(r'\s+', ' ', text).strip()

    if title:
        return f"# {title}\n\nSource: {url}\n\n{text}"
    return f"Source: {url}\n\n{text}"


def convert_file_to_text(file_path):
    """使用 markitdown 转换文档为文本"""
    try:
        result = subprocess.run(
            ['markitdown', str(file_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and len(result.stdout) > 50:
            return result.stdout
    except Exception:
        pass

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def main():
    if len(sys.argv) < 2:
        print("用法: python3 main.py <输入路径或URL>", file=sys.stderr)
        print("")
        print("支持的内容源:")
        print("  网页:      https://...（含 300+ 付费网站自动绕过）")
        print("  微信公众号: https://mp.weixin.qq.com/s/...")
        print("  YouTube:   https://youtube.com/watch?v=...")
        print("  播客:      https://xiaoyuzhoufm.com/... 等")
        print("  X/Twitter: https://x.com/...（文章/用户/搜索）")
        print("  搜索:      任意关键词")
        print("  文件:      .epub .pdf .txt .md .docx .pptx .xlsx 等")
        print("")
        print(f"环境变量 COLLECTOR_DIR 指定输出目录（默认: ~/CollectorOutput）")
        sys.exit(1)

    input_arg = sys.argv[1]
    input_type = detect_input_type(input_arg)
    output_dir = get_output_dir()
    proxy = get_proxy()

    print(f"📋 检测到输入类型: {input_type}")
    print(f"📁 输出目录: {output_dir}")
    print()

    # ── EPUB 电子书 ──
    if input_type == 'epub':
        epub_path = Path(input_arg).expanduser()
        print(f"📚 处理 EPUB: {epub_path.name}")
        content = extract_epub_to_txt(epub_path)
        print(f"✅ 文本提取完成")
        save_content(content, 'epub', epub_path.stem, str(epub_path))

    # ── 本地文档（PDF/TXT/MD） ──
    elif input_type == 'document':
        doc_path = Path(input_arg).expanduser()
        print(f"📄 处理文档: {doc_path.name}")
        content = convert_file_to_text(doc_path)
        save_content(content, 'document', doc_path.stem, str(doc_path))

    # ── Office 文档 ──
    elif input_type == 'office':
        doc_path = Path(input_arg).expanduser()
        print(f"📊 处理 Office: {doc_path.name}")
        content = convert_file_to_text(doc_path)
        save_content(content, 'office', doc_path.stem, str(doc_path))

    # ── 播客（小宇宙/喜马拉雅/B站） ──
    elif input_type == 'podcast':
        # 检查 API 凭据
        api_key = os.getenv('GETNOTE_API_KEY')
        client_id = os.getenv('GETNOTE_CLIENT_ID')
        if not api_key or not client_id:
            print("❌ Get笔记API凭据未配置", file=sys.stderr)
            print("   请设置环境变量: export GETNOTE_API_KEY=... export GETNOTE_CLIENT_ID=...", file=sys.stderr)
            sys.exit(1)

        print(f"🎙️ 处理播客/视频: {input_arg}")
        print("   通过 Get笔记 API 获取转写（可能需要 2-5 分钟）...")

        script = os.path.join(os.path.dirname(__file__), 'scripts',
                              'get_podcast_transcript.py')
        result = subprocess.run(
            ['python3', script, input_arg],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"❌ 获取转写失败: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        try:
            data = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print(f"❌ 解析输出失败: {result.stdout}", file=sys.stderr)
            sys.exit(1)

        with open(data['txt_path'], 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ 转写完成: {data['title']} ({data['content_length']} 字符)")
        save_content(content, 'podcast', data['title'], input_arg)

    # ── X/Twitter ──
    elif input_type in ('x_twitter_article', 'x_twitter_user', 'x_twitter_search', 'x_twitter_status'):
        print(f"🐦 处理 X/Twitter: {input_arg}")

        opencli_path = resolve_opencli_path()

        # 根据类型选择 OpenCLI 命令
        # --window background: 避免弹出前景浏览器窗口
        # --keep-tab false: 命令执行后立即释放 tab lease，防止标签组堆积
        opencli_flags = ['--window', 'background', '--keep-tab', 'false']
        if input_type == 'x_twitter_article':
            cmd = [opencli_path, 'twitter', 'article', input_arg] + opencli_flags
        elif input_type == 'x_twitter_status':
            # 单条推文：提取 tweet ID 给 opencli twitter thread
            tweet_id = input_arg.split('/status/')[1].split('?')[0].split('/')[0]
            cmd = [opencli_path, 'twitter', 'thread', tweet_id] + opencli_flags
        elif input_type == 'x_twitter_user':
            # 从 URL 提取用户名
            username = input_arg.split('x.com/')[1].split('/')[0].split('?')[0]
            cmd = [opencli_path, 'twitter', 'tweets', username] + opencli_flags
        else:  # x_twitter_search
            # 从 URL 提取搜索词
            try:
                query_part = input_arg.split('?')[1]
                search_term = None
                for param in query_part.split('&'):
                    if param.startswith('q='):
                        search_term = param[2:]
                        break
                if not search_term:
                    search_term = input_arg.split('search=')[1].split('&')[0]
            except Exception:
                search_term = input_arg
            cmd = [opencli_path, 'twitter', 'search', search_term] + opencli_flags

        result = run_opencli_cmd(cmd, input_arg, allow_fallback=False)

        content = result.stdout.decode('utf-8', errors='replace').strip()

        if result.returncode != 0 or not content:
            stderr_decoded = result.stderr.decode('utf-8', errors='replace')
            print("❌ OpenCLI 采集失败", file=sys.stderr)
            print("可能原因：", file=sys.stderr)
            print("1. Chrome 未开启远程调试端口 → 运行 opencli doctor 检查", file=sys.stderr)
            print("2. Twitter/X 未登录 → 打开 chrome 确认登录状态", file=sys.stderr)
            print("3. 文章不存在或权限不足 → 检查 URL 是否正确", file=sys.stderr)
            if stderr_decoded.strip():
                print(f"原始错误：{stderr_decoded.strip()[:200]}", file=sys.stderr)
            sys.exit(1)

        # 优先从 frontmatter 的 title 字段读取原标题
        title = None
        for line in content.split('\n')[:20]:
            m = re.match(r'^title:\s*["\']?(.+?)["\']?\s*$', line.strip())
            if m:
                title = m.group(1).strip().strip('"').strip("'")
                break
        if not title:
            title = input_arg.split('/')[-1] or 'x_post'
            first_line = content.split('\n')[0].strip()
            if first_line and len(first_line) < 100:
                title = first_line.lstrip('#').strip()

        print(f"✅ 内容已获取: {len(content)} 字符")
        save_content(content, 'x_twitter', title, input_arg)

    # ── YouTube ──
    elif input_type == 'youtube':
        print(f"🎬 处理 YouTube: {input_arg}")
        print("   注：YouTube 视频字幕提取需要额外工具，当前保存链接引用。")
        video_id = input_arg.split('=')[-1][:30] if '=' in input_arg else 'youtube_video'
        content = f"YouTube URL: {input_arg}\n\n"
        content += "（视频内容需通过 yt-dlp 等工具提取字幕，当前仅保存链接）"
        save_content(content, 'youtube', f"youtube_{video_id}", input_arg)

    # ── 微信公众号 ──
    elif input_type == 'weixin':
        print(f"💬 微信公众号: {input_arg}")
        print("   微信文章需通过 MCP 工具 read_weixin_article 获取内容。")
        print("   请通过 OpenClaw 技能触发，采集的内容会自动保存。")
        content = f"微信公众号文章\nURL: {input_arg}\n\n（内容需通过 MCP 工具获取后保存）"
        save_content(content, 'weixin', 'weixin_article', input_arg)

    # ── 普通网页（含付费墙绕过） ──
    elif input_type == 'url':
        print(f"🌐 处理 URL: {input_arg}")

        # 按需检查海外代理
        if is_overseas_url(input_arg) and proxy:
            print(f"   检测为海外网站，检查代理端口 {proxy}...")
            if not check_proxy_connectivity(proxy):
                print(f"❌ 海外代理端口不可用，采集海外网站会失败", file=sys.stderr)
                print(f"   请确认代理服务已启动（默认端口 127.0.0.1:6696）", file=sys.stderr)
                sys.exit(1)
            print(f"   代理可用，使用代理 {proxy} 采集...")

        print("   通过付费墙绕过获取内容...")

        fetch_script = os.path.join(os.path.dirname(__file__), 'scripts',
                                    'fetch_url.sh')
        cmd = ['bash', fetch_script, input_arg]
        if proxy and is_overseas_url(input_arg):
            cmd.append(proxy)
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120
        )

        content = result.stdout.strip()

        if result.returncode != 0 or not content:
            stderr = result.stderr.strip()
            if 'ARCHIVE_CAPTCHA' in stderr or not content:
                print("   ⚠️ 付费墙绕过不可用，使用直接抓取...")
                content = fetch_url_fallback(input_arg, proxy)
                if not content:
                    print(f"❌ 获取网页失败", file=sys.stderr)
                    if stderr:
                        print(f"   {stderr}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"❌ 获取网页失败: {stderr}", file=sys.stderr)
                sys.exit(1)

        # 优先从 frontmatter 的 title 字段读取原标题
        title = None
        for line in content.split('\n')[:20]:
            m = re.match(r'^title:\s*["\']?(.+?)["\']?\s*$', line.strip())
            if m:
                title = m.group(1).strip().strip('"').strip("'")
                break
        if not title:
            title = 'webpage'
            for line in content.split('\n')[:10]:
                line = line.strip().lstrip('#').strip()
                if line and len(line) < 100 and line != input_arg:
                    title = line
                    break

        print(f"✅ 网页内容已获取: {len(content)} 字符")
        save_content(content, 'webpage', title, input_arg)

    # ── 图片 ──
    elif input_type == 'image':
        file_path = Path(input_arg).expanduser()
        print(f"🖼️ 处理图片: {file_path.name}")
        content = convert_file_to_text(str(file_path))
        save_content(content, 'image', file_path.stem, str(file_path))

    # ── 音频 ──
    elif input_type == 'audio':
        file_path = Path(input_arg).expanduser()
        print(f"🔊 处理音频: {file_path.name}")
        content = convert_file_to_text(str(file_path))
        save_content(content, 'audio', file_path.stem, str(file_path))

    # ── ZIP 压缩包 ──
    elif input_type == 'zip':
        import zipfile
        zip_path = Path(input_arg).expanduser()
        print(f"📦 处理 ZIP: {zip_path.name}")
        extract_dir = tempfile.mkdtemp(prefix='zip_extract_')
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            # 安全校验：防止 Zip Slip 攻击（路径遍历）
            for member in zf.namelist():
                member_path = Path(extract_dir, member)
                try:
                    resolved = member_path.resolve()
                    if not resolved.startswith(Path(extract_dir).resolve()):
                        print(f"⚠️ 跳过非法路径: {member}", file=sys.stderr)
                        continue
                except (OSError, ValueError):
                    print(f"⚠️ 跳过非法路径: {member}", file=sys.stderr)
                    continue
                member_path.parent.mkdir(parents=True, exist_ok=True)
                zf.extract(member, extract_dir)
        content = f"ZIP 压缩包解压到: {extract_dir}\n原始文件: {zip_path.name}\n\n"
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                content += f"  {os.path.join(root, f)}\n"
        save_content(content, 'zip', zip_path.stem, str(zip_path))

    # ── 搜索关键词（暂不支持） ──
    elif input_type == 'search':
        print(f"🔍 搜索关键词: {input_arg}")
        print("   注：搜索功能暂不支持。")
        print("   替代方案：先通过 WebSearch 获取结果，手动保存到文件后再采集。")
        sys.exit(1)

    else:
        print(f"❌ 不支持的输入类型: {input_type}", file=sys.stderr)
        print("   支持的格式：epub/pdf/txt/md/docx/pptx/xlsx/jpg/png/mp3/wav/zip", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
