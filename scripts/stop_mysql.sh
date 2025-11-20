#!/bin/bash
# MySQL 컨테이너 중지 스크립트

echo "🛑 Stopping MySQL container..."

docker-compose -f docker-compose.mysql.yml down

echo "✅ MySQL stopped (data preserved in volume: mcp_mysql_data)"
echo ""
echo "To remove data volume as well, run:"
echo "   docker-compose -f docker-compose.mysql.yml down -v"
