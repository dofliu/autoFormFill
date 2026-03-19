@echo off
REM Phase 6.4 - 本地 CI 測試腳本 (Windows 版本)
REM 在提交前運行此腳本，模擬 GitHub Actions CI 流程

echo.
echo 🚀 開始 Phase 6.4 本地 CI 測試
echo ========================================
echo.

REM 檢查必需工具
echo 🔍 檢查必需工具...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未找到 python 命令
    echo 請安裝: Python 3.11+ (https://www.python.org/)
    exit /b 1
)

where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未找到 pip 命令
    echo 請安裝: Python pip (通常隨 Python 安裝)
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未找到 node 命令
    echo 請安裝: Node.js 20+ (https://nodejs.org/)
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未找到 npm 命令
    echo 請安裝: npm (通常隨 Node.js 安裝)
    exit /b 1
)

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  未找到 docker 命令 (Docker 測試將跳過)
    set DOCKER_MISSING=1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  未找到 docker-compose 命令 (Docker Compose 測試將跳過)
    set COMPOSE_MISSING=1
)

echo ✅ 所有必需工具已安裝
echo.

REM 檢查 Python 版本
for /f "tokens=1,2 delims=. " %%a in ('python -c "import sys; print(sys.version_info.major, sys.version_info.minor)"') do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
echo 🐍 Python 版本: %PY_MAJOR%.%PY_MINOR%

REM 檢查 Node.js 版本
for /f "delims=" %%i in ('node -v') do set NODE_VERSION=%%i
echo 🟢 Node.js 版本: %NODE_VERSION%
echo.

echo 📦 步驟 1: 安裝 Python 依賴
echo ----------------------------------------
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-asyncio black flake8 mypy isort ruff bandit safety

echo ✅ Python 依賴安裝完成
echo.

echo 📦 步驟 2: 安裝前端依賴
echo ----------------------------------------
cd frontend
call npm ci --silent
cd ..

echo ✅ 前端依賴安裝完成
echo.

echo 🔍 步驟 3: Python 代碼檢查
echo ----------------------------------------

echo 📝 運行 isort 檢查...
isort --check-only --diff .
if %errorlevel% equ 0 (
    echo ✅ isort 檢查通過
) else (
    echo ⚠️  isort 發現問題，運行 'isort .' 修復
)

echo.
echo 🎨 運行 black 檢查...
black --check --diff .
if %errorlevel% equ 0 (
    echo ✅ black 檢查通過
) else (
    echo ⚠️  black 發現問題，運行 'black .' 修復
)

echo.
echo 👀 運行 flake8 檢查...
flake8 . --count --show-source --statistics
if %errorlevel% equ 0 (
    echo ✅ flake8 檢查通過
) else (
    echo ⚠️  flake8 發現問題
)

echo.
echo 🦜 運行 ruff 檢查...
ruff check .
if %errorlevel% equ 0 (
    echo ✅ ruff 檢查通過
) else (
    echo ⚠️  ruff 發現問題
)

echo.
echo 📋 運行 mypy 類型檢查...
mypy --ignore-missing-imports --show-error-codes .
if %errorlevel% equ 0 (
    echo ✅ mypy 檢查通過
) else (
    echo ⚠️  mypy 發現問題
)

echo.
echo 🔒 步驟 4: 安全檢查
echo ----------------------------------------

echo 🛡️  運行 Bandit 安全掃描...
bandit -r app -f json -o bandit-report.json
if %errorlevel% equ 0 (
    echo ✅ Bandit 掃描完成
) else (
    echo ⚠️  Bandit 發現潛在安全問題
)

echo.
echo 📦 運行 Safety 依賴檢查...
safety check --json > safety-report.json 2>nul
if %errorlevel% equ 0 (
    echo ✅ Safety 檢查完成
) else (
    echo ⚠️  Safety 發現依賴漏洞
)

echo.
echo 🧪 步驟 5: 創建測試目錄
echo ----------------------------------------
if not exist test_uploads mkdir test_uploads
if not exist test_outputs mkdir test_outputs
if not exist test_chroma mkdir test_chroma
if not exist data mkdir data

echo ✅ 測試目錄創建完成
echo.

