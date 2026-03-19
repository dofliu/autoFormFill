# 部署指南

本文檔說明如何部署 AutoFormFill 應用程式到生產環境。

## 部署選項

### 選項 1: Docker Compose (推薦)

#### 前置要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB RAM
- 至少 10GB 磁碟空間

#### 部署步驟

1. **準備伺服器**
   ```bash
   # 更新系統
   sudo apt update && sudo apt upgrade -y
   
   # 安裝 Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # 安裝 Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **下載部署文件**
   ```bash
   # 創建應用目錄
   sudo mkdir -p /opt/autoformfill
   cd /opt/autoformfill
   
   # 下載最新版本
   # 方法 A: 從 GitHub 下載
   wget https://github.com/your-username/autoFormFill/releases/latest/download/deployment-artifacts.zip
   unzip deployment-artifacts.zip
   
   # 方法 B: 使用 git
   git clone https://github.com/your-username/autoFormFill.git .
   git checkout main
   ```

3. **配置環境變數**
   ```bash
   # 複製環境變數模板
   cp .env.template .env
   
   # 編輯環境變數
   nano .env
   ```
   
   最少需要配置：
   ```bash
   GEMINI_API_KEY=your_google_gemini_api_key
   JWT_SECRET_KEY=generate_a_secure_random_string_here
   ```

4. **設置文件權限**
   ```bash
   # 創建數據目錄
   sudo mkdir -p data/uploads data/outputs
   sudo chown -R 1000:1000 data
   
   # 保護環境變數文件
   sudo chmod 600 .env
   ```

5. **啟動應用**
   ```bash
   # 使用部署腳本
   chmod +x deploy.sh
   ./deploy.sh
   
   # 或手動啟動
   docker-compose pull
   docker-compose up -d
   ```

6. **驗證部署**
   ```bash
   # 檢查容器狀態
   docker-compose ps
   
   # 檢查日誌
   docker-compose logs -f
   
   # 測試健康檢查
   curl http://localhost:8000/health
   
   # 測試前端
   curl -I http://localhost
   ```

### 選項 2: Kubernetes

#### 前置要求
- Kubernetes 1.24+
- Helm 3.0+
- Ingress Controller (如 nginx-ingress)

#### 部署步驟

1. **創建命名空間**
   ```bash
   kubectl create namespace autoformfill
   ```

2. **創建 secrets**
   ```bash
   # 創建環境變數 secret
   kubectl create secret generic autoformfill-env \
     --namespace autoformfill \
     --from-file=.env=./.env
   ```

3. **部署應用**
   ```bash
   # 應用 Kubernetes 配置
   kubectl apply -f kubernetes/
   
   # 或使用 Helm
   helm install autoformfill ./charts/autoformfill \
     --namespace autoformfill
   ```

4. **配置 Ingress**
   ```bash
   # 應用 Ingress 配置
   kubectl apply -f kubernetes/ingress.yaml
   ```

### 選項 3: 雲端平台

#### AWS ECS

1. **創建 ECR 倉庫**
   ```bash
   aws ecr create-repository --repository-name autoformfill
   ```

2. **推送 Docker 鏡像**
   ```bash
   # 登錄 ECR
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   
   # 標記和推送鏡像
   docker tag autoformfill:latest <account-id>.dkr.ecr.<region>.amazonaws.com/autoformfill:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/autoformfill:latest
   ```

3. **創建 ECS 任務定義和服務**

#### Google Cloud Run

1. **構建和推送鏡像**
   ```bash
   gcloud builds submit --tag gcr.io/<project-id>/autoformfill
   ```

2. **部署到 Cloud Run**
   ```bash
   gcloud run deploy autoformfill \
     --image gcr.io/<project-id>/autoformfill \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

## 自動化部署 (CI/CD)

### GitHub Actions 自動部署

當推送到 main 分支或創建版本標籤時，GitHub Actions 會自動：

1. 構建 Docker 鏡像
2. 推送到 GitHub Container Registry
3. 部署到目標伺服器

#### 配置 GitHub Secrets

在 Repository Settings → Secrets and variables → Actions 中設置：

| Secret 名稱 | 描述 | 範例 |
|------------|------|------|
| `GEMINI_API_KEY` | Gemini API 金鑰 | `AIzaSy...` |
| `SSH_PRIVATE_KEY` | 部署伺服器 SSH 私鑰 | `-----BEGIN RSA PRIVATE KEY-----` |
| `DEPLOY_HOST` | 部署伺服器地址 | `example.com` 或 `192.168.1.100` |
| `DEPLOY_USER` | 部署用戶名 | `deploy` |
| `DEPLOY_PATH` | 部署路徑 | `/opt/autoformfill` |

