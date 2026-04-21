# 部署文档

## 系统要求

### 最低配置
- CPU: 2核
- 内存: 4GB
- 存储: 20GB可用空间
- 操作系统: Linux / macOS / Windows 10+

### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 存储: 100GB SSD
- 操作系统: Ubuntu 22.04 LTS

## 部署方式

### 方式一：直接运行（开发环境）

#### 1. 安装Python 3.10+
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.10 python3-pip python3.10-venv

# macOS (使用Homebrew)
brew install python@3.10

# Windows
# 从官网下载安装: https://www.python.org/downloads/
```

#### 2. 创建虚拟环境
```bash
python3.10 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或者
venv\Scripts\activate  # Windows
```

#### 3. 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要参数：
```env
# 必填配置
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-secret-key-change-in-production

# 可选配置
OPENAI_BASE_URL=https://api.openai.com/v1  # 自定义API地址
MODEL_NAME=gpt-3.5-turbo-1106               # 使用的模型
DEBUG=True                                  # 调试模式
```

#### 5. 启动服务
```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

#### 6. 验证部署
```bash
# 检查健康状态
curl http://localhost:8000/health

# 预期输出: {"status":"ok","message":"系统运行正常"}
```

---

### 方式二：Docker Compose部署（生产环境）

#### 1. 安装Docker和Docker Compose
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo apt install docker-compose-plugin
```

#### 2. 配置环境变量
```bash
export OPENAI_API_KEY=your-openai-api-key
export SECRET_KEY=your-production-secret-key
```

或者创建 `.env` 文件：
```env
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-secret-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-3.5-turbo-1106
DEBUG=False
```

#### 3. 启动服务
```bash
docker-compose up -d
```

#### 4. 查看服务状态
```bash
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 5. 验证部署
```bash
curl http://localhost:8000/health
```

---

### 方式三：Kubernetes部署（大规模生产）

#### 1. 创建命名空间
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-paper-system
```

#### 2. 创建配置映射和密钥
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-paper-system-config
  namespace: ai-paper-system
data:
  DEBUG: "False"
  HOST: "0.0.0.0"
  PORT: "8000"
  OPENAI_BASE_URL: "https://api.openai.com/v1"
  MODEL_NAME: "gpt-3.5-turbo-1106"
---
apiVersion: v1
kind: Secret
metadata:
  name: ai-paper-system-secrets
  namespace: ai-paper-system
type: Opaque
data:
  OPENAI_API_KEY: <base64-encoded-api-key>
  SECRET_KEY: <base64-encoded-secret-key>
```

#### 3. 创建部署
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-paper-system
  namespace: ai-paper-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-paper-system
  template:
    metadata:
      labels:
        app: ai-paper-system
    spec:
      containers:
      - name: ai-paper-system
        image: ai-paper-system:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ai-paper-system-config
        - secretRef:
            name: ai-paper-system-secrets
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
        volumeMounts:
        - name: storage
          mountPath: /app/storage
        - name: chroma-db
          mountPath: /app/chroma_db
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: ai-paper-system-storage
      - name: chroma-db
        persistentVolumeClaim:
          claimName: ai-paper-system-chroma-db
```

#### 4. 创建服务和Ingress
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-paper-system-service
  namespace: ai-paper-system
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: ai-paper-system
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-paper-system-ingress
  namespace: ai-paper-system
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  rules:
  - host: paper-system.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-paper-system-service
            port:
              number: 80
```

## 生产环境优化

### 1. 数据库配置
默认使用SQLite，生产环境建议使用PostgreSQL：
```env
DATABASE_URL=postgresql://user:password@postgres:5432/paper_system
```

