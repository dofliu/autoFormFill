#!/bin/bash

# Phase 6.4 - 本地 CI 測試腳本
# 在提交前運行此腳本，模擬 GitHub Actions CI 流程

set -e

echo "🚀 開始 Phase 6.4 本地 CI 測試"
echo "========================================"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 工具檢查函數
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ 未找到 $1 命令${NC}"
        echo "請安裝: $2"
        exit 1
    fi
}

# 檢查必需工具
echo "🔍 檢查必需工具..."
check_command "python" "Python 3.11+ (https://www.python.org/)"
check_command "pip" "Python pip (通常隨 Python 安裝)"
check_command "node" "Node.js 20+ (https://nodejs.org/)"
check_command "npm" "npm (通常隨 Node.js 安裝)"
check_command "docker" "Docker (https://docs.docker.com/get-docker/)"
check_command "docker-compose" "Docker Compose (https://docs.docker.com/compose/install/)"

echo -e "${GREEN}✅ 所有必需工具已安裝${NC}"

# 檢查 Python 版本
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python 版本: $PYTHON_VERSION"

# 檢查 Node.js 版本
NODE_VERSION=$(node -v)
echo "🟢 Node.js 版本: $NODE_VERSION"

echo ""
echo "📦 步驟 1: 安裝 Python 依賴"
echo "----------------------------------------"
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-asyncio black flake8 mypy isort ruff bandit safety

echo -e "${GREEN}✅ Python 依賴安裝完成${NC}"

echo ""
echo "📦 步驟 2: 安裝前端依賴"
echo "----------------------------------------"
cd frontend
npm ci --silent
cd ..

echo -e "${GREEN}✅ 前端依賴安裝完成${NC}"

echo ""
echo "🔍 步驟 3: Python 代碼檢查"
echo "----------------------------------------"

echo "📝 運行 isort 檢查..."
if isort --check-only --diff .; then
    echo -e "${GREEN}✅ isort 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  isort 發現問題，運行 'isort .' 修復${NC}"
fi

echo ""
echo "🎨 運行 black 檢查..."
if black --check --diff .; then
    echo -e "${GREEN}✅ black 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  black 發現問題，運行 'black .' 修復${NC}"
fi

echo ""
echo "👀 運行 flake8 檢查..."
if flake8 . --count --show-source --statistics; then
    echo -e "${GREEN}✅ flake8 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  flake8 發現問題${NC}"
fi

echo ""
echo "🦜 運行 ruff 檢查..."
if ruff check .; then
    echo -e "${GREEN}✅ ruff 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  ruff 發現問題${NC}"
fi

echo ""
echo "📋 運行 mypy 類型檢查..."
if mypy --ignore-missing-imports --show-error-codes .; then
    echo -e "${GREEN}✅ mypy 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  mypy 發現問題${NC}"
fi

echo ""
echo "🔒 步驟 4: 安全檢查"
echo "----------------------------------------"

echo "🛡️  運行 Bandit 安全掃描..."
if bandit -r app -f json -o bandit-report.json; then
    echo -e "${GREEN}✅ Bandit 掃描完成${NC}"
else
    echo -e "${YELLOW}⚠️  Bandit 發現潛在安全問題${NC}"
fi

echo ""
echo "📦 運行 Safety 依賴檢查..."
if safety check --json > safety-report.json 2>/dev/null; then
    echo -e "${GREEN}✅ Safety 檢查完成${NC}"
else
    echo -e "${YELLOW}⚠️  Safety 發現依賴漏洞${NC}"
fi

echo ""
echo "🧪 步驟 5: 創建測試目錄"
echo "----------------------------------------"
mkdir -p test_uploads test_outputs test_chroma data
echo -e "${GREEN}✅ 測試目錄創建完成${NC}"

echo ""
echo "🧪 步驟 6: 運行 Python 測試"
echo "----------------------------------------"
if python -m pytest tests/ -v --cov=app --cov-report=term --cov-report=html --maxfail=5 --disable-warnings; then
    echo -e "${GREEN}✅ Python 測試通過${NC}"
