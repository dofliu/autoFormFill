# Phase 6.4 CI/CD 檢查清單

本文檔提供 Phase 6.4 CI/CD 實施的完整檢查清單。

## 實施狀態

| 項目 | 狀態 | 完成日期 | 備註 |
|------|------|----------|------|
| 1. CI 管道 (.github/workflows/ci.yml) | ✅ 完成 | 2026-03-18 | 包含 lint、test、security scan |
| 2. CD 管道 (.github/workflows/deploy.yml) | ✅ 完成 | 2026-03-18 | 包含 build、push、deploy |
| 3. 環境變數管理文件 | ✅ 完成 | 2026-03-18 | ENVIRONMENT_VARIABLES.md |
| 4. CI/CD 指南文件 | ✅ 完成 | 2026-03-18 | CI_CD_GUIDE.md |
| 5. 部署指南文件 | ✅ 完成 | 2026-03-18 | DEPLOYMENT.md |
| 6. 測試覆蓋率報告 | ✅ 完成 | 2026-03-18 | 集成到 CI 管道 |
| 7. 安全掃描集成 | ✅ 完成 | 2026-03-18 | Bandit、Safety、Trivy |
| 8. Docker 鏡像構建 | ✅ 完成 | 2026-03-18 | 多架構支持 |
| 9. 部署腳本生成 | ✅ 完成 | 2026-03-18 | deploy.sh、monitor.sh 等 |
| 10. 版本發布自動化 | ✅ 完成 | 2026-03-18 | 標籤觸發發布 |

## 文件結構

```
.github/
├── workflows/
│   ├── ci.yml              # Phase 6.4 CI 管道
│   └── deploy.yml          # Phase 6.4 CD 管道
docs/
├── CI_CD_GUIDE.md          # CI/CD 指南
├── DEPLOYMENT.md           # 部署指南
├── ENVIRONMENT_VARIABLES.md # 環境變數管理
├── PHASE_6_4_CHECKLIST.md  # 本文件
└── API_DOCUMENTATION.md    # API 文檔
```

## 配置步驟

### 1. GitHub Secrets 設置

在 GitHub Repository Settings → Secrets and variables → Actions 中設置：

1. **GEMINI_API_KEY** - 用於測試的 Gemini API 金鑰
2. **DOCKERHUB_USERNAME** - Docker Hub 用戶名 (可選)
3. **DOCKERHUB_TOKEN** - Docker Hub 訪問令牌 (可選)
4. **GHCR_TOKEN** - GitHub Container Registry 令牌

### 2. GitHub Variables 設置

在 GitHub Repository Settings → Secrets and variables → Actions → Variables 中設置：

1. **PYTHON_VERSION** = `3.11,3.12`
2. **NODE_VERSION** = `20`
3. **DOCKER_REGISTRY** = `ghcr.io` (或 `docker.io`)

### 3. 本地測試

在提交前運行本地測試：

```bash
# 運行完整的本地 CI 檢查
./scripts/local-ci.sh

# 或手動運行
cd frontend && npm run lint && npx tsc --noEmit && npm run build
cd .. && black --check . && flake8 . && python -m pytest tests/ -v
```

## CI 管道詳細說明

### 觸發條件
- **Pull Request** - 任何 PR 到 main/master 分支
- **Push** - 推送到 main/master 分支
- **Schedule** - 每週一 00:00 UTC
- **Manual** - 手動觸發

### 工作流步驟
1. **代碼檢查** - Python 和 TypeScript 靜態分析
2. **單元測試** - 後端和前端測試
3. **集成測試** - API 端點測試
4. **安全掃描** - 代碼和依賴漏洞掃描
5. **Docker 測試** - 鏡像構建和配置測試
6. **性能測試** - 負載測試 (僅主分支)
7. **報告生成** - 測試覆蓋率和安全報告

## CD 管道詳細說明

### 觸發條件
- **Push to main/master** - 自動構建和推送鏡像
- **Version tags (v*)** - 創建版本發布
- **GitHub Release** - 發布時觸發
- **Manual** - 手動選擇環境部署

### 工作流步驟
1. **預部署檢查** - 驗證配置和環境變數
2. **Docker 構建** - 構建後端和前端鏡像
3. **鏡像推送** - 推送到指定的鏡像倉庫
4. **SBOM 生成** - 生成軟體物料清單
5. **部署套件生成** - 創建部署腳本和文檔
6. **自動部署** - 可選的自動部署到伺服器
7. **發布創建** - 自動創建 GitHub Release

## 環境變數管理

### 分層管理
1. **開發環境** - `.env` 文件
2. **測試環境** - GitHub Actions Secrets
3. **生產環境** - 伺服器環境變數或 Docker secrets
4. **CI/CD 環境** - GitHub Actions 工作流變數

### 安全最佳實踐
1. 使用不同的 API 金鑰用於不同環境
2. 定期輪換敏感憑證
3. 使用 Docker secrets 保護生產環境金鑰
4. 最小權限原則

## 故障排除

### CI 失敗常見原因
1. **測試失敗** - 檢查測試用例和環境變數
2. **代碼檢查失敗** - 運行 `black .` 和 `isort .` 修復格式
3. **依賴問題** - 更新 `requirements.txt` 和 `package.json`
4. **Docker 構建失敗** - 檢查 Dockerfile 語法和依賴

### CD 失敗常見原因
1. **認證失敗** - 檢查 Docker 倉庫憑證
2. **環境變數缺失** - 驗證所有必需的 secrets
3. **網絡問題** - 檢查網絡連接和防火牆設置
4. **資源不足** - 確保伺服器有足夠的資源

## 監控和維護

### 定期檢查
1. **每週** - 檢查 CI/CD 管道運行狀態
2. **每月** - 審查安全報告和更新依賴
3. **每季度** - 輪換 API 金鑰和憑證

### 性能指標
1. **構建時間** - 目標 < 10 分鐘
2. **測試覆蓋率** - 目標 > 80%
3. **安全漏洞** - 零高風險漏洞
4. **部署成功率** - 目標 > 95%

## 升級指南

### 添加新測試
1. 在 `tests/` 目錄中添加測試文件
2. 更新 `requirements.txt` 添加測試依賴
3. 確保測試在 CI 管道中運行

### 添加新部署環境
1. 在 `deploy.yml` 中添加新的環境配置
2. 設置對應的 GitHub Secrets
3. 更新部署腳本支持新環境

### 更新 CI/CD 管道
1. 修改 `.github/workflows/` 中的 YAML 文件
2. 在測試環境驗證更改
3. 更新文檔反映變化

## 聯繫和支持

如有問題，請參考：
1. [CI/CD 指南](./CI_CD_GUIDE.md)
2. [部署指南](./DEPLOYMENT.md)
3. [環境變數管理](./ENVIRONMENT_VARIABLES.md)
4. GitHub Actions 日誌和報告

---

**Phase 6.4 CI/CD 實施完成時間：2026-03-18**
**實施者：K (Claude Code)**
**狀態：✅ 全部完成**