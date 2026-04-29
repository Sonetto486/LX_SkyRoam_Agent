@echo off
chcp 65001 >nul

echo Starting LX SkyRoam Agent Dev Environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed. Please install Node.js 18+
    pause
    exit /b 1
)

REM Create necessary directories
echo Creating necessary directories...
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\uploads" mkdir backend\uploads

REM Start backend service
echo Starting backend service...
start "Backend" cmd /k "cd backend && call D:\Anaconda\Scripts\activate.bat skyroam && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Start frontend service
echo Starting frontend service...
start "Frontend" cmd /k "cd frontend && set \"REACT_APP_API_BASE_URL=http://localhost:8000/api/v1\" && npm start"

REM Wait for frontend to start
echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul

REM Show access info
echo.
echo LX SkyRoam Agent Dev Environment Started!
echo.
echo Frontend App: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Notes:
echo    - Ensure PostgreSQL is running
echo    - Ensure Redis is running
echo    - Create .env file in backend directory
echo.
echo To stop services: Close the respective command prompt windows
echo.

pause
