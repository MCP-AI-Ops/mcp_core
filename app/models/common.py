# API 전체에서 공통으로 쓰이는 스키마 모아둔 곳

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

TimeSlot = Literal["peak", "normal", "low", "weekend"]
RuntimeEnv = Literal["prod", "dev"]
ServiceType = Literal["web", "api", "db"]

class MCPContext(BaseModel):
    context_id: str
    timestamp: datetime
    service_type: ServiceType
    runtime_env: RuntimeEnv = "prod"
    time_slot: TimeSlot = "normal"
    weight: float = Field(1.0, ge=0.0)
    region: Optional[str] = None
    expected_users: Optional[int] = Field(default=None, ge=0)
    curr_cpu: Optional[float] = Field(default=None, ge=0.0)
    curr_mem: Optional[float] = Field(default=None, ge=0.0)

class PredictionPoint(BaseModel):
    time: datetime
    value: float

class PredictionResult(BaseModel):
    service_id: str
    metric_name: str
    model_version: str
    generated_at: datetime
    predictions: list[PredictionPoint]

class AnomalyResult(BaseModel):
    anomaly_detected: bool
    anomaly_score: float
    anomaly_type: Optional[str] = None
