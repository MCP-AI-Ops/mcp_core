"""Production SQLAlchemy ORM layer for MCP Core.

✅ 현재 활성화된 DB 레이어 (db.py는 deprecated)
This module provides idiomatic ORM patterns with models in `persistence_models.py`.

Key concepts demonstrated:
1. Engine & Session management
2. FastAPI dependency (`get_db`)
3. Basic CRUD (Create / Read / Update / Delete)
4. Bulk insert for prediction points
5. Query helpers (filtering, ordering, pagination)

You can import and use these in your routers, e.g.:

    from app.core.db_sqlalchemy import get_db
    from app.core.persistence_models import MCPContext

    @router.post("/contexts")
    def create_context(payload: ContextIn, db: Session = Depends(get_db)):
        ctx = MCPContext(...)
        db.add(ctx)
        db.commit()
        db.refresh(ctx)
        return ctx

NOTE: Table creation is optional since DDL is applied via .sql files.
Call `init_metadata()` only if you need to sync simple changes.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Iterator, List, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.persistence_models import (
    Base,
    MCPContext,
    PredictionFeature,
    Prediction,
    PredictionPoint,
)

# ---------------------------------------------------------------------------
# Engine / Session setup
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://mcp_user:wjdwlsgh03@localhost:3306/mcp_core",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Detect stale connections
    pool_recycle=1800,       # Recycle connections every 30 minutes
    future=True,             # Opt-in to SQLAlchemy 2.x style
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

# ---------------------------------------------------------------------------
# Dependency / Context managers
# ---------------------------------------------------------------------------

def get_db() -> Iterator[Session]:
    """FastAPI dependency style session provider."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for scripts / background jobs."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()

# ---------------------------------------------------------------------------
# Optional metadata initialization
# ---------------------------------------------------------------------------

def init_metadata(sync: bool = False) -> None:
    """Create tables if they do not exist.
    Only use when you intentionally manage schema via ORM.
    """
    if sync:
        Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# CREATE helpers
# ---------------------------------------------------------------------------

def create_context(
    db: Session,
    *,
    context_id: str,
    github_url: str,
    request_timestamp: datetime,
    context_json: dict,
    user_id: Optional[str] = None,
    requirements_text: Optional[str] = None,
    service_type: str = "web",
    runtime_env: str = "prod",
    time_slot: str = "normal",
    expected_users: Optional[int] = None,
    region: Optional[str] = None,
) -> MCPContext:
    obj = MCPContext(
        context_id=context_id,
        github_url=github_url,
        request_timestamp=request_timestamp,
        context_json=context_json,
        user_id=user_id,
        requirements_text=requirements_text,
        service_type=service_type,
        runtime_env=runtime_env,
        time_slot=time_slot,
        expected_users=expected_users,
        region=region,
    )
    db.add(obj)
    return obj

def create_feature_snapshot(
    db: Session,
    *,
    context_id: str,
    github_url: str,
    window_start: datetime,
    window_end: datetime,
    sequence_length: int,
    feature_count: int,
    features_json: dict,
) -> PredictionFeature:
    snap = PredictionFeature(
        context_id=context_id,
        github_url=github_url,
        window_start=window_start,
        window_end=window_end,
        sequence_length=sequence_length,
        feature_count=feature_count,
        features_json=features_json,
    )
    db.add(snap)
    return snap

def create_prediction(
    db: Session,
    *,
    context_id: str,
    feature_snapshot_id: int,
    github_url: str,
    metric_name: str,
    model_version: str,
    generated_at: datetime,
    predictions_json: list,
    user_id: Optional[str] = None,
    horizon_hours: int = 24,
    scale_factor: Optional[float] = None,
    recommended_flavor: Optional[str] = None,
    min_instances: int = 1,
    max_instances: int = 3,
    expected_cost_per_day: Optional[float] = None,
) -> Prediction:
    pred = Prediction(
        context_id=context_id,
        feature_snapshot_id=feature_snapshot_id,
        github_url=github_url,
        metric_name=metric_name,
        model_version=model_version,
        generated_at=generated_at,
        predictions_json=predictions_json,
        user_id=user_id,
        horizon_hours=horizon_hours,
        scale_factor=scale_factor,
        recommended_flavor=recommended_flavor,
        min_instances=min_instances,
        max_instances=max_instances,
        expected_cost_per_day=expected_cost_per_day,
    )
    db.add(pred)
    return pred

