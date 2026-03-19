# Phase 6.4 - 環境變數管理指南

本文檔說明 AutoFormFill 專案的環境變數配置和管理，專為 Phase 6.4 CI/CD 流程設計。

## 環境變數概覽

AutoFormFill 使用多層環境變數配置：

1. **開發環境** - 本地開發使用 `.env` 文件
2. **測試環境** - CI/CD 測試使用 GitHub Actions Secrets
3. **生產環境** - 部署伺服器使用環境變數或 Docker secrets
4. **CI/CD 環境** - GitHub Actions 工作流專用變數

## 變數清單

### 必需變數

| 變數名稱 | 描述 | 預設值 | 範例 |
|---------|------|--------|------|
| `GEMINI_API_KEY` | Google Gemini API 金鑰 | (無) | `AIzaSy...` |
| `LLM_PROVIDER` | LLM 提供者 | `gemini` | `gemini`, `openai` |
| `GEMINI_MODEL` | Gemini 模型名稱 | `gemini-2.0-flash` | `gemini-2.0-flash-exp` |
| `GEMINI_EMBEDDING_MODEL` | 嵌入模型 | `text-embedding-004` | `text-embedding-004` |
| `DATABASE_URL` | 資料庫連接字串 | `sqlite+aiosqlite:///./data/smartfill.db` | `postgresql://user:pass@localhost/db` |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目錄 | `/app/data/chroma` | `/data/chroma` |
| `UPLOAD_DIR` | 上傳文件目錄 | `/app/data/uploads` | `/data/uploads` |
| `OUTPUT_DIR` | 輸出文件目錄 | `/app/data/outputs` | `/data/outputs` |

### 可選變數

| 變數名稱 | 描述 | 預設值 | 範例 |
|---------|------|--------|------|
| `AUTH_ENABLED` | 啟用身份驗證 | `False` | `True`, `False` |
| `JWT_SECRET_KEY` | JWT 密鑰 | `CHANGE-ME-IN-PRODUCTION` | `your-secret-key-here` |
| `LOG_LEVEL` | 日誌級別 | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORS_ORIGINS` | CORS 允許的來源 | `*` | `http://localhost:3000,http://localhost:80` |
| `MAX_UPLOAD_SIZE` | 最大上傳大小 (MB) | `100` | `50`, `100`, `200` |
| `SESSION_TIMEOUT` | 會話超時 (分鐘) | `30` | `15`, `30`, `60` |

## 環境配置

### 1. 開發環境

1. 複製環境變數模板：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 文件，填入你的 API 金鑰和其他配置：
   ```bash
   # 使用文字編輯器編輯 .env 文件
   # 或使用命令列：
   echo "GEMINI_API_KEY=your_api_key_here" >> .env
   ```

### 2. Docker 開發環境

使用 Docker Compose 時，環境變數可以通過以下方式設置：

1. **使用 `.env` 文件** (推薦)：
   ```bash
   # docker-compose.yml 會自動讀取同目錄下的 .env 文件
   docker-compose up
   ```

2. **使用環境變數文件**：
   ```bash
   # 指定環境變數文件
   docker-compose --env-file .env.docker up
   ```

3. **直接設置環境變數**：
   ```bash
   export GEMINI_API_KEY=your_key
   docker-compose up
   ```

### 3. 生產環境部署

#### 方法 A：使用環境變數文件

1. 在伺服器上創建 `.env` 文件：
   ```bash
   sudo nano /opt/autoformfill/.env
   ```

2. 設置文件權限：
   ```bash
   sudo chmod 600 /opt/autoformfill/.env
   sudo chown root:root /opt/autoformfill/.env
   ```

#### 方法 B：使用 Docker secrets (更安全)

1. 創建 secrets：
   ```bash
   echo "your_gemini_api_key" | docker secret create gemini_api_key -
   ```

2. 更新 `docker-compose.yml`：
   ```yaml
   services:
     backend:
       secrets:
         - gemini_api_key
       environment:
         GEMINI_API_KEY_FILE: /run/secrets/gemini_api_key
   
   secrets:
     gemini_api_key:
       external: true
   ```

3. 在應用程式中讀取：
   ```python
   import os
   
   # 優先讀取 _FILE 結尾的變數
   api_key = os.getenv('GEMINI_API_KEY')
   if not api_key:
       api_key_file = os.getenv('GEMINI_API_KEY_FILE')
       if api_key_file and os.path.exists(api_key_file):
           with open(api_key_file, 'r') as f:
               api_key = f.read().strip()
   ```

#### 方法 C：使用環境變數 (簡單部署)

```bash
# 設置環境變數
export GEMINI_API_KEY=your_key
export DATABASE_URL=postgresql://user:pass@localhost/autoformfill

# 啟動容器
docker-compose up -d
```

