#!/usr/bin/env python3
"""
사용자 데이터베이스 테스트 스크립트

이 스크립트는 사용자 데이터베이스 스키마의 기본 기능을 테스트합니다.

Usage:
    export MYSQL_HOST=localhost
    export MYSQL_USER=mcp_user
    export MYSQL_PASSWORD=your_password
    export MYSQL_DATABASE=mcp_core
    python database/test_user_db.py
"""

import os
import sys
from datetime import datetime, timedelta
import secrets

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("[error] PyMySQL이 설치되지 않았습니다. pip install PyMySQL을 실행하세요.")
    sys.exit(1)


def get_db_connection():
    """데이터베이스 연결을 생성합니다."""
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
    }
    
    if not all([config['user'], config['password'], config['database']]):
        raise ValueError("필수 환경 변수가 설정되지 않았습니다: MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
    
    return pymysql.connect(**config)


def test_create_user(cursor):
    """테스트 사용자를 생성합니다."""
    print("\n[test] 사용자 생성 테스트")
    
    # 테스트 사용자 데이터
    username = f"test_user_{secrets.token_hex(4)}"
    email = f"{username}@example.com"
    password_hash = "$2b$12$" + secrets.token_hex(31)  # 실제로는 bcrypt 사용
    api_key = secrets.token_urlsafe(32)
    
    sql = """
    INSERT INTO users (
        username, email, password_hash, full_name, organization,
        is_active, cloud_provider, cloud_account_id, cloud_region,
        api_key, api_key_expires_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """
    
    values = (
        username,
        email,
        password_hash,
        "테스트 사용자",
        "MCP Labs",
        True,
        "aws",
        "123456789012",
        "us-east-1",
        api_key,
        datetime.now() + timedelta(days=365)
    )
    
    cursor.execute(sql, values)
    user_id = cursor.lastrowid
    
    print(f"[info] 사용자 생성 완료: ID={user_id}, username={username}")
    return user_id, username


def test_create_session(cursor, user_id):
    """사용자 세션을 생성합니다."""
    print("\n[test] 세션 생성 테스트")
    
    session_token = secrets.token_urlsafe(64)
    
    sql = """
    INSERT INTO user_sessions (
        user_id, session_token, ip_address, user_agent, expires_at
    ) VALUES (
        %s, %s, %s, %s, %s
    )
    """
    
    values = (
        user_id,
        session_token,
        "192.168.1.100",
        "Mozilla/5.0 (Test Agent)",
        datetime.now() + timedelta(hours=24)
    )
    
    cursor.execute(sql, values)
    session_id = cursor.lastrowid
    
    print(f"[info] 세션 생성 완료: ID={session_id}, token={session_token[:20]}...")
    return session_id


def test_create_audit_log(cursor, user_id):
    """감사 로그를 생성합니다."""
    print("\n[test] 감사 로그 생성 테스트")
    
    sql = """
    INSERT INTO user_audit_log (
        user_id, action, resource_type, resource_id,
        ip_address, user_agent, metadata
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    )
    """
    
    values = (
        user_id,
        "user.login",
        "session",
        "test-session-123",
        "192.168.1.100",
        "Mozilla/5.0 (Test Agent)",
        '{"method": "password", "success": true}'
    )
    
    cursor.execute(sql, values)
    log_id = cursor.lastrowid
    
    print(f"[info] 감사 로그 생성 완료: ID={log_id}")
    return log_id


def test_query_users(cursor):
    """사용자 목록을 조회합니다."""
    print("\n[test] 사용자 조회 테스트")
    
    sql = """
    SELECT id, username, email, cloud_provider, cloud_region, 
           is_active, created_at
    FROM users
    WHERE is_active = true
    ORDER BY created_at DESC
    LIMIT 5
    """
    
    cursor.execute(sql)
    users = cursor.fetchall()
    
    print(f"[info] 활성 사용자 {len(users)}명 조회:")
    for user in users:
        print(f"  - ID: {user['id']}, Username: {user['username']}, "
              f"Provider: {user['cloud_provider']}, Created: {user['created_at']}")


def test_query_sessions(cursor, user_id):
    """사용자의 활성 세션을 조회합니다."""
    print("\n[test] 세션 조회 테스트")
    
    sql = """
    SELECT id, session_token, ip_address, expires_at, last_activity_at
    FROM user_sessions
    WHERE user_id = %s AND expires_at > NOW()
    ORDER BY created_at DESC
    """
    
    cursor.execute(sql, (user_id,))
    sessions = cursor.fetchall()
    
    print(f"[info] 사용자 ID {user_id}의 활성 세션 {len(sessions)}개 조회:")
    for session in sessions:
        print(f"  - Session ID: {session['id']}, "
              f"Token: {session['session_token'][:20]}..., "
              f"IP: {session['ip_address']}")


def test_query_audit_log(cursor, user_id):
    """사용자의 감사 로그를 조회합니다."""
    print("\n[test] 감사 로그 조회 테스트")
    
    sql = """
    SELECT id, action, resource_type, ip_address, created_at
    FROM user_audit_log
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT 10
    """
    
    cursor.execute(sql, (user_id,))
    logs = cursor.fetchall()
    
    print(f"[info] 사용자 ID {user_id}의 감사 로그 {len(logs)}개 조회:")
    for log in logs:
        print(f"  - Action: {log['action']}, "
              f"Resource: {log['resource_type']}, "
              f"IP: {log['ip_address']}, "
              f"Time: {log['created_at']}")


def main():
    print("[info] 사용자 데이터베이스 테스트 시작\n")
    
    connection = None
    try:
        # 데이터베이스 연결
        print("[info] 데이터베이스 연결 중...")
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SHOW TABLES LIKE 'users'")
        if not cursor.fetchone():
            print("[error] users 테이블이 존재하지 않습니다.")
            print("[error] 먼저 database/init_db.py를 실행하여 스키마를 초기화하세요.")
            sys.exit(1)
        
        # 테스트 실행
        user_id, username = test_create_user(cursor)
        connection.commit()
        
        test_create_session(cursor, user_id)
        connection.commit()
        
        test_create_audit_log(cursor, user_id)
        connection.commit()
        
        test_query_users(cursor)
        test_query_sessions(cursor, user_id)
        test_query_audit_log(cursor, user_id)
        
        print("\n[info] 모든 테스트 완료!")
        print(f"[info] 생성된 테스트 사용자: {username} (ID: {user_id})")
        
    except Exception as e:
        print(f"\n[error] 테스트 실패: {e}")
        if connection:
            connection.rollback()
        sys.exit(1)
    finally:
        if connection:
            connection.close()
            print("[info] 데이터베이스 연결 종료")


if __name__ == '__main__':
    main()
