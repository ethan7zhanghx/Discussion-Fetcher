#!/bin/bash

# DiscussionFetcher 启动脚本

set -e  # 遇到错误立即退出

echo "════════════════════════════════════════════════════════════"
echo "  DiscussionFetcher v2.0 - Web Interface Launcher"
echo "════════════════════════════════════════════════════════════"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 未安装${NC}"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境已创建"
fi

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source venv/bin/activate

# 检查并安装依赖
echo ""
echo "检查依赖包..."
if ! pip show flask &> /dev/null; then
    echo -e "${YELLOW}⚠️  依赖包未安装，正在安装...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} 依赖包安装完成"
else
    echo -e "${GREEN}✓${NC} 依赖包已安装"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  .env 文件不存在${NC}"
    if [ -f ".env.example" ]; then
        echo "正在从 .env.example 创建 .env..."
        cp .env.example .env
        echo -e "${GREEN}✓${NC} .env 文件已创建"
        echo -e "${YELLOW}请编辑 .env 文件，填入你的 API 凭证${NC}"
    else
        echo -e "${RED}❌ .env.example 也不存在${NC}"
        echo "请手动创建 .env 文件并配置 API 凭证"
    fi
fi

# 检查数据目录
mkdir -p data/exports data/html_debug

# 检查 cookies（可选）
if [ ! -f "cookies.json" ]; then
    echo ""
    echo -e "${YELLOW}💡 提示: cookies.json 未找到${NC}"
    echo "   如需获取 Reddit 评论，请运行: python3 -m src.reddit_comments guide"
fi

# 启动服务器
echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}启动 Web 服务器...${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "访问地址: http://127.0.0.1:5000"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动 Flask 服务器
python3 web_server.py
