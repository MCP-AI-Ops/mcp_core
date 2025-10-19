from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .common import MCPContext, PredictionResult

class PlansRequest(BaseModel):
    service_id: str
    metric_name: str = "total_events"
    context: MCPContext

class PlansResponse(BaseModel):
    prediction: PredictionResult
    recommended_flavor: str
    expected_cost_per_day: float
    generated_at: datetime
    notes: Optional[str] = None
