from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.common import MCPContext

FlavorType = Literal["small", "medium", "large"]


class FlavorBreakpoints(BaseModel):
    p25: float
    p50: float
    p75: float
    mean: float
    stdev: float


class HourlyFlavorRecommendation(BaseModel):
    hour_index: int = Field(ge=0, le=23)
    timestamp: datetime
    predicted_value: float
    percentile: float = Field(ge=0.0, le=1.0)
    recommended_flavor: FlavorType
    hourly_cost: float


class HourlyPlansRequest(BaseModel):
    github_url: str
    metric_name: str = "total_events"
    context: MCPContext
    model_version: Optional[str] = None
    fallback_to_baseline: bool = True


class HourlyPlansResponse(BaseModel):
    github_url: str
    metric_name: str
    model_version: str
    generated_at: datetime
    hourly_recommendations: list[HourlyFlavorRecommendation]
    breakpoints: FlavorBreakpoints
    total_expected_cost_24h: float
    notes: Optional[str] = None
