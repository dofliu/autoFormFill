# Phase 6.4 - 部署指南

本文檔提供 AutoFormFill 專案的完整部署指南，專為 Phase 6.4 CI/CD 流程設計。

## 部署選項

### 1. Docker Compose (推薦用於中小型部署)

#### 快速開始
```bash
# 1. 克隆專案
git clone https://github.com/yourusername/autoFormFill.git
cd autoFormFill

# 2. 配置環境變數
cp .env.example .env
# 編輯 .env 文件，填入你的 API 金鑰

# 3. 啟動服務
docker-compose up -d

# 4. 檢查服務狀態
docker-compose ps

# 5. 查看日誌
docker-compose logs -f
```

#### 服務訪問
- **前端**: http://localhost:80
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/health

### 2. Kubernetes (生產級部署)

#### 部署文件
```bash
# 應用 Kubernetes 配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

#### 檢查部署狀態
```bash
# 檢查 Pod 狀態
kubectl get pods -n autoformfill

# 檢查服務
kubectl get svc -n autoformfill

# 查看日誌
kubectl logs -f deployment/autoformfill-backend -n autoformfill

# 進入容器
kubectl exec -it deployment/autoformfill-backend -n autoformfill -- /bin/bash
```

### 3. 雲平台部署

#### AWS ECS
```bash
# 構建並推送 Docker 鏡像
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t autoformfill-backend .
docker tag autoformfill-backend:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/autoformfill-backend:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/autoformfill-backend:latest

# 更新 ECS 服務
aws ecs update-service --cluster autoformfill-cluster --service autoformfill-service --force-new-deployment
```

#### Google Cloud Run
```bash
# 構建並部署
gcloud builds submit --tag gcr.io/your-project/autoformfill
gcloud run deploy autoformfill \
  --image gcr.io/your-project/autoformfill \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=your_key"
```

## 環境配置

### 1. 環境變數設置

#### 必需變數
```bash
# .env 文件內容示例
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash
DATABASE_URL=sqlite+aiosqlite:///./data/smartfill.db
CHROMA_PERSIST_DIR=/app/data/chroma
UPLOAD_DIR=/app/data/uploads
OUTPUT_DIR=/app/data/outputs
```

#### 安全最佳實踐
```bash
# 使用 Docker secrets (推薦)
echo "your_gemini_api_key" | docker secret create gemini_api_key -

# 使用 Kubernetes secrets
kubectl create secret generic autoformfill-secrets \
  --from-literal=gemini-api-key=your_key \
  --namespace autoformfill
```

### 2. 數據持久化

#### Docker Compose
```yaml
volumes:
  autoformfill_data:
    driver: local
  autoformfill_chroma:
    driver: local
```

#### Kubernetes
```yaml
persistentVolumeClaims:
  - metadata:
      name: data-pvc
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 10Gi
```

## 監控和維護

### 1. 健康檢查
```bash
# 手動檢查
curl -f http://localhost:8000/health

# 自動化檢查腳本
./scripts/health-check.sh
```

### 2. 日誌管理
```bash
# 查看實時日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs backend

# 導出日誌
docker-compose logs --tail=1000 > logs/$(date +%Y%m%d_%H%M%S).log
```

### 3. 備份和恢復

#### 備份腳本
```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/backup/autoformfill"
DATE=$(date +%Y%m%d_%H%M%S)

# 創建備份目錄
mkdir -p $BACKUP_DIR/$DATE

# 備份數據庫
docker exec autoformfill-backend sqlite3 /app/data/smartfill.db ".backup $BACKUP_DIR/$DATE/smartfill.db"

# 備份上傳文件
tar -czf $BACKUP_DIR/$DATE/uploads.tar.gz data/uploads/

# 備份輸出文件
tar -czf $BACKUP_DIR/$DATE/outputs.tar.gz data/outputs/

# 備份 ChromaDB
tar -czf $BACKUP_DIR/$DATE/chroma.tar.gz data/chroma/

echo "Backup completed: $BACKUP_DIR/$DATE"
```

#### 恢復腳本
```bash
#!/bin/bash
# scripts/restore.sh
BACKUP_DIR="/backup/autoformfill"
BACKUP_DATE=$1

if [ -z "$BACKUP_DATE" ]; then
  echo "Usage: $0 <backup_date>"
  ls $BACKUP_DIR
  exit 1
fi

# 停止服務
docker-compose down

# 恢復數據庫
docker exec -i autoformfill-backend sqlite3 /app/data/smartfill.db < $BACKUP_DIR/$BACKUP_DATE/smartfill.db

# 恢復文件
tar -xzf $BACKUP_DIR/$BACKUP_DATE/uploads.tar.gz -C data/
tar -xzf $BACKUP_DIR/$BACKUP_DATE/outputs.tar.gz -C data/
tar -xzf $BACKUP_DIR/$BACKUP_DATE/chroma.tar.gz -C data/

# 啟動服務
docker-compose up -d

echo "Restore completed from $BACKUP_DATE"
```

## 擴展和優化

### 1. 水平擴展
```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 2. 負載均衡
```yaml
# nginx 配置示例
upstream backend {
  server backend1:8000;
  server backend2:8000;
  server backend3:8000;
}

server {
  listen 80;
  
  location /api/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

### 3. 緩存配置
```python
# 後端緩存配置
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis

redis_client = redis.Redis(host="redis", port=6379, db=0)
FastAPICache.init(RedisBackend(redis_client), prefix="autoformfill-cache")
```

## 故障排除

### 常見問題

#### 1. 服務無法啟動
```bash
# 檢查日誌
docker-compose logs

