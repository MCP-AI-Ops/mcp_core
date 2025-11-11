#!/usr/bin/env python3
"""
Database initialization script for MCP Core user authentication schema.

This script creates the necessary database tables for user management,
authentication, and cloud account integration.

Usage:
    python database/init_db.py [--drop-existing]

Environment Variables:
    MYSQL_HOST      - MySQL host (default: localhost)
    MYSQL_PORT      - MySQL port (default: 3306)
    MYSQL_USER      - MySQL user
    MYSQL_PASSWORD  - MySQL password
    MYSQL_DATABASE  - MySQL database name
    MYSQL_SSL_CA    - Optional SSL CA certificate path
"""

import os
import sys
from pathlib import Path
import argparse

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("[error] PyMySQL가 설치되지 않았습니다. pip install PyMySQL을 실행하세요.")
    sys.exit(1)


def get_db_config():
    """환경 변수에서 데이터베이스 설정을 가져옵니다."""
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
    }
    
    # SSL 설정
    ssl_ca = os.getenv('MYSQL_SSL_CA')
    if ssl_ca:
        config['ssl'] = {'ca': ssl_ca}
    
    # 필수 값 검증
    if not config['user']:
        raise ValueError("MYSQL_USER 환경 변수가 설정되지 않았습니다.")
    if not config['password']:
        raise ValueError("MYSQL_PASSWORD 환경 변수가 설정되지 않았습니다.")
    if not config['database']:
        raise ValueError("MYSQL_DATABASE 환경 변수가 설정되지 않았습니다.")
    
    return config


def read_sql_file(filepath):
    """SQL 파일을 읽어 반환합니다."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def execute_sql_statements(cursor, sql_content):
    """SQL 문을 실행합니다. 여러 문장을 세미콜론으로 분리하여 실행합니다."""
    # 간단한 방식으로 SQL 문장 분리 (주석과 빈 줄 제거)
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        # 주석 라인 건너뛰기
        if stripped.startswith('--') or not stripped:
            continue
            
        current_statement.append(line)
        
        # 세미콜론으로 끝나면 하나의 문장 완료
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement)
            statements.append(statement)
            current_statement = []
    
    # 각 문장 실행
    for statement in statements:
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
                print(f"[info] 실행 완료: {statement[:80]}...")
            except Exception as e:
                print(f"[error] SQL 실행 실패: {e}")
                print(f"[error] 문장: {statement[:200]}...")
                raise


def drop_existing_tables(cursor):
    """기존 테이블을 삭제합니다."""
    tables = [
        'user_audit_log',
        'email_verification_tokens',
        'password_reset_tokens',
        'user_sessions',
        'users'
    ]
    
    print("[info] 기존 테이블 삭제 중...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
            print(f"[info] 테이블 삭제: {table}")
        except Exception as e:
            print(f"[warn] 테이블 삭제 실패: {table} - {e}")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")


def main():
    parser = argparse.ArgumentParser(description='MCP Core 데이터베이스 초기화')
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='기존 테이블을 삭제하고 다시 생성합니다.'
    )
    args = parser.parse_args()
    
    print("[info] MCP Core 데이터베이스 초기화 시작")
    
    # 데이터베이스 설정 가져오기
    try:
        db_config = get_db_config()
        print(f"[info] 연결 대상: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    except ValueError as e:
        print(f"[error] 설정 오류: {e}")
        sys.exit(1)
    
    # SQL 스키마 파일 경로
    script_dir = Path(__file__).parent
    schema_file = script_dir / 'schemas' / '001_users_authentication.sql'
    
    if not schema_file.exists():
        print(f"[error] 스키마 파일을 찾을 수 없습니다: {schema_file}")
        sys.exit(1)
    
    # SQL 파일 읽기
    print(f"[info] 스키마 파일 읽기: {schema_file}")
    sql_content = read_sql_file(schema_file)
    
    # 데이터베이스 연결 및 스키마 생성
    connection = None
    try:
        print("[info] 데이터베이스 연결 중...")
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        # 기존 테이블 삭제 (옵션)
        if args.drop_existing:
            drop_existing_tables(cursor)
        
        # 스키마 실행
        print("[info] 스키마 생성 중...")
        execute_sql_statements(cursor, sql_content)
        
        # 변경사항 커밋
        connection.commit()
        print("[info] 스키마 생성 완료")
        
        # 생성된 테이블 확인
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print("\n[info] 생성된 테이블:")
        for table in tables:
            table_name = list(table.values())[0]
            print(f"  - {table_name}")
        
        print("\n[info] 데이터베이스 초기화 성공!")
        
    except Exception as e:
        print(f"\n[error] 데이터베이스 초기화 실패: {e}")
        if connection:
            connection.rollback()
        sys.exit(1)
    finally:
        if connection:
            connection.close()
            print("[info] 데이터베이스 연결 종료")


if __name__ == '__main__':
    main()
