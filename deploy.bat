@echo off
REM SkyRoam Windows 一键部署脚本

echo 🚀 SkyRoam Docker 部署脚本
echo ==========================

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装
    pause
    exit /b 1
)

REM 检查配置文件
if not exist ".env.docker.prod" (
    echo ⚠️  未找到 .env.docker.prod 配置文件
    echo 📝 正在从模板创建配置文件...
    copy .env.docker.prod.example .env.docker.prod
    echo ✅ 配置文件已创建: .env.docker.prod
    echo.
    echo ⚠️  请编辑配置文件，填入你的 API 密钥后再运行此脚本
    echo.
    echo 必须配置的项：
    echo   - POSTGRES_PASSWORD（数据库密码）
    echo   - SECRET_KEY（应用密钥）
    echo   - OPENAI_API_KEY（LLM API 密钥）
    echo   - AMAP_API_KEY（高德地图 API 密钥）
    pause
    exit /b 1
)

echo 🔍 检查配置...
echo ⚠️  请确保已配置以下关键项：
echo   - POSTGRES_PASSWORD
echo   - SECRET_KEY
echo   - OPENAI_API_KEY
echo   - AMAP_API_KEY
echo.
set /p confirm="配置已完成？按 Y 继续: "
if /i not "%confirm%"=="Y" (
    echo 请先完成配置
    pause
    exit /b 1
)

echo ✅ 配置检查通过

REM 构建镜像
echo.
echo 🔨 构建 Docker 镜像...
docker compose -f docker-compose.prod.yml build

REM 启动服务
echo.
echo 🚀 启动服务...
docker compose -f docker-compose.prod.yml up -d

REM 等待服务就绪
echo.
echo ⏳ 等待服务启动（约 30 秒）...
timeout /t 30 /nobreak >nul

REM 检查服务状态
echo.
echo 📊 服务状态:
docker compose -f docker-compose.prod.yml ps

echo.
echo ✅ 部署完成！
echo.
echo 访问地址:
echo   🌐 前端页面: http://localhost
echo   📚 API 文档: http://localhost/docs
echo   🔧 健康检查: http://localhost/health
echo.
echo 常用命令:
echo   查看日志: docker compose -f docker-compose.prod.yml logs -f
echo   停止服务: docker compose -f docker-compose.prod.yml down
echo   重启服务: docker compose -f docker-compose.prod.yml restart
echo.
pause