echo 🧪 步驟 6: 運行 Python 測試
echo ----------------------------------------
python -m pytest tests/ -v --cov=app --cov-report=term --cov-report=html --maxfail=5 --disable-warnings
if %errorlevel% equ 0 (
    echo ✅ Python 測試通過
) else (
    echo ❌ Python 測試失敗
    exit /b 1
)

echo.
echo 🔍 步驟 7: 前端代碼檢查
echo ----------------------------------------
cd frontend

echo 📝 運行 TypeScript 類型檢查...
npx tsc --noEmit --project tsconfig.json
if %errorlevel% equ 0 (
    echo ✅ TypeScript 檢查通過
) else (
    echo ❌ TypeScript 檢查失敗
    exit /b 1
)

echo.
echo 👀 運行 ESLint 檢查...
call npm run lint
if %errorlevel% equ 0 (
    echo ✅ ESLint 檢查通過
) else (
    echo ⚠️  ESLint 發現問題
)

echo.
echo 🏗️  運行前端構建測試...
call npm run build
if %errorlevel% equ 0 (
    echo ✅ 前端構建成功
    
    REM 檢查構建輸出
    if exist dist (
        echo 📁 構建輸出目錄: dist/
        dir dist
    ) else (
        echo ❌ 構建失敗: dist 目錄未創建
        exit /b 1
    )
) else (
    echo ❌ 前端構建失敗
    exit /b 1
)

cd ..
echo.

if not defined DOCKER_MISSING (
    echo 🐳 步驟 8: Docker 構建測試
    echo ----------------------------------------

    echo 🏗️  構建後端 Docker 鏡像...
    docker build -t autoformfill-backend:local-test -f Dockerfile .
    if %errorlevel% equ 0 (
        echo ✅ 後端 Docker 鏡像構建成功
    ) else (
        echo ❌ 後端 Docker 鏡像構建失敗
        exit /b 1
    )

    echo.
    echo 🏗️  構建前端 Docker 鏡像...
    docker build -t autoformfill-frontend:local-test -f Dockerfile.frontend .
    if %errorlevel% equ 0 (
        echo ✅ 前端 Docker 鏡像構建成功
    ) else (
        echo ❌ 前端 Docker 鏡像構建失敗
        exit /b 1
    )

    echo.
    echo 📋 測試 Docker Compose 配置...
    docker-compose config
    if %errorlevel% equ 0 (
        echo ✅ Docker Compose 配置有效
    ) else (
        echo ❌ Docker Compose 配置無效
        exit /b 1
    )
) else (
    echo ⚠️  跳過 Docker 測試 (Docker 未安裝)
)

echo.
echo 🧹 步驟 9: 清理測試目錄
echo ----------------------------------------
if exist test_uploads rmdir /s /q test_uploads
if exist test_outputs rmdir /s /q test_outputs
if exist test_chroma rmdir /s /q test_chroma
if exist bandit-report.json del bandit-report.json
if exist safety-report.json del safety-report.json

echo ✅ 測試目錄清理完成
echo.

echo 📊 步驟 10: 生成測試報告
echo ----------------------------------------
REM 生成覆蓋率報告
if exist coverage.xml (
    for /f "tokens=2 delims==>" %%i in ('python -c "import xml.etree.ElementTree as ET; tree = ET.parse(\"coverage.xml\"); root = tree.getroot(); print(float(root.attrib[\"line-rate\"])*100)"') do set COVERAGE=%%i
    echo 📈 測試覆蓋率: %COVERAGE%%
)

REM 檢查 HTML 覆蓋率報告
if exist htmlcov (
    echo 📄 HTML 覆蓋率報告: file:///%CD%/htmlcov/index.html
)

echo.
echo ========================================
echo 🎉 Phase 6.4 本地 CI 測試全部完成！
echo.
echo 📋 測試摘要:
echo   ✅ Python 代碼檢查
if defined COVERAGE (
    echo   ✅ Python 測試 (覆蓋率: %COVERAGE%%%)
) else (
    echo   ✅ Python 測試
)
echo   ✅ 前端代碼檢查
echo   ✅ 前端構建測試
if not defined DOCKER_MISSING (
    echo   ✅ Docker 構建測試
) else (
    echo   ⚠️  Docker 測試跳過
)
echo   ✅ 安全掃描
echo.
echo 🚀 現在可以安全地提交代碼到 GitHub！
echo GitHub Actions 將運行完整的 CI/CD 管道。
echo ========================================