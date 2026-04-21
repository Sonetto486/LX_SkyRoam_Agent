@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🚀 正在启动 LX SkyRoam Agent 全量服务...

cd /d "%~dp0"

set "CONDA_ENV=D:\Anaconda\envs\skyroam"
set "ACTIVATE_SCRIPT=D:\Anaconda\Scripts\activate.bat"
set "BACKEND_DIR=%cd%\backend"
set "FRONTEND_DIR=%cd%\frontend"

call :check_node || goto :end

echo 🔁 使用 Conda 环境: %CONDA_ENV%

echo 🐍 启动 FastAPI 后端...
start "Backend API" cmd /k "cd /d %BACKEND_DIR% && call %ACTIVATE_SCRIPT% %CONDA_ENV% && uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

echo ⚙️ 启动 Celery Worker...
start "Celery Worker" cmd /k "cd /d %BACKEND_DIR% && call %ACTIVATE_SCRIPT% %CONDA_ENV% && celery -A app.core.celery worker --loglevel=info"

echo 🗺️ 启动高德 API 服务...
start "Gaode API" cmd /k "cd /d %BACKEND_DIR% && call %ACTIVATE_SCRIPT% %CONDA_ENV% && python mcp_http_server_amap.py"

echo 📈 启动小红书采集服务...
start "XHS API" cmd /k "cd /d %BACKEND_DIR% && call %ACTIVATE_SCRIPT% %CONDA_ENV% && python xhs_api_server.py"

echo ⚛️ 启动前端应用...
start "Frontend" cmd /k "cd /d %FRONTEND_DIR% && call %ACTIVATE_SCRIPT% %CONDA_ENV% && set \"REACT_APP_API_BASE_URL=http://localhost:8001/api/v1\" && npm start"

echo.
echo ✅ 所有进程已在独立窗口中启动。

echo 🛑 如需停止某个服务，直接关闭对应窗口即可。
echo.
goto :end

:check_node
where node >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Node.js，请先安装 Node.js 18+。
    exit /b 1
)
exit /b 0

:end
pause
endlocal