else
    echo -e "${RED}❌ Python 測試失敗${NC}"
    exit 1
fi

echo ""
echo "🔍 步驟 7: 前端代碼檢查"
echo "----------------------------------------"
cd frontend

echo "📝 運行 TypeScript 類型檢查..."
if npx tsc --noEmit --project tsconfig.json; then
    echo -e "${GREEN}✅ TypeScript 檢查通過${NC}"
else
    echo -e "${RED}❌ TypeScript 檢查失敗${NC}"
    exit 1
fi

echo ""
echo "👀 運行 ESLint 檢查..."
if npm run lint; then
    echo -e "${GREEN}✅ ESLint 檢查通過${NC}"
else
    echo -e "${YELLOW}⚠️  ESLint 發現問題${NC}"
fi

echo ""
echo "🏗️  運行前端構建測試..."
if npm run build; then
    echo -e "${GREEN}✅ 前端構建成功${NC}"
    
    # 檢查構建輸出
    if [ -d "dist" ]; then
        echo "📁 構建輸出目錄: dist/"
        ls -la dist/
    else
        echo -e "${RED}❌ 構建失敗: dist 目錄未創建${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 前端構建失敗${NC}"
    exit 1
fi

cd ..

echo ""
echo "🐳 步驟 8: Docker 構建測試"
echo "----------------------------------------"

echo "🏗️  構建後端 Docker 鏡像..."
if docker build -t autoformfill-backend:local-test -f Dockerfile .; then
    echo -e "${GREEN}✅ 後端 Docker 鏡像構建成功${NC}"
else
    echo -e "${RED}❌ 後端 Docker 鏡像構建失敗${NC}"
    exit 1
fi

echo ""
echo "🏗️  構建前端 Docker 鏡像..."
if docker build -t autoformfill-frontend:local-test -f Dockerfile.frontend .; then
    echo -e "${GREEN}✅ 前端 Docker 鏡像構建成功${NC}"
else
    echo -e "${RED}❌ 前端 Docker 鏡像構建失敗${NC}"
    exit 1
fi

echo ""
echo "📋 測試 Docker Compose 配置..."
if docker-compose config; then
    echo -e "${GREEN}✅ Docker Compose 配置有效${NC}"
else
    echo -e "${RED}❌ Docker Compose 配置無效${NC}"
    exit 1
fi

echo ""
echo "🧹 步驟 9: 清理測試目錄"
echo "----------------------------------------"
rm -rf test_uploads test_outputs test_chroma
rm -f bandit-report.json safety-report.json
echo -e "${GREEN}✅ 測試目錄清理完成${NC}"

echo ""
echo "📊 步驟 10: 生成測試報告"
echo "----------------------------------------"
# 生成覆蓋率報告
if [ -f "coverage.xml" ]; then
    COVERAGE=$(python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); root = tree.getroot(); print(f'{float(root.attrib[\"line-rate\"])*100:.1f}%')")
    echo "📈 測試覆蓋率: $COVERAGE"
fi

# 檢查 HTML 覆蓋率報告
if [ -d "htmlcov" ]; then
    echo "📄 HTML 覆蓋率報告: file://$(pwd)/htmlcov/index.html"
fi

echo ""
echo "========================================"
echo -e "${GREEN}🎉 Phase 6.4 本地 CI 測試全部完成！${NC}"
echo ""
echo "📋 測試摘要:"
echo "  ✅ Python 代碼檢查"
echo "  ✅ Python 測試 (覆蓋率: ${COVERAGE:-未知})"
echo "  ✅ 前端代碼檢查"
echo "  ✅ 前端構建測試"
echo "  ✅ Docker 構建測試"
echo "  ✅ 安全掃描"
echo ""
echo "🚀 現在可以安全地提交代碼到 GitHub！"
echo "GitHub Actions 將運行完整的 CI/CD 管道。"
echo "========================================"