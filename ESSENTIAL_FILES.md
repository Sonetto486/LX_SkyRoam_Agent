# SkyRoam 项目必需文件清单

## 📋 概述

本文档列出项目运行必需的文件，以及可以安全删除的文件。

---

## ✅ 必需保留的文件

### 后端核心文件 (backend/)

#### 1. 应用入口和配置
```
backend/
├── main.py                          # FastAPI 应用入口（必需）
├── requirements.txt                  # Python 依赖（必需）
├── alembic.ini                       # 数据库迁移配置（必需）
├── .env.example                      # 环境变量模板（必需）
├── Dockerfile                        # Docker 构建文件（必需）
├── Dockerfile.prod                   # 生产环境 Dockerfile（必需）
└── .dockerignore                     # Docker 忽略文件（必需）
```

#### 2. 核心模块 (backend/app/core/)
```
backend/app/core/
├── __init__.py                       # 包初始化（必需）
├── config.py                         # 应用配置（必需）
├── database.py                       # 数据库连接（必需）
├── redis.py                          # Redis 连接（必需）
├── celery.py                         # Celery 配置（必需）
├── security.py                       # 安全认证（必需）
├── logging_config.py                 # 日志配置（必需）
├── rate_limit.py                     # 限流中间件（必需）
└── async_loop.py                     # 异步循环（必需）
```

#### 3. API 路由 (backend/app/api/)
```
backend/app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── api.py                        # 路由汇总（必需）
    ├── smart_chat.py                  # 智能对话路由（必需）
    └── endpoints/
        ├── __init__.py
        ├── auth.py                    # 认证（必需）
        ├── travel_plans.py            # 旅行计划（必需）
        ├── destinations.py            # 目的地（必需）
        ├── locations.py               # 地点搜索（必需）
        ├── map.py                      # 地图服务（必需）
        ├── smart_import.py            # 智能导入（必需）
        ├── smart_planner.py           # 智能规划（必需）
        ├── attraction_details.py      # 景点详情（必需）
        ├── users.py                   # 用户管理（必需）
        ├── topics.py                  # 话题（必需）
        ├── notes.py                   # 笔记（必需）
        ├── weather.py                 # 天气（必需）
        ├── image_import.py            # 图片导入（必需）
        ├── pre_generation.py          # 预生成（必需）
        └── xiaohongshu.py             # 小红书（可选，如需爬虫）
```

#### 4. 数据模型 (backend/app/models/)
```
backend/app/models/
├── __init__.py
├── base.py                            # 基础模型（必需）
├── user.py                            # 用户模型（必需）
├── travel_plan.py                     # 旅行计划模型（必需）
├── destination.py                     # 目的地模型（必需）
├── attraction_detail.py               # 景点详情模型（必需）
├── topic.py                           # 话题模型（必需）
├── location.py                        # 地点模型（必需）
├── hot_destination.py                 # 热门目的地（必需）
└── pre_generated_plan.py              # 预生成计划（必需）
```

#### 5. 服务层 (backend/app/services/)
```
backend/app/services/
├── __init__.py
├── plan_generator.py                  # 方案生成核心（必需）
├── travel_plan_service.py             # 计划服务（必需）
├── agent_service.py                   # Agent 服务（必需）
├── route_optimizer.py                 # 路线优化（必需）
├── itinerary_optimizer.py             # 行程优化（必需）
├── plan_scorer.py                     # 方案评分（必需）
├── background_tasks.py                # 后台任务（必需）
├── data_collector.py                  # 数据采集（必需）
├── attraction_detail_service.py      # 景点详情服务（必需）
├── detail_enrichment_service.py       # 详情丰富（必需）
├── poi_retriever.py                   # POI 检索（必需）
├── rag_retriever.py                   # RAG 检索（必需）
├── pre_generation_service.py          # 预生成服务（必需）
├── pre_plan_matcher.py                # 计划匹配（必需）
└── plan_generation/                   # 模块化生成（必需）
    ├── __init__.py
    ├── daily.py                       # 每日生成
    ├── budget_calculator.py           # 预算计算
    └── retry_manager.py               # 重试管理
```

