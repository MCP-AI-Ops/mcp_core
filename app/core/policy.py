# app/core/policy.py

"""
Policy module.

역할:
- Predictor가 생성한 원시 예측값을 후처리(postprocess)한다.
- 가중치(weight) 적용, 값 범위 제한(clamp) 등 안정화 로직을 담당한다.
- downstream(배포/스케일링 로직)이 신뢰 가능한 값만 소비하도록 해준다.
"""

from datetime import datetime
from app.models.common import PredictionResult, PredictionPoint, MCPContext

# lo= low bound, hi= high bound
def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """
    값 v를 [lo, hi] 범위 안으로 강제(clamp)한다.
    NaN 등 이상값은 자동으로 0.0으로 수렴시킨다.

    사용 이유:
    - CPU 사용률, Memory 사용률 등은 (0.0 ~ 1.0) 비율로 가정하고 처리한다.
    - 비정상적으로 튀는 예측값을 그대로 내려보내면 auto-scaling 의사결정이 망가질 수 있으므로
      여기서 한 번 안정화한다.
    """

    if v != v:  # NaN
        return 0.0
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def apply_weight(value: float, weight: float) -> float:
    """
    서비스별 중요도, 정책 가중치 등을 반영하기 위한 스케일링.
    """
    
    return value * weight

def postprocess_predictions(pred: PredictionResult, ctx: MCPContext) -> PredictionResult:
    """
    Predictor가 반환한 PredictionResult를 정책적으로 보정한다.

    단계:
    1) 컨텍스트에서 온 weight를 각 시점 값에 곱해준다.
    2) clamp()를 통해 값이 [0,1] 범위를 벗어나지 않도록 제한한다.

    결과:
    - downstream (/plans 응답, 배포 추천 로직)은 이미 안정화된 수치를 그대로 사용 가능하다.
    - 즉, 이후 단계는 별도의 이상치 필터링 없이도 동작하도록 설계했다.
    """
    
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
