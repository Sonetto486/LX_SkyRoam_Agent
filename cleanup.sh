#!/bin/bash
# SkyRoam 项目清理脚本
# 删除所有非必需文件，保留运行所需的核心文件

set -e

echo "🗑️  SkyRoam 项目清理脚本"
echo "========================"
echo ""
echo "⚠️  警告：此操作将删除测试文件、临时文件、文档等非必需内容"
echo "⚠️  建议先提交 Git 或创建备份"
echo ""
read -p "确认继续？(y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始清理..."

# ============ 后端清理 ============
echo "📦 清理后端..."

# 删除测试目录
rm -rf backend/tests/ 2>/dev/null && echo "  ✓ 删除 tests/"

# 删除脚本目录
rm -rf backend/scripts/ 2>/dev/null && echo "  ✓ 删除 scripts/"

# 删除临时数据
rm -rf backend/data/ 2>/dev/null && echo "  ✓ 删除 data/"
rm -rf backend/browser_data/ 2>/dev/null && echo "  ✓ 删除 browser_data/"

# 删除文档
rm -rf backend/docs/ 2>/dev/null && echo "  ✓ 删除 docs/"

# 删除缓存
rm -rf backend/.pytest_cache/ 2>/dev/null && echo "  ✓ 删除 .pytest_cache/"
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null && echo "  ✓ 删除所有 __pycache__/"

# 删除临时文件
rm -f backend/check_data.py 2>/dev/null
rm -f backend/fill_data.py 2>/dev/null
rm -f backend/fill_data_sql.py 2>/dev/null
rm -f backend/seed_topics.py 2>/dev/null
rm -f backend/test_celery_cleanup.py 2>/dev/null
rm -f backend/update_destinations_table.py 2>/dev/null
rm -f backend/update_travel_plan_tables.py 2>/dev/null
rm -f backend/update_users_table.py 2>/dev/null
rm -f backend/init_db.py 2>/dev/null
rm -f backend/mock_flight_data.json 2>/dev/null
rm -f backend/.env.backup 2>/dev/null
echo "  ✓ 删除临时 Python 文件"

# ============ 前端清理 ============
echo ""
echo "📦 清理前端..."

# 删除构建产物
rm -rf frontend/build/ 2>/dev/null && echo "  ✓ 删除 build/"

# 删除依赖（可选，如需重新安装）
# rm -rf frontend/node_modules/ 2>/dev/null && echo "  ✓ 删除 node_modules/"

# 删除缓存
rm -rf frontend/.npm/ 2>/dev/null && echo "  ✓ 删除 .npm/"

# 删除临时文件
rm -f "frontend/lx-skyroam-agent-frontend@1.0.0" 2>/dev/null
rm -rf frontend/src/pages/TestPage/ 2>/dev/null && echo "  ✓ 删除 TestPage/"
rm -f frontend/src/pages/TestDataExtraction.tsx 2>/dev/null
rm -f frontend/src/utils/testUpgradeNotice.ts 2>/dev/null
rm -f frontend/src/utils/upgradeNoticeReset.ts 2>/dev/null
echo "  ✓ 删除测试文件"

# ============ 根目录清理 ============
echo ""
echo "📦 清理根目录..."

# 删除缓存和临时目录
rm -rf .pytest_cache/ 2>/dev/null && echo "  ✓ 删除 .pytest_cache/"
rm -rf .idea/ 2>/dev/null && echo "  ✓ 删除 .idea/"
rm -rf data/ 2>/dev/null && echo "  ✓ 删除 data/"

# 删除大文件
rm -f POIs_V2.csv 2>/dev/null && echo "  ✓ 删除 POIs_V2.csv"
rm -f travel_guide.xlsx 2>/dev/null && echo "  ✓ 删除 travel_guide.xlsx"
rm -f plan.json 2>/dev/null && echo "  ✓ 删除 plan.json"

# 删除临时脚本
rm -f build_index.py 2>/dev/null
rm -f diagnose.py 2>/dev/null
rm -f rebuild_final.py 2>/dev/null
rm -f rebuild_v2.py 2>/dev/null
rm -f rebuild_with_desc2.py 2>/dev/null
rm -f replace_function.py 2>/dev/null
rm -f seed_china_data.sql 2>/dev/null
rm -f seed_plans.sql 2>/dev/null
rm -f tash 2>/dev/null
echo "  ✓ 删除临时脚本"

# 删除旧启动脚本
rm -f start.bat 2>/dev/null
rm -f start.sh 2>/dev/null
rm -f env.example 2>/dev/null
echo "  ✓ 删除旧启动脚本"

# 删除开发文档
rm -f DESIGN.md 2>/dev/null
rm -f PPT_OUTLINE.md 2>/dev/null
rm -f PROJECT_REPORT.md 2>/dev/null
rm -f PROJECT_STRUCTURE.md 2>/dev/null
rm -f PROJECT_SUMMARY.md 2>/dev/null
rm -f QUICK_START.md 2>/dev/null
rm -f RAG_README.md 2>/dev/null
rm -f new_readme.md 2>/dev/null
rm -f implementation_summary.md 2>/dev/null
rm -f 交通方案显示Bug修复说明.md 2>/dev/null
rm -f 行程功能工作总结.md 2>/dev/null
rm -f 行程功能讲解文稿.txt 2>/dev/null
rm -f 行程概览显示修复说明.md 2>/dev/null
rm -f 行程页面改进说明.md 2>/dev/null
rm -f 配置和使用说明.txt 2>/dev/null
rm -f 项目的开发环境及依赖库说明.txt 2>/dev/null
rm -f 项目设计计划.md 2>/dev/null
echo "  ✓ 删除开发文档"

echo ""
echo "✅ 清理完成！"
echo ""
echo "保留的核心文件："
echo "  - backend/app/        (应用代码)"
echo "  - backend/main.py     (入口文件)"
echo "  - frontend/src/       (前端代码)"
echo "  - database/           (数据库脚本)"
echo "  - nginx/              (Nginx 配置)"
echo "  - docker-compose*.yml (Docker 配置)"
echo ""
echo "如需重新安装前端依赖："
echo "  cd frontend && npm install"