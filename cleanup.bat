@echo off
REM SkyRoam 项目清理脚本
REM 删除所有非必需文件，保留运行所需的核心文件

echo 🗑️  SkyRoam 项目清理脚本
echo ========================
echo.
echo ⚠️  警告：此操作将删除测试文件、临时文件、文档等非必需内容
echo ⚠️  建议先提交 Git 或创建备份
echo.
set /p confirm="确认继续？(y/N): "
if /i not "%confirm%"=="y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo 开始清理...

REM ============ 后端清理 ============
echo 📦 清理后端...

REM 删除测试目录
if exist backend\tests rd /s /q backend\tests 2>nul && echo   ✓ 删除 tests\

REM 删除脚本目录
if exist backend\scripts rd /s /q backend\scripts 2>nul && echo   ✓ 删除 scripts\

REM 删除临时数据
if exist backend\data rd /s /q backend\data 2>nul && echo   ✓ 删除 data\
if exist backend\browser_data rd /s /q backend\browser_data 2>nul && echo   ✓ 删除 browser_data\

REM 删除文档
if exist backend\docs rd /s /q backend\docs 2>nul && echo   ✓ 删除 docs\

REM 删除缓存
if exist backend\.pytest_cache rd /s /q backend\.pytest_cache 2>nul && echo   ✓ 删除 .pytest_cache\
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo   ✓ 删除所有 __pycache__\

REM 删除临时文件
del /q backend\check_data.py 2>nul
del /q backend\fill_data.py 2>nul
del /q backend\fill_data_sql.py 2>nul
del /q backend\seed_topics.py 2>nul
del /q backend\test_celery_cleanup.py 2>nul
del /q backend\update_destinations_table.py 2>nul
del /q backend\update_travel_plan_tables.py 2>nul
del /q backend\update_users_table.py 2>nul
del /q backend\init_db.py 2>nul
del /q backend\mock_flight_data.json 2>nul
del /q backend\.env.backup 2>nul
echo   ✓ 删除临时 Python 文件

REM ============ 前端清理 ============
echo.
echo 📦 清理前端...

REM 删除构建产物
if exist frontend\build rd /s /q frontend\build 2>nul && echo   ✓ 删除 build\

REM 删除缓存
if exist frontend\.npm rd /s /q frontend\.npm 2>nul && echo   ✓ 删除 .npm\

REM 删除临时文件
del /q "frontend\lx-skyroam-agent-frontend@1.0.0" 2>nul
if exist frontend\src\pages\TestPage rd /s /q frontend\src\pages\TestPage 2>nul && echo   ✓ 删除 TestPage\
del /q frontend\src\pages\TestDataExtraction.tsx 2>nul
del /q frontend\src\utils\testUpgradeNotice.ts 2>nul
del /q frontend\src\utils\upgradeNoticeReset.ts 2>nul
echo   ✓ 删除测试文件

REM ============ 根目录清理 ============
echo.
echo 📦 清理根目录...

REM 删除缓存和临时目录
if exist .pytest_cache rd /s /q .pytest_cache 2>nul && echo   ✓ 删除 .pytest_cache\
if exist .idea rd /s /q .idea 2>nul && echo   ✓ 删除 .idea\
if exist data rd /s /q data 2>nul && echo   ✓ 删除 data\

REM 删除大文件
del /q POIs_V2.csv 2>nul && echo   ✓ 删除 POIs_V2.csv
del /q travel_guide.xlsx 2>nul && echo   ✓ 删除 travel_guide.xlsx
del /q plan.json 2>nul && echo   ✓ 删除 plan.json

REM 删除临时脚本
del /q build_index.py 2>nul
del /q diagnose.py 2>nul
del /q rebuild_final.py 2>nul
del /q rebuild_v2.py 2>nul
del /q rebuild_with_desc2.py 2>nul
del /q replace_function.py 2>nul
del /q seed_china_data.sql 2>nul
del /q seed_plans.sql 2>nul
del /q tash 2>nul
echo   ✓ 删除临时脚本

REM 删除旧启动脚本
del /q start.bat 2>nul
del /q start.sh 2>nul
del /q env.example 2>nul
echo   ✓ 删除旧启动脚本

REM 删除开发文档
del /q DESIGN.md 2>nul
del /q PPT_OUTLINE.md 2>nul
del /q PROJECT_REPORT.md 2>nul
del /q PROJECT_STRUCTURE.md 2>nul
del /q PROJECT_SUMMARY.md 2>nul
del /q QUICK_START.md 2>nul
del /q RAG_README.md 2>nul
del /q new_readme.md 2>nul
del /q implementation_summary.md 2>nul
del /q 交通方案显示Bug修复说明.md 2>nul
del /q 行程功能工作总结.md 2>nul
del /q 行程功能讲解文稿.txt 2>nul
del /q 行程概览显示修复说明.md 2>nul
del /q 行程页面改进说明.md 2>nul
del /q 配置和使用说明.txt 2>nul
del /q 项目的开发环境及依赖库说明.txt 2>nul
del /q 项目设计计划.md 2>nul
echo   ✓ 删除开发文档

echo.
echo ✅ 清理完成！
echo.
echo 保留的核心文件：
echo   - backend\app\        (应用代码)
echo   - backend\main.py     (入口文件)
echo   - frontend\src\       (前端代码)
echo   - database\           (数据库脚本)
echo   - nginx\              (Nginx 配置)
echo   - docker-compose*.yml (Docker 配置)
echo.
echo 如需重新安装前端依赖：
echo   cd frontend ^&^& npm install
echo.
pause