#### 6. 工具层 (backend/app/tools/)
```
backend/app/tools/
├── __init__.py
├── amap_rest_client.py                # 高德地图客户端（必需）
├── unified_map_service.py             # 统一地图服务（必需）
├── openai_client.py                   # LLM 客户端（必需）
├── smart_planner.py                   # 智能规划器（必需）
├── city_resolver.py                   # 城市解析（必需）
├── place_image_service.py             # 图片服务（必需）
├── unsplash_service.py                # Unsplash 图片（必需）
├── wikimedia_service.py               # Wikimedia 图片（必需）
├── baidu_ocr_service.py               # 百度 OCR（必需）
├── baidu_maps_integration.py         # 百度地图（可选）
└── tianditu_maps_integration.py       # 天地图（可选）
```

#### 7. Celery 任务 (backend/app/tasks/)
```
backend/app/tasks/
├── __init__.py
├── travel_plan_tasks.py               # 旅行计划任务（必需）
├── background_tasks.py                # 后台任务（必需）
├── data_collection_tasks.py           # 数据采集任务（必需）
└── pre_generation_tasks.py            # 预生成任务（必需）
```

#### 8. 数据模型 (backend/app/schemas/)
```
backend/app/schemas/
├── __init__.py
├── auth.py                            # 认证 Schema（必需）
├── travel_plan.py                     # 计划 Schema（必需）
└── pre_generated_plan.py              # 预生成 Schema（必需）
```

#### 9. 数据库迁移 (backend/alembic/)
```
backend/alembic/
├── env.py                             # Alembic 环境（必需）
├── versions/                          # 迁移版本（必需）
│   └── *.py
```

#### 10. 小红书爬虫（可选，如需爬虫功能）
```
backend/app/platforms/xhs/             # 小红书爬虫模块（可选）
backend/xhs_api_server.py              # 小红书 API 服务（可选）
backend/xhs_login_helper.py            # 登录辅助（可选）
```

#### 11. MCP 服务（可选）
```
backend/mcp_http_server_amap.py        # 高德 MCP 服务（可选）
backend/app/mcp/                       # MCP 模块（可选）
```

---

### 前端核心文件 (frontend/)

#### 1. 配置文件
```
frontend/
├── package.json                       # NPM 配置（必需）
├── package-lock.json                  # 依赖锁定（必需）
├── tsconfig.json                      # TypeScript 配置（必需）
├── tailwind.config.js                 # Tailwind 配置（必需）
├── Dockerfile                         # Docker 构建文件（必需）
├── Dockerfile.prod                    # 生产环境 Dockerfile（必需）
├── .dockerignore                      # Docker 忽略文件（必需）
├── nginx.conf                         # Nginx 配置（必需）
└── public/
    ├── index.html                     # HTML 模板（必需）
    ├── manifest.json                  # PWA 配置（必需）
    ├── favicon.ico                    # 图标（必需）
    ├── robots.txt                     # 爬虫配置（必需）
    ├── css/                           # 样式文件（必需）
    └── images/                        # 图片资源（必需）
```

#### 2. 源代码入口
```
frontend/src/
├── index.tsx                          # 应用入口（必需）
├── App.tsx                            # 根组件（必需）
├── react-app-env.d.ts                 # TypeScript 声明（必需）
└── declarations.d.ts                 # 类型声明（必需）
```

#### 3. 路由配置
```
frontend/src/app/router/
├── AppRoutes.tsx                      # 路由配置（必需）
└── RouterApp.tsx                      # 路由组件（必需）
```

#### 4. 配置文件
```
frontend/src/config/
├── api.ts                             # API 配置（必需）
└── map.ts                             # 地图配置（必需）
```

#### 5. 工具函数
```
frontend/src/utils/
├── auth.ts                            # 认证工具（必需）
├── navigation.ts                      # 导航工具（必需）
├── searchUtils.ts                     # 搜索工具（必需）
└── upgradeNotice.ts                   # 升级通知（可选）
```

#### 6. 常量
```
frontend/src/constants/
└── travel.ts                          # 旅行常量（必需）
```

#### 7. 上下文
```
frontend/src/contexts/
└── ThemeContext.tsx                   # 主题上下文（必需）
```

