# 사용자 관리 시스템 사용 가이드

이 문서는 MCP Core의 사용자 인증 및 관리 시스템을 사용하는 방법을 설명합니다.

## 빠른 시작

### 1. 데이터베이스 설정

먼저 MySQL 데이터베이스를 설정합니다:

```bash
# MySQL에 접속
mysql -u root -p

# 데이터베이스 및 사용자 생성
CREATE DATABASE mcp_core CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'secure_password123';
GRANT ALL PRIVILEGES ON mcp_core.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

```bash
# 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mcp_user
MYSQL_PASSWORD=secure_password123
MYSQL_DATABASE=mcp_core
```

### 3. 스키마 초기화

```bash
# 스키마 생성
python database/init_db.py

# 기존 테이블이 있다면 재생성
python database/init_db.py --drop-existing
```

### 4. 테스트 실행

```bash
# 데이터베이스 연결 테스트
python database/test_user_db.py
```

## 사용 예시

### Python 코드에서 사용

#### 사용자 생성

```python
from app.models.users import UserCreate
from app.database import DatabaseConnection
from sqlalchemy import text
import bcrypt

# 데이터베이스 연결 초기화
DatabaseConnection.initialize()

# 사용자 데이터 준비
user_data = UserCreate(
    username="john_doe",
    email="john@example.com",
    password="SecurePass123!",
    full_name="John Doe",
    organization="ACME Corp"
)

# 비밀번호 해싱
password_hash = bcrypt.hashpw(
    user_data.password.encode('utf-8'),
    bcrypt.gensalt()
).decode('utf-8')

# 데이터베이스에 저장
with DatabaseConnection.get_session() as session:
    sql = text("""
        INSERT INTO users (username, email, password_hash, full_name, organization)
        VALUES (:username, :email, :password_hash, :full_name, :organization)
    """)
    
    session.execute(sql, {
        'username': user_data.username,
        'email': user_data.email,
        'password_hash': password_hash,
        'full_name': user_data.full_name,
        'organization': user_data.organization
    })
    print(f"사용자 '{user_data.username}' 생성 완료")
```

#### 클라우드 계정 연동

```python
from app.models.users import UserCloudConfig
from sqlalchemy import text

# AWS 계정 정보
aws_config = UserCloudConfig(
    cloud_provider="aws",
    cloud_account_id="123456789012",
    cloud_region="us-east-1",
    cloud_access_key="AKIA...",  # 실제로는 암호화 필요
    cloud_secret_key="secret..."  # 실제로는 암호화 필요
)

# 사용자 업데이트
with DatabaseConnection.get_session() as session:
    sql = text("""
        UPDATE users 
        SET cloud_provider = :provider,
            cloud_account_id = :account_id,
            cloud_region = :region,
            cloud_access_key = :access_key,
            cloud_secret_key = :secret_key
        WHERE username = :username
    """)
    
    session.execute(sql, {
        'provider': aws_config.cloud_provider,
        'account_id': aws_config.cloud_account_id,
        'region': aws_config.cloud_region,
        'access_key': aws_config.cloud_access_key,  # 암호화 필요
        'secret_key': aws_config.cloud_secret_key,  # 암호화 필요
        'username': 'john_doe'
    })
    print("AWS 계정 연동 완료")
```

#### 사용자 인증

```python
import bcrypt
from sqlalchemy import text

def authenticate_user(username: str, password: str) -> bool:
    """사용자 인증"""
    with DatabaseConnection.get_session() as session:
        sql = text("""
            SELECT password_hash, is_active, locked_until
            FROM users
            WHERE username = :username
        """)
        
        result = session.execute(sql, {'username': username}).fetchone()
        
        if not result:
            return False
        
        # 계정 활성 상태 확인
        if not result['is_active']:
            return False
        
        # 계정 잠금 확인
        from datetime import datetime
        if result['locked_until'] and result['locked_until'] > datetime.now():
            return False
        
        # 비밀번호 확인
        return bcrypt.checkpw(
            password.encode('utf-8'),
            result['password_hash'].encode('utf-8')
        )

# 사용 예시
if authenticate_user('john_doe', 'SecurePass123!'):
    print("인증 성공")
else:
    print("인증 실패")
