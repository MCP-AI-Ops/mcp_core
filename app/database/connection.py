"""
Database connection module for MCP Core user management.

환경 변수를 통해 데이터베이스 연결을 설정하고 관리합니다.
"""

import os
from typing import Optional
from urllib.parse import quote_plus
from contextlib import contextmanager

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from app.core.errors import DataSourceError


class DatabaseConnection:
    """데이터베이스 연결 관리 클래스"""
    
    _engine = None
    _session_factory = None
    
    @classmethod
    def initialize(
        cls,
        connection_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        ssl_ca: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        """
        데이터베이스 연결을 초기화합니다.
        
        Args:
            connection_url: 직접 제공하는 연결 URL
            host: 데이터베이스 호스트
            port: 데이터베이스 포트
            user: 데이터베이스 사용자
            password: 데이터베이스 비밀번호
            database: 데이터베이스 이름
            ssl_ca: SSL CA 인증서 경로
            pool_size: 연결 풀 크기
            max_overflow: 최대 오버플로우
        """
        if not SQLALCHEMY_AVAILABLE:
            raise DataSourceError("SQLAlchemy가 설치되지 않아 데이터베이스를 초기화할 수 없음")
        
        if connection_url:
            url = connection_url
        else:
            # 환경 변수에서 설정 가져오기
            host = host or os.getenv("MYSQL_HOST", "localhost")
            port = port or int(os.getenv("MYSQL_PORT", "3306"))
            user = user or os.getenv("MYSQL_USER", "")
            password = password or os.getenv("MYSQL_PASSWORD", "")
            database = database or os.getenv("MYSQL_DATABASE", "")
            
            if not database:
                raise DataSourceError("MYSQL_DATABASE 환경 변수가 비어 있음")
            
            user_enc = quote_plus(user)
            password_enc = quote_plus(password)
            url = f"mysql+pymysql://{user_enc}:{password_enc}@{host}:{port}/{database}?charset=utf8mb4"
        
        # SSL 설정
        connect_args = {}
        ssl_ca = ssl_ca or os.getenv("MYSQL_SSL_CA")
        if ssl_ca:
            connect_args["ssl"] = {"ca": ssl_ca}
        
        # 엔진 생성
        try:
            cls._engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
            cls._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=cls._engine,
            )
        except Exception as exc:
            raise DataSourceError(f"SQLAlchemy 엔진 생성 실패: {exc}")
    
    @classmethod
    def get_engine(cls):
        """SQLAlchemy 엔진을 반환합니다."""
        if cls._engine is None:
            cls.initialize()
        return cls._engine
    
    @classmethod
    def get_session_factory(cls):
        """세션 팩토리를 반환합니다."""
        if cls._session_factory is None:
            cls.initialize()
        return cls._session_factory
    
    @classmethod
    @contextmanager
    def get_session(cls):
        """
        데이터베이스 세션을 제공하는 컨텍스트 매니저입니다.
        
        Usage:
            with DatabaseConnection.get_session() as session:
                # 세션 사용
                result = session.execute(...)
        """
        session_factory = cls.get_session_factory()
        session: Session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @classmethod
    def is_available(cls) -> bool:
        """데이터베이스 연결 가능 여부를 확인합니다."""
        try:
            engine = cls.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    @classmethod
    def close(cls) -> None:
        """데이터베이스 연결을 종료합니다."""
        if cls._engine:
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None


# 편의 함수
def get_db_session():
    """
    데이터베이스 세션을 가져오는 의존성 함수입니다.
    FastAPI 라우터에서 사용할 수 있습니다.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            # db 세션 사용
    """
    session_factory = DatabaseConnection.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
