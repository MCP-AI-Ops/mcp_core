#!/bin/bash
# MySQL 컨테이너 시작 스크립트

set -e

echo "🚀 Starting MySQL container for mcp_core..."

# 네트워크 생성 (이미 있으면 무시)
docker network create mcp_net 2>/dev/null || echo "✓ Network mcp_net already exists"

# docker-compose로 MySQL 시작
docker-compose -f docker-compose.mysql.yml --env-file .env.mysql up -d

echo "⏳ Waiting for MySQL to be ready..."
sleep 10

# Health check
until docker exec mcp-mysql mysqladmin ping -h localhost --silent; do
    echo "   MySQL is starting..."
    sleep 2
done

echo "✅ MySQL is ready!"
echo ""
echo "📊 Connection Info:"
echo "   Host: localhost"
echo "   Port: 3306"
echo "   Database: mcp_core"
echo "   User: mcp_user"
echo "   Password: (check .env.mysql)"
echo ""
echo "🔧 Useful Commands:"
echo "   Connect: docker exec -it mcp-mysql mysql -u mcp_user -p mcp_core"
echo "   Logs: docker logs -f mcp-mysql"
echo "   Stop: docker-compose -f docker-compose.mysql.yml down"
echo "   Stop & Remove Data: docker-compose -f docker-compose.mysql.yml down -v"