PostgreSQL Docker Compose配置：
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: paper_system
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
```

### 2. 向量数据库配置
默认使用ChromaDB，大规模场景建议使用Qdrant：
```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
```

### 3. 异步任务队列
对于大规模爬虫和复现任务，建议添加Celery队列：
```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  celery-worker:
    build: .
    command: celery -A src.core.tasks worker --loglevel=info
    volumes:
      - ./storage:/app/storage
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped
```

### 4. Nginx反向代理
```nginx
server {
    listen 80;
    server_name paper-system.example.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # 静态文件缓存
    location /static/ {
        alias /path/to/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

## 监控和运维

### 1. 日志管理
日志默认存储在 `logs/` 目录下，建议配置日志轮转：
```logrotate
/path/to/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload ai-paper-system.service
    endscript
}
```

### 2. 系统服务配置（systemd）
```ini
[Unit]
Description=AI Paper System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/app
Environment="PATH=/path/to/app/venv/bin"
ExecStart=/path/to/app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-paper-system
sudo systemctl start ai-paper-system
```

### 3. 备份策略
建议定期备份以下数据：
- 数据库文件 (`papers.db` 或 PostgreSQL 数据)
- 向量数据库目录 (`chroma_db/`)
- 存储目录 (`storage/`)
- 配置文件 (`.env`)

备份脚本示例：
```bash
#!/bin/bash
BACKUP_DIR=/backup/ai-paper-system
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
sqlite3 /path/to/app/papers.db ".backup $BACKUP_DIR/db_$DATE.sqlite3"

# 备份向量库
tar -czf $BACKUP_DIR/chroma_$DATE.tar.gz /path/to/app/chroma_db

# 备份存储
tar -czf $BACKUP_DIR/storage_$DATE.tar.gz /path/to/app/storage

# 备份配置
cp /path/to/app/.env $BACKUP_DIR/env_$DATE

# 删除30天前的备份
find $BACKUP_DIR -type f -mtime +30 -delete
```

添加到cron定时任务：
```bash
0 2 * * * /path/to/backup_script.sh
```

## 常见问题排查

### 1. 服务启动失败
```bash
# 查看日志
tail -f logs/app.log

# 检查端口占用
lsof -i :8000

# 检查依赖是否完整
pip list | grep -E "fastapi|uvicorn|langchain|chromadb"
```

### 2. OpenAI API调用失败
- 检查API密钥是否正确
- 检查网络连接和代理配置
- 检查账户余额和API额度
- 查看API返回的具体错误信息

### 3. PDF下载失败
- 检查网络连接
- 检查是否被目标网站封禁
- 尝试配置代理：`PROXY_URL=http://proxy:port`
- 调整速率限制：`CRAWL_RATE_LIMIT=2.0`

### 4. 复现功能不可用
- 检查Docker是否正常运行：`docker info`
- 检查Docker socket权限：`ls -l /var/run/docker.sock`
- 确保当前用户有Docker访问权限：`sudo usermod -aG docker $USER`
- 检查Docker镜像是否能正常构建

### 5. 向量检索慢
- 增加内存配置
- 考虑使用Qdrant或Weaviate替代ChromaDB
- 调整向量索引配置
- 定期优化向量数据库

## 性能基准

| 功能 | 平均耗时 | 并发支持 |
|------|----------|----------|
| 论文搜索 | <1s | 100+ QPS |
| PDF下载 | 2-5s/篇 | 10并发 |
| 论文解读 | 10-30s/篇 | 5并发 |
| 向量检索 | <100ms/次 | 1000+ QPS |
| 复现任务 | 1-10min/篇 | 2并发（单节点） |

## 安全建议

1. **身份认证**：生产环境建议添加API Key认证或OAuth2认证
2. **HTTPS配置**：使用Let's Encrypt配置SSL证书，启用HTTPS
3. **CORS限制**：配置允许的域名，避免跨站请求伪造
4. **输入过滤**：所有用户输入都经过严格校验，防止注入攻击
5. **资源限制**：配置Docker容器资源限制，防止资源耗尽
6. **定期更新**：及时更新依赖包和系统补丁，修复安全漏洞

## 升级指南

### 版本升级步骤
1. 备份所有数据
2. 拉取最新代码：`git pull`
3. 升级依赖：`pip install -r requirements.txt`
4. 执行数据库迁移（如果有）
5. 重启服务
6. 验证功能正常

### 数据库迁移
使用Alembic进行数据库迁移：
```bash
# 初始化迁移环境
alembic init alembic

# 生成迁移脚本
alembic revision --autogenerate -m "update schema"

# 执行迁移
alembic upgrade head
```

如有其他问题，请参考[README.md](./README.md)或提交Issue。
