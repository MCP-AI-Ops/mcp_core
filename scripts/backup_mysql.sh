#!/bin/bash
# MySQL 백업 스크립트 (cron 등록 가능)

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/mysql"
CONTAINER_NAME="mcp-mysql"
DB_NAME="mcp_core"

mkdir -p $BACKUP_DIR

echo "📦 Starting MySQL backup..."

# Volume 백업 (전체 데이터)
echo "   Backing up volume..."
docker run --rm \
  -v mcp_mysql_data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf /backup/mysql-volume-$DATE.tar.gz -C /data .

# SQL 덤프 백업 (특정 DB만)
echo "   Backing up SQL dump..."
docker exec $CONTAINER_NAME mysqldump \
  -u root -p${MYSQL_ROOT_PASSWORD:-mcp_root_2024} \
  --single-transaction \
  --routines \
  --triggers \
  $DB_NAME > $BACKUP_DIR/mysql-dump-$DATE.sql

gzip $BACKUP_DIR/mysql-dump-$DATE.sql

echo "✅ Backup completed!"
echo "   Volume backup: $BACKUP_DIR/mysql-volume-$DATE.tar.gz"
echo "   SQL dump: $BACKUP_DIR/mysql-dump-$DATE.sql.gz"

# 7일 이상된 백업 삭제
find $BACKUP_DIR -name "mysql-*" -mtime +7 -delete 2>/dev/null || true

echo "   Old backups cleaned (>7 days)"