#### 8. 布局组件
```
frontend/src/components/Layout/
├── Layout.tsx                         # 布局组件（必需）
└── MainLayout.tsx                     # 主布局（必需）
```

#### 9. 功能组件
```
frontend/src/components/
├── AIAssistant/
│   ├── AIAssistant.tsx                # AI 助手（必需）
│   └── index.ts
├── MapComponent/
│   ├── MapComponent.tsx               # 地图组件（必需）
│   └── index.ts
├── AttractionImageCarousel/
│   └── AttractionImageCarousel.tsx    # 图片轮播（必需）
├── Auth/
│   └── RequireAdmin.tsx               # 管理员权限（必需）
├── Itinerary/                         # 行程组件（必需）
│   ├── ActivityEditModal.tsx
│   ├── AttractionsSection.tsx
│   ├── DateRangeEditor.tsx
│   ├── DayScheduleSection.tsx
│   ├── DetailModal.tsx
│   ├── EnhancedActivityCard.tsx
│   ├── HotelSection.tsx
│   ├── LocationSearch.tsx
│   ├── MealsSection.tsx
│   ├── RouteSegment.tsx
│   ├── TransportSection.tsx
│   ├── WeatherCard.tsx
│   └── index.ts
├── SystemUpgradeNotice/               # 系统升级通知（可选）
└── __init__.ts
```

#### 10. 页面组件
```
frontend/src/pages/
├── __init__.ts
├── common.css                         # 公共样式（必需）
├── HomePage/                          # 首页（必需）
│   └── HomePage.tsx
├── LoginPage/                         # 登录（必需）
│   └── LoginPage.tsx
├── RegisterPage/                      # 注册（必需）
│   └── RegisterPage.tsx
├── ProfilePage/                       # 个人中心（必需）
│   └── ProfilePage.tsx
├── AboutPage/                         # 关于页面（必需）
│   └── AboutPage.tsx
├── DiscoverPage/                      # 发现页面（必需）
│   └── DiscoverPage.tsx
├── ItineraryPage/                     # 行程页面（必需）
│   ├── ItineraryListPage.tsx
│   └── ItineraryWorkspace.tsx
├── PlanGeneratorPage/                 # 方案生成（必需）
│   └── PlanGeneratorPage.tsx
├── ImportPage/                        # 智能导入（必需）
│   └── SmartImportPage.tsx
├── DestinationsPage/                  # 目的地（必需）
│   └── DestinationsPage.tsx
├── PlanDetailPage/                    # 计划详情（必需）
│   └── PlanDetailPage.tsx
├── PlanEditPage/                      # 计划编辑（必需）
│   └── PlanEditPage.tsx
├── PlansLibraryPage/                  # 计划库（必需）
│   └── PlansLibraryPage.tsx
├── PublicPlansPage/                   # 公开计划（必需）
│   └── PublicPlansPage.tsx
├── TopicsPage/                        # 话题页面（必需）
│   └── TopicsPage.tsx
├── TopicLibraryPage/                  # 话题库（必需）
│   └── TopicLibraryPage.tsx
├── TopicDetailPage/                   # 话题详情（必需）
│   └── TopicDetailPage.tsx
├── NotesPage/                         # 笔记页面（必需）
│   └── NotesPage.tsx
├── NoteDetailPage/                    # 笔记详情（必需）
│   └── NoteDetailPage.tsx
├── PlaceDetailPage/                   # 地点详情（必需）
│   └── PlaceDetailPage.tsx
├── TravelPlanPage/                    # 旅行计划（必需）
│   └── TravelPlanPage.tsx
└── Admin/                             # 管理员页面（必需）
    ├── UsersAdminPage.tsx
    ├── AttractionDetailsAdminPage.tsx
    ├── HistoryAdminPage.tsx
    └── UpgradeControlPage/
        └── UpgradeControlPage.tsx
```

---

### 项目根目录文件

