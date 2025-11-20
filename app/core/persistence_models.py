"""
SQLAlchemy ORM models for persistence (mcp_contexts, prediction_features, predictions, prediction_points)
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Float, TIMESTAMP, Text, Integer, DECIMAL, Enum as SQLEnum, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

# Enum types
class ServiceType(str, enum.Enum):
    web = "web"
    api = "api"
    db = "db"

class RuntimeEnv(str, enum.Enum):
    prod = "prod"
    dev = "dev"

class TimeSlot(str, enum.Enum):
    peak = "peak"
    normal = "normal"
    low = "low"
    weekend = "weekend"

class FlavorType(str, enum.Enum):
    small = "small"
    medium = "medium"
    large = "large"


class MCPContext(Base):
    __tablename__ = "mcp_contexts"
    __table_args__ = (
        Index("idx_user_time", "user_id", "created_at"),
        Index("idx_github", "github_url"),
        Index("idx_time_slot", "time_slot"),
        {"mysql_engine": "InnoDB", "mysql_comment": "MCP 컨텍스트 스냅샷 (사용자 매핑 포함)"}
    )

    context_id = Column(String(36), primary_key=True, comment="UUID")
    user_id = Column(String(100), nullable=True, comment="사용자 식별자 (email, user_id 등)")
    github_url = Column(String(500), nullable=False)
    requirements_text = Column(Text, nullable=True, comment="사용자 자연어 요구사항 원본")
    service_type = Column(SQLEnum(ServiceType), nullable=False, default=ServiceType.web)
    runtime_env = Column(SQLEnum(RuntimeEnv), nullable=False, default=RuntimeEnv.prod)
    time_slot = Column(SQLEnum(TimeSlot), nullable=False, default=TimeSlot.normal)
    expected_users = Column(Integer, nullable=True)
    region = Column(String(50), nullable=True)
    request_timestamp = Column(DateTime, nullable=False, comment="사용자 요청 시각 (MCPContext.timestamp)")
    context_json = Column(JSON, nullable=False, comment="Claude 변환한 전체 컨텍스트")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    prediction_features = relationship("PredictionFeature", back_populates="context", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="context", cascade="all, delete-orphan")


class PredictionFeature(Base):
    __tablename__ = "prediction_features"
    __table_args__ = (
        Index("idx_context", "context_id"),
        Index("idx_github_window", "github_url", "window_end"),
        {"mysql_engine": "InnoDB", "mysql_comment": "예측에 사용된 feature 스냅샷"}
    )

    feature_snapshot_id = Column(BigInteger, primary_key=True, autoincrement=True)
    context_id = Column(String(36), ForeignKey("mcp_contexts.context_id", ondelete="CASCADE"), nullable=False)
    github_url = Column(String(500), nullable=False)
    window_start = Column(DateTime, nullable=False, comment="사용된 feature 시작 시간")
    window_end = Column(DateTime, nullable=False, comment="사용된 feature 종료 시간")
    sequence_length = Column(Integer, nullable=False, comment="시퀀스 길이 (예: 24시간)")
    feature_count = Column(Integer, nullable=False, comment="feature 개수 (예: 79개)")
    features_json = Column(JSON, nullable=False, comment="feature_names + 값들 (압축 가능)")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    context = relationship("MCPContext", back_populates="prediction_features")
    predictions = relationship("Prediction", back_populates="feature_snapshot")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("idx_user_time", "user_id", "generated_at"),
        Index("idx_github_metric", "github_url", "metric_name", "generated_at"),
        Index("idx_model", "model_version"),
        {"mysql_engine": "InnoDB", "mysql_comment": "후처리된 예측 결과 (사용자+시간 매핑)"}
    )

    prediction_id = Column(BigInteger, primary_key=True, autoincrement=True)
    context_id = Column(String(36), ForeignKey("mcp_contexts.context_id", ondelete="CASCADE"), nullable=False)
    feature_snapshot_id = Column(BigInteger, ForeignKey("prediction_features.feature_snapshot_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(100), nullable=True, comment="예측을 요청한 사용자")
    github_url = Column(String(500), nullable=False)
    metric_name = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=False)
    generated_at = Column(DateTime, nullable=False, comment="예측 생성 시각 (= request_timestamp)")
    horizon_hours = Column(Integer, nullable=False, default=24)
    predictions_json = Column(JSON, nullable=False, comment="24시간 후처리된 예측값 [{time, value}, ...]")
    scale_factor = Column(DECIMAL(12, 6), nullable=True, comment="컨텍스트 스케일 팩터")
    recommended_flavor = Column(SQLEnum(FlavorType), nullable=True)
    min_instances = Column(Integer, nullable=False, default=1)
    max_instances = Column(Integer, nullable=False, default=3)
    expected_cost_per_day = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    context = relationship("MCPContext", back_populates="predictions")
    feature_snapshot = relationship("PredictionFeature", back_populates="predictions")
    prediction_points = relationship("PredictionPoint", back_populates="prediction", cascade="all, delete-orphan")


class PredictionPoint(Base):
    __tablename__ = "prediction_points"
    __table_args__ = (
        Index("idx_prediction", "prediction_id"),
        Index("idx_forecast_time", "forecast_time"),
        {"mysql_engine": "InnoDB", "mysql_comment": "시간별 예측값 (시간 매핑, 실제값 비교용)"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    prediction_id = Column(BigInteger, ForeignKey("predictions.prediction_id", ondelete="CASCADE"), nullable=False)
    forecast_time = Column(DateTime, nullable=False, comment="예측 대상 시각 (미래 시점)")
    predicted_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=True, comment="나중에 실제 발생한 값 (피드백용)")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    prediction = relationship("Prediction", back_populates="prediction_points")


# 사용 예시:
# from app.core.db import get_session
# from app.core.persistence_models import MCPContext, PredictionFeature, Prediction, PredictionPoint
# import uuid
# from datetime import datetime, timedelta
#
# with get_session() as session:
#     # 1. Context 저장
#     ctx_id = str(uuid.uuid4())
#     ctx = MCPContext(
#         context_id=ctx_id,
#         user_id="user123",
#         github_url="https://github.com/org/repo",
#         requirements_text="피크 시간대 스케일업 필요",
#         service_type="web",
#         time_slot="peak",
#         expected_users=1000,
#         request_timestamp=datetime.utcnow(),
#         context_json={"key": "value"}
#     )
#     session.add(ctx)
#
#     # 2. Feature 저장
#     fs = PredictionFeature(
#         context_id=ctx_id,
#         github_url="https://github.com/org/repo",
#         window_start=datetime.utcnow() - timedelta(hours=24),
#         window_end=datetime.utcnow(),
#         sequence_length=24,
#         feature_count=79,
#         features_json={"features": [...]}
#     )
#     session.add(fs)
#     session.flush()  # feature_snapshot_id 생성
#
#     # 3. Prediction 저장
#     pred = Prediction(
#         context_id=ctx_id,
#         feature_snapshot_id=fs.feature_snapshot_id,
#         user_id="user123",
#         github_url="https://github.com/org/repo",
#         metric_name="total_events",
#         model_version="lstm_v1",
#         generated_at=datetime.utcnow(),
#         predictions_json=[{"time": "...", "value": 123.4}, ...],
#         scale_factor=1.2,
#         recommended_flavor="medium",
#         expected_cost_per_day=2.8
#     )
#     session.add(pred)
#     session.flush()  # prediction_id 생성
#
#     # 4. Prediction Points 저장 (선택)
#     for i in range(24):
#         pp = PredictionPoint(
#             prediction_id=pred.prediction_id,
#             forecast_time=datetime.utcnow() + timedelta(hours=i+1),
#             predicted_value=120.5 + i
#         )
#         session.add(pp)
#
#     session.commit()
