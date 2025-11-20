# MySQL Docker 설정 가이드

## 🚀 빠른 시작

### 1. MySQL 컨테이너 시작
```bash
# Linux/Mac
chmod +x scripts/start_mysql.sh
./scripts/start_mysql.sh

# Windows (Git Bash)
bash scripts/start_mysql.sh

# 또는 직접 docker-compose 실행
docker-compose -f docker-compose.mysql.yml --env-file .env.mysql up -d
```

### 2. 스키마 초기화 (자동)
컨테이너 시작 시 `db/` 폴더의 `.sql` 파일이 자동 실행됩니다:
- `schema_unified.sql`

### 3. 연결 확인
```bash
# MySQL 접속
docker exec -it mcp-mysql mysql -u mcp_user -p mcp_core
# Password: mcp_pass_2024 (또는 .env.mysql에서 설정한 값)

# 테이블 확인
mysql> SHOW TABLES;
mysql> DESC mcp_contexts;
```

## 📊 연결 정보

```
Host: localhost
Port: 3306
Database: mcp_core
User: mcp_user
Password: mcp_pass_2024 (변경 권장)
```

**SQLAlchemy 연결 문자열:**
```python
DATABASE_URL = "mysql+pymysql://mcp_user:mcp_pass_2024@localhost:3306/mcp_core"
```

## 🔧 유용한 명령어

### 컨테이너 관리
```bash
# 상태 확인
docker ps | grep mcp-mysql

# 로그 확인
docker logs -f mcp-mysql

# 중지
./scripts/stop_mysql.sh
# 또는
docker-compose -f docker-compose.mysql.yml down

# 중지 + 데이터 삭제
docker-compose -f docker-compose.mysql.yml down -v
```

### 데이터베이스 작업
```bash
# SQL 파일 실행
docker exec -i mcp-mysql mysql -u root -pmcp_root_2024 mcp_core < db/schema_unified.sql

# 덤프 생성
docker exec mcp-mysql mysqldump -u root -pmcp_root_2024 mcp_core > backup.sql

# 백업 (스크립트 사용)
./scripts/backup_mysql.sh
```

### 볼륨 관리
```bash
# 볼륨 목록
docker volume ls | grep mcp

# 볼륨 상세 정보
docker volume inspect mcp_mysql_data

# 볼륨 삭제 (주의: 데이터 손실)
docker volume rm mcp_mysql_data
```

## 📁 파일 구조

```
mcp_core/
├── docker-compose.mysql.yml    # MySQL 컨테이너 정의
├── .env.mysql                  # 환경변수 (비밀번호 등)
├── db/                         # 스키마 SQL 파일 (자동 실행)
│   └── schema_unified.sql
├── scripts/
│   ├── start_mysql.sh          # 시작 스크립트
│   ├── stop_mysql.sh           # 중지 스크립트
│   └── backup_mysql.sh         # 백업 스크립트
└── backups/mysql/              # 백업 저장 위치
```

## 🔐 보안 설정 (프로덕션)

`.env.mysql` 파일에서 강력한 비밀번호로 변경:
```bash
MYSQL_ROOT_PASSWORD=your_strong_root_password_here
MYSQL_PASSWORD=your_strong_app_password_here
```

**주의:** `.env.mysql`을 `.gitignore`에 추가하여 Git에 커밋되지 않도록 설정하세요.

## 🐛 트러블슈팅

### 포트 3306이 이미 사용중
```bash
# 기존 MySQL 프로세스 확인
netstat -an | grep 3306
# 또는
lsof -i :3306

# docker-compose.mysql.yml에서 포트 변경
ports:
  - "3307:3306"  # 호스트:컨테이너
```

### 컨테이너가 시작되지 않음
```bash
# 로그 확인
docker logs mcp-mysql

# 볼륨 삭제 후 재시작 (데이터 손실 주의)
docker-compose -f docker-compose.mysql.yml down -v
docker-compose -f docker-compose.mysql.yml up -d
```

### 연결 거부 (Connection refused)
```bash
# Health check 상태 확인
docker inspect mcp-mysql | grep -A 10 Health

# MySQL이 준비될 때까지 대기 (최대 30초)
until docker exec mcp-mysql mysqladmin ping -h localhost --silent; do
    echo "Waiting for MySQL..."
    sleep 2
done
```

## 📦 백업 & 복구

### 자동 백업 설정 (Cron)
```bash
# crontab 편집
crontab -e

# 매일 새벽 2시 백업
0 2 * * * cd /path/to/mcp_core && ./scripts/backup_mysql.sh >> logs/backup.log 2>&1
```

### 복구
```bash
# SQL 덤프에서 복구
gunzip < backups/mysql/mysql-dump-20241121.sql.gz | docker exec -i mcp-mysql mysql -u root -pmcp_root_2024 mcp_core

# 볼륨 백업에서 복구
docker-compose -f docker-compose.mysql.yml down
docker volume rm mcp_mysql_data
docker volume create mcp_mysql_data
docker run --rm -v mcp_mysql_data:/data -v $(pwd)/backups/mysql:/backup alpine tar xzf /backup/mysql-volume-20241121.tar.gz -C /data
docker-compose -f docker-compose.mysql.yml up -d
```

## 🔗 관련 파일

- ORM 모델: `app/core/persistence_models.py`
- 데이터베이스 세션: `app/core/db.py` (생성 필요)
- 환경변수 설정: `app/config/settings.py`
