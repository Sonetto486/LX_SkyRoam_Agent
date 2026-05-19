# LX SkyRoam Agent - 智能旅游攻略生成系统

## 环境依赖

### 基础环境
| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 后端开发语言 |
| Node.js | 18+ | 前端开发语言 |
| Redis | 7.0+ | 缓存和消息队列 |
| PostgreSQL | 15+ | 关系型数据库 |

### Python依赖库
| 库名 | 版本 | 作用 |
|------|------|------|
| fastapi | 0.115.0 | 高性能API框架 |
| uvicorn | 0.24.0 | ASGI服务器 |
| sqlalchemy | 2.0+ | ORM数据库操作 |
| asyncpg | 0.28.0 | PostgreSQL异步驱动 |
| celery | 5.3+ | 异步任务队列 |
| redis | 5.0+ | Redis客户端 |
| pydantic | 2.0+ | 数据验证 |
| openai | 1.0+ | OpenAI API客户端 |
| numpy | 1.26+ | 数值计算 |
| scikit-learn | 1.3+ | 机器学习算法 |
| playwright | 1.40+ | 网页爬虫 |
| sse-starlette | 1.6.5 | Server-Sent Events支持 |
| python-dotenv | 1.0+ | 环境变量加载 |
| requests | 2.31+ | HTTP请求 |

### Node.js依赖库
| 库名 | 版本 | 作用 |
|------|------|------|
| react | 18+ | 前端框架 |
| react-dom | 18+ | DOM操作 |
| react-router-dom | 6+ | 路由管理 |
| typescript | 5.0+ | 类型安全 |
| antd | 5.0+ | UI组件库 |
| @ant-design/icons | 5.0+ | 图标库 |
| leaflet | 1.9+ | 地图组件 |
| react-leaflet | 4.0+ | React地图封装 |
| axios | 1.6+ | HTTP客户端 |

## 配置说明

### 后端配置 (backend/.env)

```env
# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/skyroam

# Redis配置
REDIS_URL=redis://localhost:6379/0

# AI配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your-dashscope-api-key

# 地图服务配置
AMAP_API_KEY=your-amap-api-key

# OCR配置
BAIDU_OCR_API_KEY=your-baidu-ocr-key
BAIDU_OCR_SECRET_KEY=your-baidu-ocr-secret
```

### 前端配置 (frontend/.env)

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_MAP_PROVIDER=amap
```

## 使用说明

### 安装步骤



1. **后端安装**
```bash
cd backend
pip install -r requirements.txt
```

2. **前端安装**
```bash
cd frontend
npm install
```

3. **数据库初始化**
```bash
cd backend
# 创建数据库表
python -c "from app.core.database import init_db; init_db()"
```

### 启动服务

**开发模式**

```bash
# 启动Redis
redis-server

# 启动PostgreSQL（确保已配置好）

# 启动后端
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 启动Celery Worker（新终端）
cd backend
celery -A app.core.celery worker --loglevel=info --pool=solo

# 启动前端（新终端）
cd frontend
npm start
```



### 功能使用

1. **智能导入**
   - 支持文本粘贴导入
   - 支持小红书链接导入
   - 支持图片OCR导入

2. **一键规划**
   - 输入目的地、日期、预算
   - 选择旅行偏好
   - 自动生成多个方案供选择

3. **行程管理**
   - 查看、编辑、删除行程
   - 拖拽调整景点顺序
   - 移动景点到不同天数

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/travel-plans/` | GET/POST | 行程列表/创建行程 |
| `/api/v1/travel-plans/{id}` | GET/PUT/DELETE | 行程详情/更新/删除 |
| `/api/v1/travel-plans/{id}/generate` | POST | 生成旅行方案 |
| `/api/v1/smart-import/import` | POST | 智能导入 |
| `/api/v1/openai/chat` | POST | AI对话 |
| `/api/v1/health` | GET | 健康检查 |

## 项目结构

```
LX_SkyRoam_Agent/
├── backend/
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   ├── services/       # 业务逻辑
│   │   ├── tools/          # 工具类
│   │   └── platforms/      # 第三方平台集成
│   ├── requirements.txt    # Python依赖
│   └── main.py             # 应用入口
├── frontend/
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   └── utils/          # 工具函数
│   └── package.json        # npm依赖
├── database/
│   └── migrations/         # 数据库迁移
└── docs/                   # 文档
```