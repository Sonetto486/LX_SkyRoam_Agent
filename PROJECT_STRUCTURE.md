# SkyRoam 项目结构图

## 总览

```text
LX_SkyRoam_Agent/
├── backend/                     # 后端服务
├── frontend/                    # 前端应用
├── database/                    # 数据库初始化与结构脚本
├── docs/                        # 补充文档
├── scripts/                     # 通用脚本与数据处理工具
├── uploads/                     # 上传文件与静态资源
├── logs/                        # 运行日志
├── docker-compose.yml           # 容器编排
├── start*.bat / start*.sh       # 一键启动脚本
├── README.md                    # 项目入口说明
├── PROJECT_SUMMARY.md           # 项目总结
└── implementation_summary.md    # 功能实现总结
```

## 后端结构

```text
backend/
├── main.py                      # FastAPI 应用入口
├── requirements.txt             # Python 依赖
├── Dockerfile                   # 后端镜像构建
├── alembic.ini                  # 数据库迁移配置
├── alembic/                     # Alembic 迁移文件
├── app/
│   ├── api/                     # 路由层（REST / Stream API）
│   ├── core/                    # 配置、日志、数据库、安全等核心能力
│   ├── mcp/                     # MCP 服务与工具封装
│   ├── models/                  # ORM 数据模型
│   ├── schemas/                 # Pydantic 数据结构
│   ├── services/                # 业务服务层
│   ├── tasks/                   # Celery 异步任务
│   ├── tools/                   # 外部工具/客户端封装
│   └── platforms/               # 平台适配与爬虫相关逻辑
├── scripts/                     # 后端运维脚本
├── tests/                       # 后端测试
├── data/                        # 运行数据（如向量库、缓存文件）
├── logs/                        # 后端日志
└── uploads/                     # 后端上传文件
```

### 后端关键入口
- `backend/main.py`：后端应用启动入口
- `backend/app/api/v1/endpoints/openai.py`：AI 对话与配置接口
- `backend/app/core/config.py`：环境变量与全局配置
- `backend/app/core/logging_config.py`：日志初始化
- `backend/app/services/nlu_service.py`：意图识别与实体抽取

## 前端结构

```text
frontend/
├── package.json                 # 前端依赖与脚本
├── tsconfig.json                # TypeScript 配置
├── public/                      # 静态资源
└── src/
    ├── app/                     # 应用级组织代码
    ├── components/              # 通用组件
    │   ├── AIAssistant/         # 智能助手浮窗
    │   ├── Itinerary/           # 行程相关组件
    │   └── ...
    ├── config/                  # API 配置、常量配置
    ├── constants/               # 常量定义
    ├── contexts/                # React Context
    ├── pages/                   # 页面级组件
    │   ├── Admin/               # 管理后台页面
    │   ├── HomePage/            # 首页
    │   ├── ProfilePage/         # 个人中心
    │   └── ItineraryPage/        # 行程页
    ├── types/                   # TypeScript 类型
    ├── utils/                   # 通用工具函数
    └── index.tsx                # 前端入口
```

### 前端关键入口
- `frontend/src/index.tsx`：React 入口
- `frontend/src/App.tsx`：应用主路由
- `frontend/src/config/api.ts`：API 基础地址与端点配置
- `frontend/src/components/AIAssistant/AIAssistant.tsx`：智能助手组件
- `frontend/src/pages/`：各业务页面

## 数据库结构

```text
database/
├── init.sql                     # 初始化脚本
├── mysql_schema.sql             # MySQL 结构
├── mydb_struct.sql              # 数据结构说明
├── poi_pgvector_init.sql        # POI 向量库初始化
├── rag_pgvector_init.sql        # RAG 向量库初始化
└── rag_pgvector_init_en.sql     # 英文 RAG 向量库初始化
```

## 脚本结构

```text
scripts/
├── import_poi_dataset.py        # 导入 POI 数据
├── import_rag_dataset.py        # 导入 RAG 数据
└── test_poi_processing.py       # POI 数据处理测试
```

## 运行与配置

```text
根目录
├── docker-compose.yml           # 一键拉起后端、前端、数据库、缓存
├── env.example                  # 环境变量模板
├── start-all-win.bat            # Windows 一键启动
├── start-dev.bat / start-dev.sh # 开发模式启动
├── start.bat / start.sh         # 通用启动脚本
└── docs/                        # 补充说明文档
```

## 推荐阅读顺序

1. `README.md`：先了解项目定位与启动方式
2. `PROJECT_SUMMARY.md`：查看整体架构和功能概览
3. `PROJECT_STRUCTURE.md`：快速定位目录与文件职责
4. `frontend/src/config/api.ts`：查看前端接口入口
5. `backend/app/api/v1/endpoints/openai.py`：查看 AI 接口实现

## 目录职责速查

- **`backend/app/api`**：对外接口层
- **`backend/app/services`**：核心业务逻辑
- **`backend/app/core`**：配置、日志、数据库、安全
- **`frontend/src/components`**：可复用 UI 组件
- **`frontend/src/pages`**：页面与业务入口
- **`database`**：表结构与初始化脚本
- **`scripts`**：导入、测试、数据处理脚本

## 备注

- 本结构图按照当前仓库内容整理，适合快速定位代码与功能模块。
- 如果后续新增模块，建议同步更新本文件与 `PROJECT_SUMMARY.md`。
