"""
SQLAlchemy ORM 모델: metric_history (LSTM feature 시계열)
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Float, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MetricHistory(Base):
    __tablename__ = "metric_history"
    __table_args__ = (
        UniqueConstraint("github_url", "ts", "metric_name", name="uk_metric"),
        Index("idx_github_url", "github_url"),
        Index("idx_metric_name", "metric_name"),
        Index("idx_ts", "ts"),
        {"mysql_engine": "InnoDB", "mysql_comment": "LSTM feature_names 전체를 저장하는 시계열 테이블"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="row id")
    github_url = Column(String(200), nullable=False, comment="서비스 구분자")
    ts = Column(DateTime, nullable=False, comment="타임스탬프 (UTC)")
    metric_name = Column(String(100), nullable=False, comment="feature 이름")
    value = Column(Float, nullable=False, comment="feature 값")
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, comment="적재 시각")

# 사용 예시:
# from app.core.db import get_session
# from .metric_history import MetricHistory
# with get_session() as session:
#     session.add(MetricHistory(github_url="https://github.com/xxx", ts=datetime.utcnow(), metric_name="avg_cpu", value=0.5))
#     session.commit()
