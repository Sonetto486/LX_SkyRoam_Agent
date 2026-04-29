@echo off
chcp 65001 >/dev/null
setlocal enabledelayedexpansion

echo Starting LX SkyRoam Agent Services...

cd /d "%~dp0"

set "CONDA_ENV=D:\python\anaconda3\envs\travel"
set "PYTHON_EXE=%CONDA_ENV%\python.exe"
set "BACKEND_DIR=%cd%\backend"
set "FRONTEND_DIR=%cd%\frontend"

echo Using Conda Environment: %CONDA_ENV%

echo Starting FastAPI Backend...
start "Backend API" cmd /k "cd /d %BACKEND_DIR% && set PYTHONPATH=%BACKEND_DIR% && %PYTHON_EXE% -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

echo Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %BACKEND_DIR% && set PYTHONPATH=%BACKEND_DIR% && %PYTHON_EXE% -m celery -A app.core.celery worker --loglevel=info --pool=threads"

echo Starting Amap API Service...
start "Gaode API" cmd /k "cd /d %BACKEND_DIR% && set PYTHONPATH=%BACKEND_DIR% && %PYTHON_EXE% mcp_http_server_amap.py"

echo Starting XHS API Service...
start "XHS API" cmd /k "cd /d %BACKEND_DIR% && set PYTHONPATH=%BACKEND_DIR% && %PYTHON_EXE% xhs_api_server.py"

echo Starting Frontend...
start "Frontend" cmd /k "cd /d %FRONTEND_DIR% && set REACT_APP_API_BASE_URL=http://localhost:8001/api/v1 && npm start"

echo.
echo All services started in separate windows.
echo Close each window to stop the corresponding service.
echo.

pause
endlocal