## Phase 6.4 CI/CD 環境變數管理

### GitHub Actions Secrets (必需)

在 GitHub Repository Settings → Secrets and variables → Actions 中設置以下 secrets：

| Secret 名稱 | 描述 | Phase 6.4 用途 |
|------------|------|---------------|
| `GEMINI_API_KEY` | Gemini API 金鑰 | 測試環境執行 LLM 相關測試 |
| `DOCKERHUB_USERNAME` | Docker Hub 用戶名 | 推送 Docker 鏡像到倉庫 |
| `DOCKERHUB_TOKEN` | Docker Hub 訪問令牌 | 認證 Docker 推送操作 |
| `GHCR_TOKEN` | GitHub Container Registry 令牌 | 推送鏡像到 GHCR |

### GitHub Actions Variables (可選)

在 GitHub Repository Settings → Secrets and variables → Actions → Variables 中設置：

| 變數名稱 | 描述 | 預設值 |
|---------|------|--------|
| `PYTHON_VERSION` | Python 測試版本 | `3.11,3.12` |
| `NODE_VERSION` | Node.js 版本 | `20` |
| `DOCKER_REGISTRY` | Docker 鏡像倉庫 | `ghcr.io` |
| `IMAGE_NAME` | 鏡像名稱 | `${{ github.repository }}` |

### CI/CD 專用環境變數

在 CI/CD 工作流中定義的環境變數：

```yaml
# .github/workflows/ci.yml
env:
  CI: true
  PYTHONPATH: ${{ github.workspace }}
  TEST_DATABASE_URL: sqlite+aiosqlite:///./test.db
  TEST_CHROMA_DIR: ./test_chroma
  COVERAGE_THRESHOLD: 80

# .github/workflows/deploy.yml
env:
  DOCKER_BUILDKIT: 1
  COMPOSE_DOCKER_CLI_BUILD: 1
  REGISTRY: ${{ vars.DOCKER_REGISTRY || 'ghcr.io' }}
  IMAGE_NAME: ${{ vars.IMAGE_NAME || github.repository }}
```

### 測試環境變數

在 `.github/workflows/ci.yml` 中設置測試環境變數：

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  DATABASE_URL: sqlite+aiosqlite:///./test.db
```

## 安全最佳實踐

### 1. 不要提交敏感資訊
- 確保 `.env` 在 `.gitignore` 中
- 使用 `.env.example` 作為模板
- 定期檢查 git 歷史中是否有敏感資訊洩漏

### 2. 使用不同的金鑰
- 開發、測試、生產環境使用不同的 API 金鑰
- 定期輪換金鑰
- 設置金鑰使用限制和配額

### 3. 最小權限原則
- 資料庫用戶只具有必要權限
- API 金鑰只具有必要範圍
- 定期審查和撤銷未使用的金鑰

### 4. 監控和日誌
- 記錄環境變數的使用情況
- 監控異常的 API 調用
- 設置金鑰使用警報

## 故障排除

### 常見問題

1. **環境變數未生效**
   ```bash
   # 檢查變數是否設置
   echo $GEMINI_API_KEY
   
   # 檢查 Docker 容器內的環境變數
   docker exec <container_name> env
   ```

2. **權限問題**
   ```bash
   # 檢查文件權限
   ls -la .env
   
   # 正確權限
   -rw------- 1 user user .env  # 只有所有者可讀寫
   ```

3. **變數覆蓋問題**
   ```bash
   # 檢查變數來源優先級
   # 1. Docker Compose env_file
   # 2. Docker Compose environment
   # 3. Shell 環境變數
   # 4. .env 文件
   ```

### 驗證腳本

創建 `scripts/validate_env.py` 來驗證環境變數：

```python
#!/usr/bin/env python3
import os
import sys

REQUIRED_VARS = [
    'GEMINI_API_KEY',
    'LLM_PROVIDER',
    'DATABASE_URL',
]

def validate_environment():
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please set them in your .env file or environment.")
        sys.exit(1)
    
    print("✅ All required environment variables are set.")
    
    # 驗證 API 金鑰格式
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key and not api_key.startswith('AIza'):
        print("⚠️  GEMINI_API_KEY doesn't look like a standard Google API key")
    
    return True

if __name__ == '__main__':
    validate_environment()
```

## 更新日誌

| 日期 | 版本 | 變更說明 |
|------|------|----------|
| 2026-03-13 | 1.0.0 | 初始版本，包含基本環境變數管理 |
| 2026-03-13 | 1.1.0 | 添加 Docker secrets 和安全最佳實踐 |

## 相關文件

- [部署指南](./DEPLOYMENT.md)
- [Docker 配置](./DOCKER_CONFIG.md)
- [API 文檔](./API_DOCUMENTATION.md)