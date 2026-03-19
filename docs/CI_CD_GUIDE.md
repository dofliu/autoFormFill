# Phase 6.4 - CI/CD 指南

本文檔說明 AutoFormFill 專案 Phase 6.4 的持續整合和持續部署流程。

## Phase 6.4 概述

Phase 6.4 實現了完整的 CI/CD 管道，包含：

1. **CI 管道** - 自動化代碼檢查、測試和安全掃描
2. **CD 管道** - 自動化構建、部署和發布
3. **環境管理** - 標準化的環境變數配置

## 架構圖

```
┌─────────────────────────────────────────────────────────┐
│                    Phase 6.4 CI/CD                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │  開發者   │───▶│   Git    │───▶│ GitHub   │         │
│  │          │    │  Push    │    │          │         │
│  └──────────┘    └──────────┘    └──────────┘         │
│                                 │                      │
│  ┌──────────────────────────────┼────────────────────┐ │
│  │      GitHub Actions          │                    │ │
│  │                              ▼                    │ │
│  │  ┌────────────┐    ┌────────────┐    ┌─────────┐ │ │
│  │  │   CI 管道   │───▶│   測試     │───▶│  報告   │ │ │
│  │  │            │    │            │    │         │ │ │
│  │  └────────────┘    └────────────┘    └─────────┘ │ │
│  │         │                      │                  │ │
│  │         ▼                      ▼                  │ │
│  │  ┌────────────┐    ┌────────────┐                │ │
│  │  │   CD 管道   │───▶│   部署     │                │ │
│  │  │            │    │            │                │ │
│  │  └────────────┘    └────────────┘                │ │
│  │         │                      │                  │ │
│  │         ▼                      ▼                  │ │
│  │  ┌────────────┐    ┌────────────┐                │ │
│  │  │  生產環境   │◀───│  鏡像倉庫  │                │ │
│  │  │            │    │            │                │ │
│  │  └────────────┘    └────────────┘                │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## CI 流程

### 觸發條件
- 推送到 `main` 或 `master` 分支
- 拉取請求到 `main` 或 `master` 分支
- 每週一 00:00 UTC 自動運行
- 手動觸發

### CI 工作流步驟

1. **代碼檢查和測試**
   - Python 代碼檢查 (isort, black, flake8, ruff, mypy)
   - Python 測試運行 (pytest with coverage)
   - 前端 TypeScript 類型檢查
   - 前端 ESLint 檢查
   - 前端構建測試

2. **安全掃描**
   - Bandit 安全掃描
   - Safety 依賴漏洞檢查
   - Trivy 漏洞掃描

3. **Docker 構建測試**
   - 構建後端 Docker 鏡像
   - 構建前端 Docker 鏡像
   - Docker Compose 配置測試
   - 容器健康檢查測試

4. **性能測試** (僅在主分支推送時)
   - Locust 性能測試
   - 負載測試報告生成

## CD 流程

### 觸發條件
- 推送到 `main` 或 `master` 分支
- 創建 `v*` 版本標籤
- 發布 GitHub Release
- 手動觸發 (可選擇環境)

### CD 工作流步驟

1. **預部署驗證**
   - 檢查必要文件
   - 驗證 docker-compose 配置
   - 檢查環境變數模板

2. **構建和推送 Docker 鏡像**
   - 構建後端鏡像
   - 構建前端鏡像
   - 推送到 GitHub Container Registry
   - 生成 SBOM (軟體物料清單)

3. **生成部署套件**
   - 創建部署目錄
   - 生成部署腳本
   - 創建監控腳本
   - 創建備份腳本
   - 打包部署套件

4. **部署到環境** (可選)
   - 通過 SSH 部署到伺服器
   - 運行部署腳本
   - 健康檢查驗證

5. **創建 GitHub Release** (僅版本標籤時)
   - 自動生成發布說明
   - 附加部署套件

## 環境配置

### GitHub Secrets 設置

在 Repository Settings → Secrets and variables → Actions 中設置以下 secrets：

| Secret 名稱 | 描述 | 必需 |
|------------|------|------|
| `GEMINI_API_KEY` | Gemini API 金鑰 (用於測試) | 是 |
| `SSH_PRIVATE_KEY` | 部署伺服器 SSH 私鑰 | 否 |
| `DEPLOY_HOST` | 部署伺服器地址 | 否 |
| `DEPLOY_USER` | 部署用戶名 | 否 |
| `DEPLOY_PATH` | 部署路徑 | 否 |

### 環境變數

CI/CD 流程使用以下環境變數：

| 變數名稱 | 描述 | 預設值 |
|---------|------|--------|
| `GEMINI_API_KEY` | Gemini API 金鑰 | 從 secrets 讀取 |
| `DATABASE_URL` | 測試資料庫 URL | `sqlite+aiosqlite:///./test.db` |
| `AUTH_ENABLED` | 啟用身份驗證 | `False` |
| `REGISTRY` | Docker 鏡像倉庫 | `ghcr.io` |
| `IMAGE_NAME` | 鏡像名稱 | `github.repository` |

