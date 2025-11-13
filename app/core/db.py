"""MVP용 최소 DB 유틸리티 레이어.

DATABASE_URL 환경 변수가 설정된 경우에만 SQLAlchemy 사용.
그렇지 않으면 no-op stub으로 동작.

테이블 구조 (schema_mvp.sql): repositories, plan_requests, predictions,
anomaly_detections, alert_history.
"""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from typing import Any, Dict, Optional

DATABASE_URL = os.getenv("DATABASE_URL")  # 예: mysql+pymysql://user:pass@host/db

_engine = None
SessionLocal = None


def _init_engine():
    """엔진 및 세션 팩토리 초기화."""
    global _engine, SessionLocal
    if not DATABASE_URL:
        return
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    except Exception as e:
        # 에러 로그만 남기고 앱은 계속 실행 (no-op DB)
        print(f"[db] 엔진 초기화 실패: {e}")


_init_engine()


@contextmanager
def get_session():
    """DB 세션 컨텍스트 매니저. DB 비활성화 시 더미 세션 반환."""
    if SessionLocal is None:
        # DB가 없을 때 사용하는 더미 세션 객체
        class DummySession:
            def add(self, *_args, **_kwargs):
                pass

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                pass

            def execute(self, *_args, **_kwargs):
                pass

        ds = DummySession()
        yield ds
        return
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        print(f"[db] 세션 에러: {e}")
        session.rollback()
    finally:
        session.close()


def ensure_repository(repo_url: str, repo_name: str, provider: str = "unknown") -> Optional[int]:
    """저장소를 조회하거나 삽입하고 repo_id 반환 (DB 비활성화 시 None)."""
    if SessionLocal is None:
        return None
    from sqlalchemy import text
    with get_session() as s:
        row = s.execute(text("SELECT repo_id FROM repositories WHERE repo_url=:u"), {"u": repo_url}).fetchone()
        if row:
            return row[0]
        s.execute(
            text("INSERT INTO repositories(repo_url, repo_name, repo_provider) VALUES(:u,:n,:p)"),
            {"u": repo_url, "n": repo_name, "p": provider},
        )
        new_row = s.execute(text("SELECT repo_id FROM repositories WHERE repo_url=:u"), {"u": repo_url}).fetchone()
        return new_row[0] if new_row else None


def record_plan_request(
    repo_id: Optional[int], github_url: str, metric_name: str, context: Dict[str, Any]
) -> Optional[int]:
    """플랜 요청을 기록하고 plan_request_id 반환."""
    if SessionLocal is None or repo_id is None:
        return None
    from sqlalchemy import text
    with get_session() as s:
        s.execute(
            text(
                """
            INSERT INTO plan_requests (repo_id, github_url, metric_name, context_json)
            VALUES (:r, :s, :m, :c)
        """
            ),
            {"r": repo_id, "s": github_url, "m": metric_name, "c": json.dumps(context)},
        )
        row = s.execute(text("SELECT LAST_INSERT_ID()"))
        return row.scalar()


def record_prediction(
    repo_id: Optional[int],
    start_ts: str,
    horizon_hours: int,
    metric_name: str,
    model_version: str,
    predicted_values: list[float],
    rec_min: int,
    rec_max: int,
    expected_cost: Optional[float],
) -> Optional[int]:
    """예측 결과를 기록하고 prediction_id 반환."""
    if SessionLocal is None or repo_id is None:
        return None
    from sqlalchemy import text
    with get_session() as s:
        s.execute(
            text(
                """
            INSERT INTO predictions (repo_id, prediction_start, prediction_horizon_hours, metric_name, model_version,
                                     predicted_values, recommended_min_instances, recommended_max_instances, expected_cost_per_day)
            VALUES (:r, :ps, :h, :mn, :mv, :pv, :rmin, :rmax, :cost)
        """
            ),
            {
                "r": repo_id,
                "ps": start_ts,
                "h": horizon_hours,
                "mn": metric_name,
                "mv": model_version,
                "pv": json.dumps(predicted_values),
                "rmin": rec_min,
                "rmax": rec_max,
                "cost": expected_cost,
            },
        )
        row = s.execute(text("SELECT LAST_INSERT_ID()"))
        return row.scalar()


def record_anomaly(
    repo_id: Optional[int],
    prediction_id: Optional[int],
    score: float,
    detail: Dict[str, Any],
    severity: str = "medium",
    anomaly_type: str = "deviation",
    alert_sent: bool = False,
) -> Optional[int]:
    """이상 탐지 결과를 기록하고 anomaly_id 반환."""
    if SessionLocal is None or repo_id is None:
        return None
    from sqlalchemy import text
    with get_session() as s:
        s.execute(
            text(
                """
            INSERT INTO anomaly_detections (repo_id, prediction_id, anomaly_type, severity, anomaly_score, detail_json, alert_sent)
            VALUES (:r, :pid, :atype, :sev, :score, :detail, :asent)
        """
            ),
            {
                "r": repo_id,
                "pid": prediction_id,
                "atype": anomaly_type,
                "sev": severity,
                "score": score,
                "detail": json.dumps(detail),
                "asent": alert_sent,
            },
        )
        row = s.execute(text("SELECT LAST_INSERT_ID()"))
        return row.scalar()


def record_alert(
    repo_id: Optional[int],
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    channels: list[str],
    status: str,
    response_text: Optional[str],
) -> Optional[int]:
    """알림 전송 이력을 기록하고 alert_id 반환."""
    if SessionLocal is None or repo_id is None:
        return None
    from sqlalchemy import text
    with get_session() as s:
        s.execute(
            text(
                """
            INSERT INTO alert_history (repo_id, alert_type, severity, title, message, channels, status, response_text)
            VALUES (:r, :atype, :sev, :title, :msg, :channels, :status, :resp)
        """
            ),
            {
                "r": repo_id,
                "atype": alert_type,
                "sev": severity,
                "title": title,
                "msg": message,
                "channels": json.dumps(channels),
                "status": status,
                "resp": response_text,
            },
        )
        row = s.execute(text("SELECT LAST_INSERT_ID()"))
        return row.scalar()