def bulk_points(
    db: Session,
    *,
    prediction_id: int,
    rows: List[dict],  # {forecast_time, predicted_value, actual_value?}
) -> None:
    db.add_all(
        [
            PredictionPoint(
                prediction_id=prediction_id,
                forecast_time=r["forecast_time"],
                predicted_value=r["predicted_value"],
                actual_value=r.get("actual_value"),
            )
            for r in rows
        ]
    )

# ---------------------------------------------------------------------------
# READ helpers (queries)
# ---------------------------------------------------------------------------

def get_context(db: Session, context_id: str) -> Optional[MCPContext]:
    return db.get(MCPContext, context_id)

def list_contexts(db: Session, github_url: str, limit: int = 20) -> List[MCPContext]:
    stmt = (
        select(MCPContext)
        .where(MCPContext.github_url == github_url)
        .order_by(MCPContext.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())

def list_predictions(db: Session, github_url: str, metric: Optional[str] = None, limit: int = 50) -> List[Prediction]:
    stmt = select(Prediction).where(Prediction.github_url == github_url)
    if metric:
        stmt = stmt.where(Prediction.metric_name == metric)
    stmt = stmt.order_by(Prediction.generated_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars())

# ---------------------------------------------------------------------------
# UPDATE / DELETE examples
# ---------------------------------------------------------------------------

def update_prediction_scale(db: Session, prediction_id: int, new_scale: float) -> bool:
    pred = db.get(Prediction, prediction_id)
    if not pred:
        return False
    pred.scale_factor = new_scale
    return True

def delete_prediction(db: Session, prediction_id: int) -> bool:
    pred = db.get(Prediction, prediction_id)
    if not pred:
        return False
    db.delete(pred)
    return True

# ---------------------------------------------------------------------------
# Demo script (invoke: python -m app.core.db_sqlalchemy)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uuid
    from datetime import timedelta

    print("[demo] ORM create + query demo starting...")
    with session_scope() as s:
        ctx_id = str(uuid.uuid4())
        ctx = create_context(
            s,
            context_id=ctx_id,
            github_url="https://github.com/org/repo",
            request_timestamp=datetime.utcnow(),
            context_json={"source": "demo"},
            user_id="userA",
            requirements_text="트래픽 증가 대비",
        )
        snap = create_feature_snapshot(
            s,
            context_id=ctx_id,
            github_url=ctx.github_url,
            window_start=datetime.utcnow() - timedelta(hours=24),
            window_end=datetime.utcnow(),
            sequence_length=24,
            feature_count=79,
            features_json={"features": [1,2,3]},
        )
        pred = create_prediction(
            s,
            context_id=ctx_id,
            feature_snapshot_id=snap.feature_snapshot_id,
            github_url=ctx.github_url,
            metric_name="total_events",
            model_version="lstm_v1",
            generated_at=datetime.utcnow(),
            predictions_json=[{"time": i, "value": 100+i} for i in range(24)],
            recommended_flavor="medium",
        )
        bulk_points(
            s,
            prediction_id=pred.prediction_id,
            rows=[
                {"forecast_time": datetime.utcnow() + timedelta(hours=i+1), "predicted_value": 100+i}
                for i in range(24)
            ],
        )
        print(f"Created context={ctx.context_id}, prediction={pred.prediction_id}")
    with session_scope() as s:
        recent = list_predictions(s, github_url="https://github.com/org/repo", limit=5)
        print(f"Recent predictions: {[p.prediction_id for p in recent]}")
    print("[demo] Done.")
