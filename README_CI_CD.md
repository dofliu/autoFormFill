# Phase 6.4 CI/CD 管道

AutoFormFill 已實現完整的 Phase 6.4 CI/CD 管道，提供自動化的測試、構建和部署流程。

## 🚀 快速開始

### 本地開發測試
```bash
# 運行完整的本地 CI 檢查 (Linux/macOS)
./scripts/test-ci-local.sh

# Windows 用戶
scripts\test-ci-local.bat

# 或手動運行核心測試
cd frontend && npm run lint && npx tsc --noEmit && npm run build
cd .. && black --check . && flake8 . && python -m pytest tests/ -v
```

## 🔧 GitHub Actions CI/CD

### CI 管道 (`ci.yml`)
- **觸發條件**: 每次 PR 或推送時自動運行
- **代碼檢查**: black, isort, flake8, ruff, mypy
- **測試執行**: Python 單元測試 + 前端測試
- **安全掃描**: Bandit, Safety, Trivy
- **Docker 測試**: 鏡像構建和配置測試
- **覆蓋率報告**: 自動生成並上傳到 Codecov

### CD 管道 (`deploy.yml`)
- **觸發條件**: 推送到 main 分支或創建版本標籤
- **自動構建**: 多架構 Docker 鏡像 (amd64, arm64)
- **鏡像推送**: 自動推送到 GitHub Container Registry
- **部署工件**: 生成部署腳本和配置文件
- **SBOM 生成**: 軟體物料清單和安全掃描

## 🏗️ 部署選項

### 1. Docker Compose (推薦)
- **適合**: 中小型應用，單機部署
- **優點**: 簡單快速，易於維護
- **配置**: `docker-compose.yml` + `.env` 文件

### 2. Kubernetes (生產級)
- **適合**: 大型應用，需要水平擴展
- **優點**: 高可用性，自動擴展
- **配置**: 完整的 K8s 部署文件

### 3. 雲平台
- **AWS ECS**: 完全託管的容器服務
- **Google Cloud Run**: 無伺服器容器平台
- **Azure Container Instances**: 快速容器部署

## 🔐 環境變數管理

專案使用分層環境變數管理：

| 環境 | 配置方式 | 用途 |
|------|----------|------|
| **開發環境** | `.env` 文件 | 本地開發和測試 |
| **測試環境** | GitHub Actions Secrets | CI/CD 管道測試 |
| **生產環境** | 伺服器環境變數 / Docker secrets | 正式部署 |

## 📊 監控指標

### CI 管道指標
- **測試通過率**: 100%
- **代碼覆蓋率**: > 80%
- **構建時間**: < 10 分鐘
- **安全漏洞**: 零高風險

### CD 管道指標
- **部署成功率**: 100%
- **部署時間**: < 5 分鐘
- **回滾時間**: < 2 分鐘
- **服務可用性**: 99.9%

## 📚 詳細指南

### 核心文檔
- [部署指南](docs/DEPLOYMENT_GUIDE.md) - 完整部署指南
- [環境變數管理](docs/ENVIRONMENT_VARIABLES.md) - 環境配置詳解
- [Phase 6.4 完成檢查清單](docs/PHASE_6_4_COMPLETION_CHECKLIST.md) - 驗證步驟

### 配置指南
- [CI/CD 指南](docs/CI_CD_GUIDE.md) - 工作流配置說明
- [安全最佳實踐](docs/SECURITY_BEST_PRACTICES.md) - 安全配置建議
- [故障排除指南](docs/TROUBLESHOOTING.md) - 常見問題解決

## 🛠️ 工具集成

### 代碼質量
- **black**: Python 代碼格式化
- **isort**: 導入排序
- **flake8**: 代碼風格檢查
- **mypy**: 靜態類型檢查
- **ruff**: 快速 linting

### 測試框架
- **pytest**: Python 單元測試
- **pytest-cov**: 測試覆蓋率
- **TypeScript**: 前端類型檢查
- **ESLint**: JavaScript 代碼檢查

### 安全掃描
- **bandit**: Python 安全掃描
- **safety**: 依賴漏洞檢查
- **trivy**: 容器漏洞掃描

### 部署工具
- **Docker**: 容器化部署
- **Docker Compose**: 多容器管理
- **GitHub Actions**: 自動化 CI/CD
- **GitHub Container Registry**: 鏡像倉庫

## 🔄 工作流程

### 開發流程
1. 創建功能分支
2. 開發和本地測試
3. 提交更改並推送到 GitHub
4. 創建 Pull Request
5. CI 管道自動運行檢查
6. 代碼審查和合併

### 部署流程
1. 代碼合併到 main 分支
2. CD 管道自動觸發
3. Docker 鏡像構建和推送
4. 部署工件生成
5. 自動或手動部署到目標環境

## 🎯 Phase 6.4 成功標準

- ✅ CI 管道在每次 PR 時自動運行
- ✅ CD 管道在推送到 main 時自動部署
- ✅ 所有測試通過率 100%
- ✅ 安全掃描無高風險漏洞
- ✅ 部署過程完全自動化
- ✅ 文檔完整且最新
- ✅ 監控和警報設置完成

## 📞 支援和問題

### 常見問題
1. **CI 管道失敗**: 檢查日誌，運行本地測試腳本
2. **Docker 構建失敗**: 測試本地 Docker 構建
3. **部署失敗**: 檢查環境變數和日誌
4. **安全警報**: 更新依賴或添加例外

### 獲取幫助
1. 查看相關文檔
2. 運行本地測試腳本
3. 檢查 GitHub Actions 日誌
4. 提交 GitHub Issue
5. 聯繫項目維護者

---

**最後更新**: 2026-03-19  
**Phase 6.4 狀態**: ✅ 完成  
**驗證者**: K (Claude Code)