#### 手動觸發部署

在 GitHub Actions 頁面，可以手動觸發部署工作流。

## 監控和維護

### 日誌管理

```bash
# 查看實時日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs backend
docker-compose logs frontend

# 導出日誌到文件
docker-compose logs --tail=1000 > logs.txt
```

### 性能監控

```bash
# 查看資源使用情況
docker stats

# 查看容器詳細信息
docker-compose ps
docker inspect <container_id>

# 監控應用性能
curl http://localhost:8000/metrics
```

### 備份和恢復

#### 數據備份
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/autoformfill"
DATE=$(date +%Y%m%d_%H%M%S)

# 創建備份目錄
mkdir -p $BACKUP_DIR

# 備份數據庫
docker-compose exec -T backend sqlite3 /app/data/smartfill.db ".backup $BACKUP_DIR/smartfill_$DATE.db"

# 備份上傳文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz data/uploads/

# 備份輸出文件
tar -czf $BACKUP_DIR/outputs_$DATE.tar.gz data/outputs/

# 保留最近7天的備份
find $BACKUP_DIR -type f -mtime +7 -delete
```

#### 數據恢復
```bash
#!/bin/bash
# restore.sh
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <backup_file>"
  exit 1
fi

# 停止應用
docker-compose down

# 恢復數據
tar -xzf $BACKUP_FILE -C /

# 啟動應用
docker-compose up -d
```

### 更新應用

```bash
# 使用更新腳本
./update.sh

# 或手動更新
git pull origin main
docker-compose pull
docker-compose up -d --build
```

### 回滾到舊版本

```bash
# 查看可用版本
git tag

# 回滾到特定版本
git checkout v1.0.0
./deploy.sh
```

## 故障排除

### 常見問題

#### 1. 容器無法啟動
```bash
# 檢查日誌
docker-compose logs

# 檢查端口衝突
netstat -tulpn | grep :80
netstat -tulpn | grep :8000

# 檢查 Docker 服務狀態
systemctl status docker
```

#### 2. 數據庫連接問題
```bash
# 檢查數據庫文件權限
ls -la data/

# 檢查數據庫連接
docker-compose exec backend python -c "import sqlite3; conn = sqlite3.connect('/app/data/smartfill.db'); print('Database connected')"
```

#### 3. API 金鑰無效
```bash
# 測試 API 金鑰
docker-compose exec backend python -c "
import os
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    print(f'API Key length: {len(api_key)}')
else:
    print('API Key not found')
"
```

#### 4. 內存不足
```bash
# 查看系統內存
free -h

# 查看容器內存使用
docker stats --no-stream

# 調整 Docker 內存限制
# 編輯 /etc/docker/daemon.json
{
  "default-ulimits": {
    "memory": "2g"
  }
}
```

### 性能優化

#### 調整 Docker 資源限制
```yaml
# docker-compose.override.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
  frontend:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.25'
```

#### 啟用緩存
```yaml
# docker-compose.override.yml
services:
  backend:
    environment:
      - CACHE_ENABLED=True
      - CACHE_TTL=300
      - REDIS_URL=redis://redis:6379/0
    
  redis:
    image: redis:alpine
    restart: unless-stopped
```

## 安全最佳實踐

### 1. 定期更新
```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 更新 Docker 鏡像
docker-compose pull

# 更新依賴
docker-compose exec backend pip list --outdated
```

### 2. 安全掃描
```bash
# 掃描 Docker 鏡像漏洞
docker scan autoformfill-backend:latest

# 掃描代碼安全問題
bandit -r app/
safety check
```

### 3. 訪問控制
```bash
# 配置防火牆
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 使用 HTTPS
# 配置 nginx 或 traefik 作為反向代理
```

### 4. 監控和警報
```bash
# 設置監控腳本
#!/bin/bash
# monitor.sh
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$HEALTH" != "200" ]; then
  echo "Health check failed: $HEALTH"
  # 發送警報郵件或通知
fi
```

## 支持

如果遇到問題，請：

1. 檢查 [故障排除](#故障排除) 章節
2. 查看 GitHub Issues
3. 查閱 [API 文檔](./API_DOCUMENTATION.md)
4. 聯繫維護團隊

## 版本歷史

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| 1.0.0 | 2026-03-13 | 初始部署指南 |
| 1.1.0 | 2026-03-13 | 添加 Kubernetes 和雲端部署選項 |