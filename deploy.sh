#!/bin/bash
# SkyRoam 一键部署脚本

set -e

echo "🚀 SkyRoam Docker 部署脚本"
echo "=========================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker Desktop"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 检查配置文件
if [ ! -f ".env.docker.prod" ]; then
    echo "⚠️  未找到 .env.docker.prod 配置文件"
    echo "📝 正在从模板创建配置文件..."
    cp .env.docker.prod.example .env.docker.prod
    echo "✅ 配置文件已创建: .env.docker.prod"
    echo "⚠️  请编辑配置文件，填入你的 API 密钥后再运行此脚本"
    echo ""
    echo "必须配置的项："
    echo "  - POSTGRES_PASSWORD（数据库密码）"
    echo "  - SECRET_KEY（应用密钥）"
    echo "  - OPENAI_API_KEY（LLM API 密钥）"
    echo "  - AMAP_API_KEY（高德地图 API 密钥）"
    exit 1
fi

# 检查关键配置
echo "🔍 检查配置..."

check_config() {
    local key=$1
    local value=$(grep "^$key=" .env.docker.prod | cut -d'=' -f2)
    if [ -z "$value" ] || [ "$value" = "your_secure_password_here" ] || [ "$value" = "your_very_secure_secret_key_here" ]; then
        echo "❌ 请配置 $key"
        return 1
    fi
    return 0
}

check_config "POSTGRES_PASSWORD" || exit 1
check_config "SECRET_KEY" || exit 1
check_config "OPENAI_API_KEY" || exit 1
check_config "AMAP_API_KEY" || exit 1

echo "✅ 配置检查通过"

# 构建镜像
echo ""
echo "🔨 构建 Docker 镜像..."
docker compose -f docker-compose.prod.yml build

# 启动服务
echo ""
echo "🚀 启动服务..."
docker compose -f docker-compose.prod.yml up -d

# 等待服务就绪
echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker compose -f docker-compose.prod.yml ps

# 健康检查
echo ""
echo "🏥 健康检查..."

check_health() {
    local service=$1
    local url=$2
    local max_retries=10
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo "✅ $service 健康"
            return 0
        fi
        retry=$((retry + 1))
        sleep 3
    done

    echo "⚠️  $service 启动超时"
    return 1
}

check_health "Backend" "http://localhost/health/backend" || true
check_health "Frontend" "http://localhost/health" || true

echo ""
echo "✅ 部署完成！"
echo ""
echo "访问地址:"
echo "  🌐 前端页面: http://localhost"
echo "  📚 API 文档: http://localhost/docs"
echo "  🔧 健康检查: http://localhost/health"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "  停止服务: docker compose -f docker-compose.prod.yml down"
echo "  重启服务: docker compose -f docker-compose.prod.yml restart"