## 部署腳本

CD 流程生成以下部署腳本：

### `deploy.sh`
主部署腳本，執行以下操作：
1. 檢查環境變數
2. 登錄 Docker 倉庫
3. 拉取最新鏡像
4. 停止舊容器
5. 啟動新容器
6. 運行健康檢查

### `update.sh`
更新腳本，執行以下操作：
1. 拉取最新代碼
2. 運行 `deploy.sh`

### `rollback.sh`
回滾腳本，執行以下操作：
1. 檢查指定版本標籤
2. 切換到該版本
3. 運行部署

### `monitor.sh`
監控腳本，顯示：
1. 服務狀態
2. 資源使用情況
3. 日誌
4. 磁碟使用情況
5. 健康檢查狀態

### `backup.sh`
備份腳本，備份：
1. 資料庫
2. 上傳文件
3. 輸出文件

## 本地開發

### 運行 CI 檢查
```bash
# 安裝測試依賴
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy isort ruff

# 運行代碼檢查
black --check .
flake8 .
mypy --ignore-missing-imports .
ruff check .

# 運行測試
python -m pytest tests/ -v --cov=app
```

### 運行前端檢查
```bash
cd frontend

# 安裝依賴
npm ci

# 類型檢查
npx tsc --noEmit

# 代碼檢查
npm run lint

# 構建測試
npm run build
```

## 故障排除

### CI 失敗常見原因

1. **測試失敗**
   ```bash
   # 本地運行測試
   python -m pytest tests/ -v
   
   # 查看具體錯誤
   python -m pytest tests/test_file.py::test_function -v
   ```

2. **代碼檢查失敗**
   ```bash
   # 自動修復格式
   black .
   isort .
   
   # 檢查具體問題
   flake8 . --count --show-source --statistics
   ```

3. **Docker 構建失敗**
   ```bash
   # 本地構建測試
   docker build -t autoformfill-backend:test -f Dockerfile .
   docker build -t autoformfill-frontend:test -f Dockerfile.frontend .
   ```

### CD 失敗常見原因

1. **環境變數缺失**
   ```bash
   # 檢查環境變數
   echo $GEMINI_API_KEY
   
   # 驗證 .env 文件
   cp .env.example .env
   nano .env
   ```

2. **Docker 登錄失敗**
   ```bash
   # 手動登錄測試
   echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
   ```

3. **部署腳本權限問題**
   ```bash
   # 設置執行權限
   chmod +x *.sh
   
   # 測試運行
   ./deploy.sh --dry-run
   ```

## 最佳實踐

### 1. 提交前本地測試
```bash
# 運行完整的本地檢查
./scripts/local-ci.sh
```

### 2. 小步提交
- 每次提交只做一個小的改動
- 確保測試通過後再提交
- 使用有意義的提交訊息

### 3. 版本標籤
```bash
# 創建版本標籤
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 4. 監控部署
```bash
# 查看部署狀態
./monitor.sh

# 查看日誌
docker-compose logs -f

# 健康檢查
curl http://localhost:8000/health
```

## 進階配置

### 自定義 CI 步驟
編輯 `.github/workflows/ci.yml` 自定義：
- 測試矩陣 (Python 版本、操作系統)
- 緩存策略
- 測試超時設置
- 通知配置

### 自定義 CD 步驟
編輯 `.github/workflows/deploy.yml` 自定義：
- 部署環境
- 部署策略
- 滾動更新配置
- 藍綠部署

### 多環境部署
```yaml
# 在 workflow_dispatch 中配置多環境
inputs:
  environment:
    description: 'Deployment environment'
    required: true
    default: 'staging'
    type: choice
    options:
    - development
    - staging
    - production
```

## 相關文件

- [環境變數管理](./ENVIRONMENT_VARIABLES.md)
- [部署指南](./DEPLOYMENT.md)
- [API 文檔](./API_DOCUMENTATION.md)
- [開發指南](./DEVELOPMENT.md)