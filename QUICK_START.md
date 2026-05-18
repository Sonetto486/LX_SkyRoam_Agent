# 🚀 LX SkyRoam Agent 快速启动指南

## 📋 前置要求

- **Docker**: 版本 20.10+
- **Docker Compose**: 版本 2.0+
- **Node.js**: 版本 16+ (仅用于本地开发)
- **Python**: 版本 3.10+ (仅用于本地开发)

## ⚡ 快速启动 (推荐)

### 方式一：Docker Compose（推荐）

#### 1. 克隆项目
```bash
git clone <your-repository-url>
cd LX_SkyRoam_Agent
```

#### 2. 配置环境
```bash
# 复制环境配置文件
cd backend
cp .env.example .env

# 编辑配置文件，添加你的API密钥
# 至少需要配置以下内容：
# - OPENAI_API_KEY: 你的OpenAI API密钥
# - 其他API密钥（可选）
```

#### 3. 一键启动
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

### 方式二：本地开发环境

#### 1. 环境要求
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

#### 2. 启动服务
```bash
# Windows
start-dev.bat

# Linux/Mac
chmod +x start-dev.sh
./start-dev.sh
```

#### 3. 手动启动
```bash
# 启动后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 启动Celery Worker（新终端）
cd backend
celery -A app.core.celery worker --loglevel=info

# 启动前端（新终端）
cd frontend
npm install
npm start
```

### 4. 访问应用
```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

### 4. 访问应用
- 前端应用: http://localhost:13000
- 后端 API: 默认不对外暴露；由前端容器通过 `http://backend:8001` 访问。若需宿主机直接访问，请在 `docker-compose.yml` 的 `backend` 服务添加端口映射：`ports: - "18001:8001"`，然后使用 `http://localhost:1`。
- API 文档: 默认仅容器内可访问 `http://backend:8001/docs`；如上端口映射后，可在宿主机访问 `http://localhost:18001/docs`。
- Celery 监控 (Flower): 默认仅容器内 `http://skyroam-flower:5555`；若需宿主机访问，请在 `flower` 服务添加端口映射：`ports: - "15555:5555"`，然后使用 `http://localhost:15555`。
- 高德 MCP HTTP 服务: http://localhost:13002
- 小红书 API 服务: http://localhost:18002
- PostgreSQL: 内网容器 `postgres:5432`，未对外暴露
- Redis: 内网容器 `redis:6379`，未对外暴露

## 🔧 手动启动 (开发模式)

### 后端启动
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

### 数据库启动
```bash
# 启动PostgreSQL和Redis
docker-compose up -d postgres redis

# 运行数据库迁移
cd backend
alembic upgrade head
```

## 🐳 Docker 启动

### 完整服务启动
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 单独启动服务
```bash
# 只启动数据库
docker-compose up -d postgres redis

# 只启动后端
docker-compose up -d backend

# 只启动前端
docker-compose up -d frontend
```

## 🔍 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 检查端口占用
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 停止占用进程
sudo kill -9 <PID>
```

#### 2. Docker 服务启动失败
```bash
# 查看详细错误
docker-compose logs backend
docker-compose logs frontend

# 重新构建镜像
docker-compose build --no-cache

# 清理并重启
docker-compose down
docker-compose up -d
```

#### 3. 前端依赖安装失败
```bash
# 清理缓存
npm cache clean --force

# 删除node_modules重新安装
rm -rf node_modules package-lock.json
npm install
```

#### 4. 后端依赖安装失败
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### 5. 数据库连接失败
```bash
# 检查数据库状态
docker-compose ps postgres

# 重启数据库
docker-compose restart postgres

# 查看数据库日志
docker-compose logs postgres
```

### 环境变量配置

#### 必需配置
```env
# OpenAI API密钥 (必需)
OPENAI_API_KEY=your-openai-api-key-here

# OpenAI API地址 (可选，支持自定义地址)
OPENAI_API_BASE=https://api.openai.com/v1
# 示例自定义地址：
# OPENAI_API_BASE=https://your-proxy.com/v1
# OPENAI_API_BASE=https://api.openai-proxy.com/v1

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/skyroam
REDIS_URL=redis://localhost:6379/0
```

#### 可选配置
```env
# 第三方API密钥 (可选，用于真实数据)
WEATHER_API_KEY=your-openweathermap-api-key
FLIGHT_API_KEY=your-amadeus-api-key
HOTEL_API_KEY=your-booking-api-key
MAP_API_KEY=your-google-maps-api-key
```

## 📊 服务监控

### 健康检查（Docker 部署）
- 默认后端未映射到宿主机端口，需在容器内执行或先映射端口。
- 在容器内执行示例：
```
docker exec skyroam-backend bash -lc "curl -s http://localhost:8001/health"
docker exec skyroam-backend bash -lc "curl -s http://localhost:8001/docs"
docker exec skyroam-backend bash -lc "curl -s http://localhost:8001/api/v1/openai/config"
docker exec skyroam-backend bash -lc "curl -s -X POST http://localhost:8001/api/v1/openai/test"
```
- 若已为后端添加端口映射（如 `18001:8001`），则宿主机可直接：
```
curl http://localhost:18001/health
curl http://localhost:18001/docs
curl http://localhost:18001/api/v1/openai/config
curl -X POST http://localhost:18001/api/v1/openai/test
```

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 性能监控
```bash
# 查看容器资源使用
docker stats

# 查看系统资源
htop
```

## 🛑 停止服务

### 停止所有服务
```bash
docker-compose down
```

### 停止并清理
```bash
# 停止服务并删除容器
docker-compose down --remove-orphans

# 停止服务并删除数据卷
docker-compose down -v
```

## 🔄 更新服务

### 更新代码
```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose build --no-cache
docker-compose up -d
```

### 更新依赖
```bash
# 后端依赖
cd backend
pip install -r requirements.txt --upgrade

# 前端依赖
cd frontend
npm update
```

## 📝 开发提示

### 热重载
- 后端: 使用 `--reload` 参数启动
- 前端: React 开发服务器自动热重载

### 调试模式
```bash
# 后端调试
cd backend
python -m debugpy --listen 5678 --wait-for-client main.py

# 前端调试
cd frontend
npm run start
```

### 代码格式化
```bash
# 后端代码格式化
cd backend
black .
isort .

# 前端代码格式化
cd frontend
npm run format
```

## 🆘 获取帮助

如果遇到问题，请：

1. 查看 [故障排除](#故障排除) 部分
2. 检查 [GitHub Issues](https://github.com/your-repo/issues)
3. 提交新的 Issue 描述问题
4. 联系开发团队

---

**祝您使用愉快！** 🎉

## 🐳 Docker 部署端口与访问
- `frontend`: 13000 -> 3000，宿主机访问 `http://localhost:13000`
- `backend`: 默认不对外暴露（容器内 `http://backend:8001`）；如需宿主机访问，添加 `ports: - "18001:8001"`
- `amap-mcp-api`: 13002 -> 3002，宿主机访问 `http://localhost:13002`
- `xhs-api`: 18002 -> 8002，宿主机访问 `http://localhost:18002`
- `flower`: 默认不对外暴露（容器内 `http://skyroam-flower:5555`）；如需宿主机访问，添加 `ports: - "15555:5555"`
- `postgres`: 仅内网，容器内 `postgres:5432`
- `redis`: 仅内网，容器内 `redis:6379`

### 说明
- 前端通过服务名 `backend` 访问后端，无需后端对外暴露即可正常工作。
- 需要在宿主机直接调用后端 API 或 Flower 时，再按需开启对应端口映射。