```
/
├── docker-compose.yml                 # 开发环境 Docker（必需）
├── docker-compose.prod.yml            # 生产环境 Docker（必需）
├── .env.docker                        # Docker 环境变量（必需）
├── .env.docker.prod.example           # 生产环境变量模板（必需）
├── CLAUDE.md                          # 项目说明（必需）
├── README.md                          # 项目文档（必需）
├── DOCKER_DEPLOY.md                   # Docker 部署文档（必需）
├── deploy.sh                          # Linux 部署脚本（必需）
├── deploy.bat                         # Windows 部署脚本（必需）
├── start-dev.sh                       # Linux 开发启动（必需）
├── start-dev.bat                      # Windows 开发启动（必需）
├── start-all-win.bat                  # Windows 全启动（必需）
└── database/                          # 数据库脚本（必需）
    ├── init.sql                       # 初始化脚本
    ├── poi_pgvector_init.sql          # POI 向量初始化
    ├── rag_pgvector_init.sql          # RAG 向量初始化
    └── pre_generation_tables.sql      # 预生成表
```

---

## ❌ 可以删除的文件

### 后端可删除文件

```
backend/
├── tests/                             # 测试文件（可删除）
│   └── test_*.py
├── scripts/                           # 数据脚本（可删除）
│   ├── add_*.py
│   ├── check_*.py
│   ├── import_*.py
│   ├── init_*.py
│   ├── preset_*.py
│   └── update_*.py
├── data/                              # 临时数据（可删除）
│   └── cookies/
├── docs/                              # 文档（可删除）
│   └── redis-cloud.md
├── .pytest_cache/                     # 测试缓存（可删除）
├── __pycache__/                       # Python 缓存（可删除）
├── logs/                              # 日志目录（运行时生成）
├── uploads/                           # 上传目录（运行时生成）
├── browser_data/                      # 浏览器数据（可删除）
├── check_data.py                      # 检查脚本（可删除）
├── fill_data.py                       # 填充数据（可删除）
├── fill_data_sql.py                   # SQL 填充（可删除）
├── seed_topics.py                     # 种子数据（可删除）
├── test_celery_cleanup.py             # 测试文件（可删除）
├── update_destinations_table.py       # 更新脚本（可删除）
├── update_travel_plan_tables.py       # 更新脚本（可删除）
├── update_users_table.py              # 更新脚本（可删除）
├── init_db.py                         # 初始化脚本（可删除）
├── mock_flight_data.json              # 模拟数据（可删除）
├── .env                               # 实际环境变量（敏感，不提交）
├── .env.backup                        # 备份文件（可删除）
└── app/
    ├── __pycache__/                   # Python 缓存（可删除）
    └── */__pycache__/                 # 所有子目录缓存（可删除）
```

### 前端可删除文件

```
frontend/
├── build/                             # 构建产物（可删除）
├── node_modules/                      # 依赖包（可删除）
├── .npm/                              # NPM 缓存（可删除）
├── lx-skyroam-agent-frontend@1.0.0    # 临时文件（可删除）
├── .env                               # 实际环境变量（敏感）
├── .env.development                   # 开发环境变量（可删除）
└── src/
    ├── pages/
    │   ├── TestPage/                  # 测试页面（可删除）
    │   └── TestDataExtraction.tsx     # 测试组件（可删除）
    └── utils/
        ├── testUpgradeNotice.ts       # 测试文件（可删除）
        └── upgradeNoticeReset.ts      # 测试文件（可删除）
```

### 项目根目录可删除文件

