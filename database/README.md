# MCP Core 데이터베이스 스키마

이 디렉터리는 MCP Core의 사용자 인증 및 관리를 위한 MySQL 데이터베이스 스키마를 포함합니다.

## 개요

사용자 관리 시스템은 다음 기능을 제공합니다:

- **사용자 인증**: 사용자명/이메일 기반 로그인, 비밀번호 해싱
- **클라우드 계정 통합**: AWS, Azure, GCP 등 주요 클라우드 제공자 계정 연동
- **API 키 관리**: 프로그래밍 방식의 접근을 위한 API 키 발급
- **세션 관리**: 안전한 세션 추적 및 관리
- **2단계 인증**: TOTP 기반 2FA 지원
- **감사 로그**: 모든 사용자 활동 추적

## 데이터베이스 테이블

### 1. `users` (사용자)
주요 사용자 정보 및 인증 데이터를 저장합니다.

**주요 필드:**
- `id`: 기본 키
- `username`, `email`: 인증 정보 (고유)
- `password_hash`: bcrypt/argon2 해시된 비밀번호
- `cloud_provider`, `cloud_account_id`, `cloud_access_key` 등: 클라우드 계정 통합
- `api_key`: API 접근 키
- `two_factor_enabled`, `two_factor_secret`: 2FA 설정
- `is_active`, `is_verified`: 계정 상태

### 2. `user_sessions` (사용자 세션)
활성 사용자 세션을 추적합니다.

**주요 필드:**
- `session_token`: 세션 식별자
- `user_id`: 사용자 참조 (외래 키)
- `expires_at`: 세션 만료 시간
- `ip_address`, `user_agent`: 보안 추적 정보

### 3. `password_reset_tokens` (비밀번호 재설정 토큰)
비밀번호 재설정 프로세스를 관리합니다.

**주요 필드:**
- `token`: 재설정 토큰 (고유)
- `user_id`: 사용자 참조
- `expires_at`: 토큰 만료 시간
- `used_at`: 토큰 사용 시간

### 4. `email_verification_tokens` (이메일 인증 토큰)
이메일 인증 워크플로우를 관리합니다.

**주요 필드:**
- `token`: 인증 토큰 (고유)
- `user_id`: 사용자 참조
- `verified_at`: 인증 완료 시간

### 5. `user_audit_log` (감사 로그)
모든 사용자 활동을 기록합니다.

**주요 필드:**
- `user_id`: 사용자 참조
- `action`: 수행된 작업
- `resource_type`, `resource_id`: 영향받은 리소스
- `metadata`: JSON 형식의 추가 정보

## 초기 설정

### 환경 변수 설정

데이터베이스 연결을 위해 다음 환경 변수를 설정하세요:

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=mcp_user
export MYSQL_PASSWORD=your_secure_password
export MYSQL_DATABASE=mcp_core
# 선택사항: SSL 연결
# export MYSQL_SSL_CA=/path/to/ca.pem
```

또는 `.env` 파일에 저장:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mcp_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=mcp_core
```

### 데이터베이스 생성

먼저 MySQL 데이터베이스를 생성합니다:

```bash
mysql -u root -p
```

```sql
CREATE DATABASE mcp_core CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON mcp_core.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 스키마 초기화

초기화 스크립트를 실행하여 테이블을 생성합니다:

```bash
# 환경 변수 설정 후
python database/init_db.py
```

기존 테이블을 삭제하고 다시 생성하려면:

```bash
python database/init_db.py --drop-existing
```

### 수동 스키마 적용

SQL 파일을 직접 적용할 수도 있습니다:

```bash
mysql -u mcp_user -p mcp_core < database/schemas/001_users_authentication.sql
```

## 클라우드 제공자 통합

시스템은 다음 클라우드 제공자를 지원합니다:

- **AWS**: `cloud_provider='aws'`
  - `cloud_access_key`: AWS Access Key ID
  - `cloud_secret_key`: AWS Secret Access Key (암호화 저장)
  - `cloud_region`: AWS 리전 (예: us-east-1)

- **Azure**: `cloud_provider='azure'`
  - `cloud_tenant_id`: Azure Tenant ID
  - `cloud_access_key`: Azure Client ID
  - `cloud_secret_key`: Azure Client Secret (암호화 저장)
  - `cloud_region`: Azure 리전

- **GCP**: `cloud_provider='gcp'`
  - `cloud_project_id`: GCP Project ID
  - `cloud_config_json`: 서비스 계정 JSON (암호화 저장)

- **기타**: `alibaba`, `oracle`, `ibm`, `other`

## 보안 고려사항

### 비밀번호 해싱
- 사용자 비밀번호는 절대 평문으로 저장하지 않습니다
- bcrypt 또는 argon2를 사용하여 해싱합니다
- 최소 12 라운드의 솔트를 사용합니다

### 클라우드 자격증명 암호화
- `cloud_access_key`, `cloud_secret_key` 필드는 암호화하여 저장해야 합니다
- 응용 프로그램 수준에서 AES-256 암호화를 권장합니다
- 암호화 키는 환경 변수나 비밀 관리 서비스에 저장합니다

### API 키
- API 키는 UUID v4 또는 충분히 무작위한 문자열을 사용합니다
- 만료 시간을 설정하여 주기적으로 갱신하도록 합니다

### 세션 관리
- 세션 토큰은 암호학적으로 안전한 난수를 사용합니다
- 만료된 세션은 주기적으로 정리합니다
- 의심스러운 활동 감지 시 세션을 무효화합니다

## 사용 예시

### Python에서 데이터베이스 연결

```python
from app.database import DatabaseConnection

# 연결 초기화 (환경 변수 사용)
DatabaseConnection.initialize()

# 세션 사용
with DatabaseConnection.get_session() as session:
    from sqlalchemy import text
    result = session.execute(text("SELECT * FROM users WHERE is_active = true"))
    users = result.fetchall()
```

### FastAPI에서 사용

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db_session

router = APIRouter()

@router.get("/users")
def get_users(db: Session = Depends(get_db_session)):
    from sqlalchemy import text
    result = db.execute(text("SELECT * FROM users"))
    return result.fetchall()
```

## 마이그레이션

스키마 변경이 필요한 경우 `database/migrations/` 디렉터리에 마이그레이션 파일을 생성합니다.

파일명 형식: `YYYYMMDD_HHMM_description.sql`

예시:
```
database/migrations/20250115_1430_add_user_preferences.sql
```

## 백업 및 복구

### 백업
```bash
mysqldump -u mcp_user -p mcp_core > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 복구
```bash
mysql -u mcp_user -p mcp_core < backup_20250115_143000.sql
```

## 문제 해결

### 연결 오류
1. MySQL 서버가 실행 중인지 확인
2. 환경 변수가 올바르게 설정되었는지 확인
3. 방화벽 설정 확인

### 권한 오류
```sql
GRANT ALL PRIVILEGES ON mcp_core.* TO 'mcp_user'@'%';
FLUSH PRIVILEGES;
```

### SSL 연결 오류
- CA 인증서 경로 확인
- MySQL 서버 SSL 설정 확인

## 참고 자료

- [MySQL 8.0 Documentation](https://dev.mysql.com/doc/refman/8.0/en/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)
