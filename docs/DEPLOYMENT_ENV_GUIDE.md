# 環境變數管理指南 - Phase 6.4 CI/CD

本文件說明 AutoFormFill 的完整環境變數管理策略，適用於 CI、CD 及本地開發場景。

---

## 一、工作流程觸發條件

### CI Pipeline (`ci.yml`)
| 觸發條件 | 說明 |
|---------|------|
| `pull_request` to `main/master/develop` | 任何 PR 開啟、更新、重新開啟時自動執行 lint + test |
| `push` to `main/master` | 合併後再次驗證 |
| `workflow_dispatch` | 手動觸發（調試用） |

### CD Pipeline (`deploy.yml`)
| 觸發條件 | 說明 |
|---------|------|
| `push` to `main/master` | 自動 build + push Docker 映像 |
| `push` tag `v*.*.*` | 版本發佈時自動建立 Release |
| `workflow_dispatch` | 手動指定環境部署 |

---

## 二、環境變數分層架構

```
本地開發          測試/CI             生產/CD
─────────         ────────            ─────────
.env              GitHub Secrets      伺服器環境變數
.env.example  ──► GitHub Variables ──► Docker secrets
.env.docker       workflow env vars   docker-compose env
```

---

## 三、必要的 GitHub Secrets 設定

在 **Settings → Secrets and variables → Actions** 中設置：

| Secret 名稱 | 說明 | 必填 |
|------------|------|------|
| `GEMINI_API_KEY` | Google Gemini API 金鑰，供 CI 測試 LLM 功能 | ✅ |
| `DEPLOY_HOST` | 部署伺服器 IP 或域名 | 選填（自動部署用） |
| `DEPLOY_USER` | SSH 登入用戶名 | 選填 |
| `DEPLOY_PATH` | 伺服器上的部署路徑 | 選填 |

---

## 四、CI 測試環境變數 (`ci.yml` env 區塊)

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  DATABASE_URL: sqlite+aiosqlite:///./test.db
  CHROMA_PERSIST_DIR: ./test_chroma
  UPLOAD_DIR: ./test_uploads
  OUTPUT_DIR: ./test_outputs
  AUTH_ENABLED: False
  JWT_SECRET_KEY: test-secret-key-for-ci
  PYTHONPATH: ${{ github.workspace }}
  PYTHONUNBUFFERED: 1
  PYTHONDONTWRITEBYTECODE: 1
```

> **注意**: CI 測試使用獨立的 SQLite 資料庫和測試目錄，不影響生產資料。

---

## 五、CD 部署環境變數 (`deploy.yml` env 區塊)

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  DOCKER_BUILDKIT: 1
  COMPOSE_DOCKER_CLI_BUILD: 1
```

---

## 六、本地開發設置

```bash
# 1. 複製環境模板
cp .env.example .env

# 2. 填入必要設定
# 至少需要設置：
GEMINI_API_KEY=AIzaSy...          # Google AI Studio 取得
LLM_PROVIDER=gemini
DATABASE_URL=sqlite+aiosqlite:///./data/smartfill.db
CHROMA_PERSIST_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
OUTPUT_DIR=./data/outputs
AUTH_ENABLED=False
JWT_SECRET_KEY=local-dev-secret-key

# 3. Docker 開發模式
docker-compose --env-file .env.docker up
```

---

## 七、生產環境部署變數

### 必填變數

| 變數 | 說明 | 範例值 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini API 金鑰 | `AIzaSy...` |
| `DATABASE_URL` | 資料庫連接字串 | `sqlite+aiosqlite:///./data/smartfill.db` |
| `JWT_SECRET_KEY` | JWT 簽名密鑰（生產必須強密鑰） | `openssl rand -hex 32` 生成 |
| `AUTH_ENABLED` | 啟用認證 | `True` |

### 選填變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LOG_LEVEL` | `INFO` | 日誌級別 |
| `CORS_ORIGINS` | `*` | CORS 允許來源 |
| `MAX_UPLOAD_SIZE` | `100` | 最大上傳 MB |
| `SESSION_TIMEOUT` | `30` | 會話超時分鐘 |
| `LLM_PROVIDER` | `gemini` | LLM 提供者 |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini 模型版本 |

---

## 八、安全最佳實踐

1. **永遠不要 commit `.env` 檔**（已在 `.gitignore` 設定）
2. **生產環境** 的 `JWT_SECRET_KEY` 必須使用強隨機值：
   ```bash
   openssl rand -hex 32
   ```
3. **API 金鑰分環境**：開發、測試、生產各用不同金鑰
4. **定期輪換**金鑰，尤其是 JWT secret
5. **最小權限**：資料庫帳號只授予必要操作

---

## 九、故障排除

### CI 測試失敗：GEMINI_API_KEY 未設定
```
Error: GEMINI_API_KEY is not set
```
→ 到 GitHub Settings → Secrets → 添加 `GEMINI_API_KEY`

### Docker build 失敗
```bash
# 本地測試 Docker build
docker build -t autoformfill-backend:local .
docker build -t autoformfill-frontend:local -f Dockerfile.frontend .
```

### 查看容器環境變數
```bash
docker exec <container_name> env | grep -E "(GEMINI|DATABASE|AUTH)"
```

---

**更新時間**: 2026-03-27  
**版本**: Phase 6.4  
**狀態**: ✅ CI 自動觸發 on PR | CD 自動觸發 on push to main
