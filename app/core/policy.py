# app/core/policy.py
from datetime import datetime
from app.models.common import PredictionResult, PredictionPoint, MCPContext

# lo= low bound, hi= high bound
def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if v != v:  # NaN
        return 0.0
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def apply_weight(value: float, weight: float) -> float:
    return value * weight

def postprocess_predictions(pred: PredictionResult, ctx: MCPContext) -> PredictionResult:
    """예측 결과에 컨텍스트 기반 보정 적용 (가중치 → 클램핑)."""
    weighted = [
        PredictionPoint(time=p.time, value=apply_weight(p.value, ctx.weight))
        for p in pred.predictions
    ]
    clamped = [PredictionPoint(time=p.time, value=clamp(p.value)) for p in weighted]
    return PredictionResult(
        service_id=pred.service_id,
        metric_name=pred.metric_name,
        model_version=pred.model_version,
        generated_at=datetime.utcnow(),
        predictions=clamped,
    )
