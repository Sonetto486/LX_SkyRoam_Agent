# SkyRoam Docker 部署指南

## 快速开始

### 1. 环境准备

确保已安装：
- Docker Desktop (Windows/Mac) 或 Docker Engine (Linux)
- Docker Compose v2.0+

验证安装：
```bash
docker --version
docker compose version
```

### 2. 配置环境变量

```bash
# 复制生产环境配置模板
cp .env.docker.prod.example .env.docker.prod

# 编辑配置文件，填入你的 API 密钥
# 必须修改以下配置：
# - POSTGRES_PASSWORD（数据库密码）
# - SECRET_KEY（应用密钥）
# - OPENAI_API_KEY（LLM API 密钥）
# - AMAP_API_KEY（高德地图 API 密钥）
```

### 3. 启动服务

**开发环境**（支持热重载）：
```bash
docker compose up -d
```

**生产环境**：
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. 访问应用

- **前端页面**: http://localhost
- **API 文档**: http://localhost/docs
- **健康检查**: http://localhost/health

## 服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (80)                           │
│                    反向代理 + 负载均衡                        │
└─────────────────┬───────────────────┬───────────────────────┘
                  │                   │
        ┌─────────▼─────────┐ ┌───────▼────────┐
        │   Frontend (80)   │ │ Backend (8001) │
        │   React + Nginx   │ │    FastAPI     │
        └───────────────────┘ └───────┬────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
          ┌─────────▼────────┐ ┌────────▼────────┐ ┌───────▼──────┐
          │ Celery Worker    │ │  Celery Beat    │ │  PostgreSQL  │
          │ (异步任务处理)     │ │  (定时任务)      │ │   + pgvector │
          └──────────────────┘ └─────────────────┘ └──────────────┘
                    │
          ┌─────────▼────────┐
          │      Redis       │
          │  (缓存 + 消息队列) │
          └──────────────────┘
```

## 常用命令

### 服务管理

```bash
# 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 停止所有服务
docker compose -f docker-compose.prod.yml down

# 重启特定服务
docker compose -f docker-compose.prod.yml restart backend

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery-worker
```

### 数据管理

```bash
# 备份 PostgreSQL 数据库
docker exec skyroam-postgres-prod pg_dump -U postgres skyroam > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup.sql | docker exec -i skyroam-postgres-prod psql -U postgres skyroam

# 清理 Redis 缓存
docker exec skyroam-redis-prod redis-cli FLUSHALL

# 查看数据库连接
docker exec skyroam-postgres-prod psql -U postgres -d skyroam -c "SELECT count(*) FROM pg_stat_activity;"
```

### 镜像管理

```bash
# 重新构建镜像
docker compose -f docker-compose.prod.yml build --no-cache

# 推送镜像到仓库
docker tag skyroam-backend:latest your-registry/skyroam-backend:latest
docker push your-registry/skyroam-backend:latest
```

## 生产环境优化

### 1. 安全加固

```bash
# 修改默认密码
# 在 .env.docker.prod 中设置强密码

# 限制端口暴露
# 只暴露 Nginx 端口，其他服务不对外

# 启用 HTTPS（需要配置 SSL 证书）
# 在 nginx/conf.d/default.conf 中添加 SSL 配置
```

### 2. 性能调优

**PostgreSQL**：
```sql
-- 调整连接池大小
ALTER SYSTEM SET max_connections = 200;

-- 启用查询优化
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_cache_size = '4GB';
```

**Redis**：
```bash
# 在 docker-compose.prod.yml 中调整内存限制
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**Celery**：
```yaml
# 调整并发数
environment:
  CELERY_WORKER_CONCURRENCY: 8  # 根据 CPU 核心数调整
```

### 3. 监控和日志

```bash
# 查看资源使用情况
docker stats

# 导出日志
docker compose -f docker-compose.prod.yml logs --no-color > app.log

# 实时监控 Celery 任务
docker compose -f docker-compose.prod.yml logs -f celery-worker
```

## 故障排查

### 后端无法启动

```bash
# 检查数据库连接
docker exec skyroam-postgres-prod psql -U postgres -d skyroam -c "SELECT 1;"

# 检查 Redis 连接
docker exec skyroam-redis-prod redis-cli ping

# 查看后端日志
docker compose -f docker-compose.prod.yml logs backend
```

### Celery 任务不执行

```bash
# 检查 Worker 状态
docker exec skyroam-backend-prod celery -A app.core.celery inspect active

# 检查队列
docker exec skyroam-redis-prod redis-cli LLEN celery

# 重启 Worker
docker compose -f docker-compose.prod.yml restart celery-worker
```

### 前端无法访问 API

```bash
# 检查 Nginx 配置
docker exec skyroam-nginx-prod nginx -t

# 检查网络连接
docker exec skyroam-nginx-prod ping backend

# 查看 Nginx 日志
docker compose -f docker-compose.prod.yml logs nginx
```

## 数据持久化

Docker Compose 会创建以下持久化卷：

| 卷名 | 用途 | 挂载点 |
|------|------|--------|
| postgres_data | 数据库数据 | /var/lib/postgresql/data |
| redis_data | Redis 数据 | /data |
| backend_uploads | 上传文件 | /app/uploads |
| backend_logs | 应用日志 | /app/logs |
| nginx_logs | Nginx 日志 | /var/log/nginx |

### 备份策略

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec skyroam-postgres-prod pg_dump -U postgres skyroam > $BACKUP_DIR/database.sql

# 备份上传文件
docker run --rm -v skyroam_uploads:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/uploads.tar.gz /data

# 备份 Redis
docker exec skyroam-redis-prod redis-cli BGSAVE
docker cp skyroam-redis-prod:/data/dump.rdb $BACKUP_DIR/redis.rdb
```

## 升级指南

```bash
# 1. 备份数据
./backup.sh

# 2. 拉取最新代码
git pull

# 3. 重新构建镜像
docker compose -f docker-compose.prod.yml build

# 4. 停止旧容器
docker compose -f docker-compose.prod.yml down

# 5. 启动新容器
docker compose -f docker-compose.prod.yml up -d

# 6. 运行数据库迁移（如有）
docker exec skyroam-backend-prod alembic upgrade head
```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| POSTGRES_PASSWORD | 数据库密码 | changeme |
| SECRET_KEY | 应用密钥 | - |
| OPENAI_API_KEY | LLM API 密钥 | - |
| AMAP_API_KEY | 高德地图 API 密钥 | - |
| NGINX_PORT | 对外暴露端口 | 80 |
| CELERY_WORKER_CONCURRENCY | Celery 并发数 | 4 |

## 常见问题

**Q: 如何修改端口？**
A: 修改 `.env.docker.prod` 中的 `NGINX_PORT` 变量。

**Q: 如何启用 HTTPS？**
A: 在 `nginx/conf.d/default.conf` 中添加 SSL 配置，或使用 Caddy/Nginx Proxy Manager。

**Q: 如何查看 Celery 任务执行情况？**
A: 访问 Flower 监控界面（需要启动 flower 服务）。

**Q: 数据库迁移失败怎么办？**
A: 检查 Alembic 版本，手动执行迁移脚本。

## 技术支持

如有问题，请查看：
- 项目文档: `CLAUDE.md`
- API 文档: http://localhost/docs
- 健康检查: http://localhost/health/backend
