from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .common import MCPContext, PredictionResult

class PlansRequest(BaseModel):
    github_url: str
    metric_name: str = "total_events"
    context: MCPContext
    requirements: Optional[str] = None  # 자연어 요청사항 (프론트엔드에서 전송)

class PlansResponse(BaseModel):
    prediction: PredictionResult
    recommended_flavor: str
    expected_cost_per_day: float
    generated_at: datetime
    notes: Optional[str] = None

# --- Multi-metric variants (non-breaking addition) ---
class MultiPlansRequest(BaseModel):
    github_url: str
    metric_names: list[str]
    context: MCPContext
    requirements: Optional[str] = None

class MultiPlansResponse(BaseModel):
    # Mapping of metric_name -> PlansResponse (keeps original contract per metric)
    results: dict[str, PlansResponse]
    generated_at: datetime
