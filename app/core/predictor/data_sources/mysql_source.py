import os
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import numpy as np

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    SQLALCHEMY_AVAILABLE = True
except Exception:  # pragma: no cover
    create_engine = None
    Engine = None # type: ignore
    SQLALCHEMY_AVAILABLE = False

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine import Engine as EngineType

from .base import DataSource
from app.core.errors import DataSourceError, DataNotFoundError


class MySQLDataSource(DataSource):
    """SQLAlchemy를 사용해 MySQL에서 시계열 데이터를 조회한다."""

    def __init__(
        self,
        *,
        connection_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        table: Optional[str] = None,
        ssl_ca: Optional[str] = None,
    ) -> None:
        if create_engine is None or Engine is None:
            raise DataSourceError("SQLAlchemy가 설치되지 않아 MySQL을 초기화할 수 없음")

        self.table = table or os.getenv("MYSQL_TABLE", "metric_history")

        if connection_url:
            url = connection_url
        else:
            host = host or os.getenv("MYSQL_HOST", "localhost")
            port = port or int(os.getenv("MYSQL_PORT", "3308"))
            user = user or os.getenv("MYSQL_USER", "")
            password = password or os.getenv("MYSQL_PASSWORD", "")
            database = database or os.getenv("MYSQL_DATABASE", "")

            if not database:
                raise DataSourceError("MYSQL_DATABASE 환경 변수가 비어 있음")

            user_enc = quote_plus(user)
            password_enc = quote_plus(password)
            url = f"mysql+pymysql://{user_enc}:{password_enc}@{host}:{port}/{database}?charset=utf8mb4"

        connect_args = {}
        ssl_ca = ssl_ca or os.getenv("MYSQL_SSL_CA", None)
        if ssl_ca:
            connect_args["ssl"] = {"ca": ssl_ca}

        try:
            self.engine: "EngineType" = create_engine(
                url,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
        except Exception as exc:
            raise DataSourceError(f"SQLAlchemy 엔진 생성 실패: {exc}")

    def fetch_historical_data(
        self,
        github_url: str,
        metric_name: str,
        hours: int = 168,
        end_time: Optional[datetime] = None,
    ) -> np.ndarray:
        if hours <= 0:
            raise ValueError("hours 값은 양수여야 함")

        end_ts = end_time or datetime.utcnow()
        start_ts = end_ts - timedelta(hours=hours - 1)

        stmt = text(
            f"""
            SELECT ts, value
            FROM {self.table}
            WHERE github_url = :github_url
              AND metric_name = :metric_name
              AND ts BETWEEN :start_ts AND :end_ts
            ORDER BY ts ASC
            """
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    stmt,
                    {
                        "github_url": github_url,
                        "metric_name": metric_name,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                    },
                )
                rows = result.fetchall()
        except Exception as exc:
            raise DataSourceError(f"MySQL 조회 실패: {exc}")

        if not rows:
            raise DataNotFoundError(f"{github_url}/{metric_name} 데이터 없음")

        values = np.array([float(row[1]) for row in rows], dtype=float)  # row[1] = value column

        if len(values) < hours:
            pad_len = hours - len(values)
            pad_val = values[0] if len(values) > 0 else 0.0
            pad = np.full(pad_len, pad_val, dtype=float)
            values = np.concatenate([pad, values])
        elif len(values) > hours:
            values = values[-hours:]

        return values

    def is_available(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