```
/
├── .pytest_cache/                     # 测试缓存（可删除）
├── .idea/                             # IDE 配置（可删除）
├── logs/                              # 日志目录（运行时生成）
├── uploads/                           # 上传目录（运行时生成）
├── data/                              # 临时数据（可删除）
├── POIs_V2.csv                        # 大数据文件（可删除）
├── travel_guide.xlsx                  # Excel 文件（可删除）
├── plan.json                          # 临时文件（可删除）
├── build_index.py                     # 构建脚本（可删除）
├── diagnose.py                        # 诊断脚本（可删除）
├── rebuild_final.py                   # 重建脚本（可删除）
├── rebuild_v2.py                      # 重建脚本（可删除）
├── rebuild_with_desc2.py              # 重建脚本（可删除）
├── replace_function.py                # 替换脚本（可删除）
├── seed_china_data.sql                # 种子数据（可删除）
├── seed_plans.sql                     # 种子数据（可删除）
├── tash                               # 临时文件（可删除）
├── DESIGN.md                          # 设计文档（可删除）
├── PPT_OUTLINE.md                     # PPT 大纲（可删除）
├── PROJECT_REPORT.md                  # 项目报告（可删除）
├── PROJECT_STRUCTURE.md               # 项目结构（可删除）
├── PROJECT_SUMMARY.md                 # 项目总结（可删除）
├── QUICK_START.md                     # 快速开始（可删除）
├── RAG_README.md                      # RAG 文档（可删除）
├── new_readme.md                      # 旧文档（可删除）
├── implementation_summary.md          # 实现总结（可删除）
├── env.example                        # 旧环境变量（可删除）
├── start.bat                          # 旧启动脚本（可删除）
├── start.sh                           # 旧启动脚本（可删除）
├── 交通方案显示Bug修复说明.md           # 开发文档（可删除）
├── 行程功能工作总结.md                 # 开发文档（可删除）
├── 行程功能讲解文稿.txt                # 开发文档（可删除）
├── 行程概览显示修复说明.md             # 开发文档（可删除）
├── 行程页面改进说明.md                 # 开发文档（可删除）
├── 配置和使用说明.txt                  # 开发文档（可删除）
├── 项目的开发环境及依赖库说明.txt       # 开发文档（可删除）
└── 项目设计计划.md                     # 开发文档（可删除）
```

---

## 📊 文件统计

| 类别 | 必需文件数 | 可删除文件数 |
|------|-----------|-------------|
| 后端 Python | ~80 | ~40 |
| 前端 TS/TSX | ~60 | ~5 |
| 配置文件 | ~20 | ~10 |
| 文档文件 | ~5 | ~20 |
| 数据文件 | ~5 | ~5 |
| **总计** | **~170** | **~80** |

---

## 🗑️ 一键清理脚本

创建 `cleanup.sh`（Linux/Mac）：

```bash
#!/bin/bash
# 清理非必需文件

echo "开始清理..."

# 后端清理
rm -rf backend/tests/
rm -rf backend/scripts/
rm -rf backend/data/
rm -rf backend/docs/
rm -rf backend/.pytest_cache/
rm -rf backend/__pycache__/
rm -rf backend/app/__pycache__/
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

rm -f backend/check_data.py
rm -f backend/fill_data.py
rm -f backend/fill_data_sql.py
rm -f backend/seed_topics.py
rm -f backend/test_celery_cleanup.py
rm -f backend/update_*.py
rm -f backend/init_db.py
rm -f backend/mock_flight_data.json
rm -f backend/.env.backup

# 前端清理
rm -rf frontend/build/
rm -rf frontend/node_modules/
rm -rf frontend/.npm/
rm -f frontend/lx-skyroam-agent-frontend@1.0.0
rm -rf frontend/src/pages/TestPage/
rm -f frontend/src/pages/TestDataExtraction.tsx
rm -f frontend/src/utils/testUpgradeNotice.ts
rm -f frontend/src/utils/upgradeNoticeReset.ts

# 根目录清理
rm -rf .pytest_cache/
rm -rf .idea/
rm -rf data/
rm -f POIs_V2.csv
rm -f travel_guide.xlsx
rm -f plan.json
rm -f build_index.py
rm -f diagnose.py
rm -f rebuild_*.py
rm -f replace_function.py
rm -f seed_*.sql
rm -f tash
rm -f DESIGN.md
rm -f PPT_OUTLINE.md
rm -f PROJECT_REPORT.md
rm -f PROJECT_STRUCTURE.md
rm -f PROJECT_SUMMARY.md
rm -f QUICK_START.md
rm -f RAG_README.md
rm -f new_readme.md
rm -f implementation_summary.md
rm -f env.example
rm -f start.bat
rm -f start.sh
rm -f *.md.bak
rm -f 交通方案显示Bug修复说明.md
rm -f 行程功能工作总结.md
rm -f 行程功能讲解文稿.txt
rm -f 行程概览显示修复说明.md
rm -f 行程页面改进说明.md
rm -f 配置和使用说明.txt
rm -f 项目的开发环境及依赖库说明.txt
rm -f 项目设计计划.md

echo "清理完成！"
```

创建 `cleanup.bat`（Windows）：

