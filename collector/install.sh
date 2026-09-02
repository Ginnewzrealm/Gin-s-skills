#!/bin/bash

# caijiji Skill Installer
# 自动安装所有依赖并配置环境

set -e  # 遇到错误立即退出

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="caijiji"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  采集器 安装程序${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查 Python 版本
echo -e "${YELLOW}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ Python 版本过低（当前 $PYTHON_VERSION，需要 3.9+）${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION${NC}"

# 2. 检查并克隆 wexin-read-mcp
echo ""
echo -e "${YELLOW}[2/5] 安装 MCP 服务器...${NC}"
MCP_DIR="$SKILL_DIR/wexin-read-mcp"

if [ -d "$MCP_DIR" ]; then
    echo -e "${GREEN}✅ MCP 服务器已存在${NC}"
else
    echo "正在克隆 wexin-read-mcp..."
    git clone https://github.com/Bwkyd/wexin-read-mcp.git "$MCP_DIR"
    echo -e "${GREEN}✅ MCP 服务器克隆完成${NC}"
fi

# 3. 安装 Python 依赖
echo ""
echo -e "${YELLOW}[3/5] 安装 Python 依赖...${NC}"

# 安装 MCP 服务器依赖
if [ -f "$MCP_DIR/requirements.txt" ]; then
    echo "安装 MCP 依赖..."
    pip3 install -r "$MCP_DIR/requirements.txt" --break-system-packages -q
    echo -e "${GREEN}✅ MCP 依赖安装完成${NC}"
fi

# 安装 Skill 依赖（包括 markitdown）
if [ -f "$SKILL_DIR/requirements.txt" ]; then
    echo "安装 Skill 依赖..."
    pip3 install -r "$SKILL_DIR/requirements.txt" --break-system-packages -q
    echo -e "${GREEN}✅ Skill 依赖安装完成${NC}"
fi

# 4. 安装 url-md（微信 MCP 依赖的抓取引擎）
echo ""
echo -e "${YELLOW}[4/5] 安装 url-md 抓取引擎...${NC}"

# 检查 url-md 是否已安装
_url_md_check() {
  command -v url-md &> /dev/null || [ -x "$HOME/.url-md/bin/url-md" ]
}

if _url_md_check; then
    echo -e "${GREEN}✅ url-md 已安装${NC}"
else
    echo "正在安装 url-md..."
    if ! curl -fsSL https://raw.githubusercontent.com/Bwkyd/url-md/main/install.sh | bash; then
        echo -e "${RED}❌ url-md 安装失败${NC}"
        exit 1
    fi
    # 将 url-md 添加到当前 shell 的 PATH（本次安装生效）
    export PATH="$HOME/.url-md/bin:$PATH"
    if ! _url_md_check; then
        echo -e "${RED}❌ url-md 安装后仍不可用，请手动检查 ~/.url-md/bin${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ url-md 安装完成${NC}"
    echo ""
    echo "请将以下行添加到 ~/.zshrc（持久化 PATH）："
    echo -e "${GREEN}  export PATH=\"\$HOME/.url-md/bin:\$PATH\"${NC}"
fi

# 5. 配置指导
echo ""
echo -e "${YELLOW}[5/5] 配置指导${NC}"
echo ""

OPENCLAW_CONFIG="$HOME/.config/openclaw/config.json"
CONFIG_SNIPPET="    \"weixin-reader\": {
      \"command\": \"python\",
      \"args\": [
        \"$MCP_DIR/server.py\"
      ]
    }"

echo -e "${BLUE}📝 下一步：配置 MCP 服务器${NC}"
echo ""
echo "编辑 OpenClaw 配置文件："
echo "  $OPENCLAW_CONFIG"
echo ""
echo "在 \"mcpServers\" 中添加："
echo -e "${GREEN}$CONFIG_SNIPPET${NC}"
echo ""
echo "完整配置示例："
echo -e "${GREEN}{
  \"mcpServers\": {
$CONFIG_SNIPPET
  }
}${NC}"
echo ""

echo ""
echo -e "${BLUE}📝 使用前配置${NC}"
echo ""
echo "设置采集内容输出目录（写入 ~/.zshrc 持久生效）："
echo -e "${GREEN}  export COLLECTOR_DIR=\"\$HOME/CollectorOutput\"${NC}"
echo ""

# 最终检查
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 安装完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "📦 安装位置：$SKILL_DIR"
echo ""
echo "🚀 使用示例："
echo "  采集这篇文章 https://example.com/article"
echo ""
