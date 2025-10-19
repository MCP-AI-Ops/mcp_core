from datetime import datetime
from app.models.common import PredictionResult, PredictionPoint, MCPContext

def clamp (v: float, low_bound: float = 0.0, high_bound: float = 1.0) -> float:
    if v != v: # NaN
        return 0.0
    if v < low_bound:
        return low_bound
    if v > high_bound:
        return high_bound
    return v

def apply_weight(value: float, weight: float) -> float:
    return value * weight

def postprocess_prediction(pred: PredictionResult, context: MCPContext) ->PredictionResult:
    weighted = [
        PredictionPoint(time= p.time, value= apply_weight(p.value, context.weight))
        for p in pred.predictions
    ]

    clamped = [
        PredictionPoint(time= p.time, value= clamp(p.value))
        for p in weighted
    ]

    return PredictionResult(
        service_id= pred.service_id,
        metric_name= pred.metric_name,
        model_version= pred.model_version,
        generated_at= datetime(), # utcnow() 더이상 사용 안된다고 해서 이거는 나중에 시간 많을 때 대체 함수 찾아볼게요
        predictions= clamped,
    )