```

#### 세션 관리

```python
import secrets
from datetime import datetime, timedelta
from sqlalchemy import text

def create_session(user_id: int, ip_address: str, user_agent: str) -> str:
    """사용자 세션 생성"""
    session_token = secrets.token_urlsafe(64)
    expires_at = datetime.now() + timedelta(hours=24)
    
    with DatabaseConnection.get_session() as session:
        sql = text("""
            INSERT INTO user_sessions 
            (user_id, session_token, ip_address, user_agent, expires_at)
            VALUES (:user_id, :session_token, :ip_address, :user_agent, :expires_at)
        """)
        
        session.execute(sql, {
            'user_id': user_id,
            'session_token': session_token,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'expires_at': expires_at
        })
    
    return session_token

# 사용 예시
token = create_session(
    user_id=1,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0 ..."
)
print(f"세션 생성: {token[:20]}...")
```

#### 감사 로그 기록

```python
from sqlalchemy import text
import json

def log_user_action(user_id: int, action: str, resource_type: str = None,
                   resource_id: str = None, metadata: dict = None):
    """사용자 활동 로그 기록"""
    with DatabaseConnection.get_session() as session:
        sql = text("""
            INSERT INTO user_audit_log
            (user_id, action, resource_type, resource_id, metadata)
            VALUES (:user_id, :action, :resource_type, :resource_id, :metadata)
        """)
        
        session.execute(sql, {
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'metadata': json.dumps(metadata) if metadata else None
        })

# 사용 예시
log_user_action(
    user_id=1,
    action="user.login",
    metadata={
        "method": "password",
        "ip_address": "192.168.1.100",
        "success": True
    }
)
```

### FastAPI 라우터 예시

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db_session
from app.models.users import UserCreate, UserResponse
import bcrypt

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db_session)
):
    """새 사용자 등록"""
    # 비밀번호 해싱
    password_hash = bcrypt.hashpw(
        user_data.password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # 사용자 생성
    sql = text("""
        INSERT INTO users (username, email, password_hash, full_name, organization)
        VALUES (:username, :email, :password_hash, :full_name, :organization)
    """)
    
    try:
        result = db.execute(sql, {
            'username': user_data.username,
            'email': user_data.email,
            'password_hash': password_hash,
            'full_name': user_data.full_name,
            'organization': user_data.organization
        })
        user_id = result.lastrowid
        
        # 생성된 사용자 조회
        user_sql = text("SELECT * FROM users WHERE id = :id")
        user = db.execute(user_sql, {'id': user_id}).fetchone()
        
        return UserResponse(**dict(user))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db_session)
):
    """사용자 정보 조회"""
    sql = text("SELECT * FROM users WHERE id = :id AND is_active = true")
    user = db.execute(sql, {'id': user_id}).fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    return UserResponse(**dict(user))
```

## 보안 권장사항

### 1. 비밀번호 해싱

반드시 bcrypt 또는 argon2를 사용하세요:

```python
import bcrypt

# 비밀번호 해싱
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# 비밀번호 검증
is_valid = bcrypt.checkpw(password.encode('utf-8'), password_hash)
```

### 2. 클라우드 자격증명 암호화

민감한 정보는 암호화하여 저장하세요:

```python
from cryptography.fernet import Fernet
import os

# 암호화 키 (환경 변수에 저장)
key = os.getenv('ENCRYPTION_KEY').encode()
cipher = Fernet(key)

# 암호화
encrypted = cipher.encrypt(sensitive_data.encode())

# 복호화
decrypted = cipher.decrypt(encrypted).decode()
```

### 3. API 키 생성

안전한 API 키 생성:

```python
import secrets

api_key = secrets.token_urlsafe(32)  # 256 비트
```

### 4. 세션 토큰

암호학적으로 안전한 세션 토큰:

```python
import secrets

session_token = secrets.token_urlsafe(64)  # 512 비트
```

## 문제 해결

### 연결 오류

```python
# 연결 테스트
from app.database import DatabaseConnection

if DatabaseConnection.is_available():
    print("데이터베이스 연결 성공")
else:
    print("데이터베이스 연결 실패")
```

### 디버깅

```python
# SQLAlchemy 로깅 활성화
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## 더 많은 정보

- [데이터베이스 스키마 문서](../database/README.md)
- [메인 README](../README.md)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