```batch
@echo off
REM 清理非必需文件

echo 开始清理...

REM 后端清理
rd /s /q backend\tests 2>nul
rd /s /q backend\scripts 2>nul
rd /s /q backend\data 2>nul
rd /s /q backend\docs 2>nul
rd /s /q backend\.pytest_cache 2>nul
rd /s /q backend\__pycache__ 2>nul
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

del /q backend\check_data.py 2>nul
del /q backend\fill_data.py 2>nul
del /q backend\fill_data_sql.py 2>nul
del /q backend\seed_topics.py 2>nul
del /q backend\test_celery_cleanup.py 2>nul
del /q backend\update_*.py 2>nul
del /q backend\init_db.py 2>nul
del /q backend\mock_flight_data.json 2>nul
del /q backend\.env.backup 2>nul

REM 前端清理
rd /s /q frontend\build 2>nul
rd /s /q frontend\node_modules 2>nul
rd /s /q frontend\.npm 2>nul
del /q frontend\lx-skyroam-agent-frontend@1.0.0 2>nul
rd /s /q frontend\src\pages\TestPage 2>nul
del /q frontend\src\pages\TestDataExtraction.tsx 2>nul
del /q frontend\src\utils\testUpgradeNotice.ts 2>nul
del /q frontend\src\utils\upgradeNoticeReset.ts 2>nul

REM 根目录清理
rd /s /q .pytest_cache 2>nul
rd /s /q .idea 2>nul
rd /s /q data 2>nul
del /q POIs_V2.csv 2>nul
del /q travel_guide.xlsx 2>nul
del /q plan.json 2>nul
del /q build_index.py 2>nul
del /q diagnose.py 2>nul
del /q rebuild_*.py 2>nul
del /q replace_function.py 2>nul
del /q seed_*.sql 2>nul
del /q tash 2>nul
del /q DESIGN.md 2>nul
del /q PPT_OUTLINE.md 2>nul
del /q PROJECT_REPORT.md 2>nul
del /q PROJECT_STRUCTURE.md 2>nul
del /q PROJECT_SUMMARY.md 2>nul
del /q QUICK_START.md 2>nul
del /q RAG_README.md 2>nul
del /q new_readme.md 2>nul
del /q implementation_summary.md 2>nul
del /q env.example 2>nul
del /q start.bat 2>nul
del /q start.sh 2>nul
del /q 交通方案显示Bug修复说明.md 2>nul
del /q 行程功能工作总结.md 2>nul
del /q 行程功能讲解文稿.txt 2>nul
del /q 行程概览显示修复说明.md 2>nul
del /q 行程页面改进说明.md 2>nul
del /q 配置和使用说明.txt 2>nul
del /q 项目的开发环境及依赖库说明.txt 2>nul
del /q 项目设计计划.md 2>nul

echo 清理完成！
pause
```

---

## ⚠️ 注意事项

1. **删除前备份**：建议在删除前创建 Git 分支或备份
2. **环境变量**：`.env` 文件包含敏感信息，不应提交到版本控制
3. **运行时目录**：`logs/`、`uploads/` 等目录会在运行时自动创建
4. **依赖安装**：删除 `node_modules/` 后需要重新运行 `npm install`
5. **测试文件**：如果需要运行测试，不要删除 `tests/` 目录

---

## 📝 最小化部署包

如果需要创建最小化的部署包，只需保留以下文件：

```
skyroam-minimal/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   ├── Dockerfile.prod
│   ├── .dockerignore
│   └── app/                          # 整个 app 目录
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── Dockerfile.prod
│   ├── .dockerignore
│   ├── nginx.conf
│   ├── public/                       # 整个 public 目录
│   └── src/                          # 整个 src 目录（删除测试文件）
├── database/
│   ├── init.sql
│   ├── poi_pgvector_init.sql
│   └── rag_pgvector_init.sql
├── nginx/
│   ├── nginx.conf
│   └── conf.d/default.conf
├── docker-compose.prod.yml
├── .env.docker.prod.example
├── CLAUDE.md
├── README.md
├── DOCKER_DEPLOY.md
├── deploy.sh
└── deploy.bat
```

预计大小：约 5-10 MB（不含 node_modules）