# 檢查端口衝突
netstat -tulpn | grep :80
netstat -tulpn | grep :8000

# 檢查環境變數
docker-compose config
```

#### 2. API 金鑰無效
```bash
# 驗證 API 金鑰
curl -X POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent \
  -H "Content-Type: application/json" \
  -H "x-goog-api-key: YOUR_API_KEY" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

#### 3. 數據庫連接問題
```bash
# 檢查數據庫文件權限
ls -la data/

# 檢查數據庫完整性
docker exec autoformfill-backend sqlite3 /app/data/smartfill.db "PRAGMA integrity_check;"

# 修復數據庫
docker exec autoformfill-backend sqlite3 /app/data/smartfill.db ".backup /tmp/backup.db"
docker exec autoformfill-backend sqlite3 /tmp/backup.db ".restore /app/data/smartfill.db"
```

#### 4. 內存不足
```bash
# 檢查內存使用
docker stats

# 增加內存限制
# 在 docker-compose.yml 中：
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 安全配置

### 1. SSL/TLS 配置
```nginx
# nginx SSL 配置
server {
  listen 443 ssl;
  server_name autoformfill.example.com;
  
  ssl_certificate /etc/nginx/ssl/cert.pem;
  ssl_certificate_key /etc/nginx/ssl/key.pem;
  
  location / {
    proxy_pass http://frontend:80;
  }
}
```

### 2. 防火牆規則
```bash
# 只允許必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw --force enable
```

### 3. 定期安全更新
```bash
# 更新 Docker 鏡像
docker-compose pull
docker-compose up -d

# 更新系統包
apt update && apt upgrade -y

# 掃描漏洞
trivy image autoformfill-backend:latest
```

## 性能優化

### 1. 數據庫優化
```sql
-- 創建索引
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);

-- 定期清理
DELETE FROM documents WHERE created_at < datetime('now', '-30 days');
VACUUM;
```

### 2. 緩存策略
```python
# 使用緩存裝飾器
from fastapi_cache.decorator import cache

@router.get("/documents/{document_id}")
@cache(expire=300)  # 緩存 5 分鐘
async def get_document(document_id: int):
    return await get_document_from_db(document_id)
```

### 3. 並發優化
```python
# 使用異步處理
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def process_documents_batch(documents):
    loop = asyncio.get_event_loop()
    tasks = []
    for doc in documents:
        task = loop.run_in_executor(executor, process_document, doc)
        tasks.append(task)
    return await asyncio.gather(*tasks)
```

## 自動化部署腳本

### 1. 一鍵部署腳本
```bash
#!/bin/bash
# deploy.sh
set -e

echo "🚀 Starting AutoFormFill deployment..."

# 檢查依賴
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

# 檢查環境變數
if [ ! -f .env ]; then
  echo "❌ .env file not found. Creating from template..."
  cp .env.example .env
  echo "⚠️  Please edit .env file and set your API keys."
  exit 1
fi

# 拉取最新鏡像
echo "📥 Pulling latest images..."
docker-compose pull

# 停止舊容器
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans

# 啟動新容器
echo "🚀 Starting new containers..."
docker-compose up -d

# 等待服務就緒
echo "⏳ Waiting for services to be ready..."
sleep 10

# 運行健康檢查
echo "🏥 Running health checks..."
if curl -s -f http://localhost:8000/health > /dev/null; then
  echo "✅ Deployment successful!"
  echo ""
  echo "🌐 Frontend: http://localhost:80"
  echo "🔧 Backend API: http://localhost:8000"
  echo "📝 API Documentation: http://localhost:8000/docs"
else
  echo "❌ Health check failed"
  docker-compose logs
  exit 1
fi
```

### 2. 滾動更新腳本
```bash
#!/bin/bash
# rolling-update.sh
set -e

# 藍綠部署策略
BLUE="autoformfill-blue"
GREEN="autoformfill-green"

# 檢查當前活動部署
if docker-compose -p $BLUE ps | grep -q "Up"; then
  ACTIVE=$BLUE
  STANDBY=$GREEN
else
  ACTIVE=$GREEN
  STANDBY=$BLUE
fi

echo "Current active deployment: $ACTIVE"
echo "Updating standby deployment: $STANDBY"

# 更新待機部署
docker-compose -p $STANDBY pull
docker-compose -p $STANDBY up -d

# 等待待機部署就緒
echo "Waiting for standby deployment to be ready..."
sleep 15

# 切換流量
echo "Switching traffic to $STANDBY..."
# 這裡可以更新負載均衡器配置

# 停止舊部署
echo "Stopping old deployment: $ACTIVE..."
docker-compose -p $ACTIVE down

echo "Rolling update completed!"
```

## 監控和警報

### 1. Prometheus 配置
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'autoformfill'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

### 2. Grafana 儀表板
```json
{
  "dashboard": {
    "title": "AutoFormFill Monitoring",
    "panels": [
      {
        "title": "API Requests",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      }
    ]
  }
}
```

### 3. 警報規則
```yaml
# alert-rules.yml
groups:
  - name: autoformfill
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for 2 minutes"
```

## 總結

本部署指南提供了 AutoFormFill 專案的完整部署方案，涵蓋了從簡單的 Docker Compose 部署到生產級的 Kubernetes 部署。根據你的需求選擇合適的部署方式，並遵循安全最佳實踐確保系統穩定運行。

如需進一步協助，請參考：
- [環境變數管理](./ENVIRONMENT_VARIABLES.md)
- [CI/CD 指南](./CI_CD_GUIDE.md)
- [API 文檔](../README.md#api-文檔)