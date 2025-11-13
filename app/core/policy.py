# app/core/policy.py
"""
Prediction post-processing policy.

- 가중치(weight) 적용
- 메트릭 특성에 맞는 clamp/보정
- downstream 시스템이 바로 활용할 수 있는 안정된 값 제공
"""

from datetime import datetime

from app.core.metrics import get_metric_meta
from app.models.common import MCPContext, PredictionPoint, PredictionResult


def apply_weight(value: float, weight: float) -> float:
    """서비스별 중요도 가중치 반영."""
    return value * weight


def postprocess_predictions(pred: PredictionResult, ctx: MCPContext) -> PredictionResult:
    """
    Predictor가 생성한 PredictionResult를 정책적으로 보정한다.

    단계:
        1) 컨텍스트 weight만큼 scaling
        2) ratio/count 메트릭에 따른 clamp 정책 적용
    """

    meta = get_metric_meta(pred.metric_name)
    processed = []
    for point in pred.predictions:
        weighted_value = apply_weight(point.value, ctx.weight)
        if meta.kind == "ratio":
            adjusted = meta.clamp(weighted_value)
        else:
            adjusted = weighted_value if weighted_value >= meta.clamp_min else meta.clamp_min
        processed.append(PredictionPoint(time=point.time, value=adjusted))

    return PredictionResult(
        github_url=pred.github_url,
        metric_name=pred.metric_name,
        model_version=pred.model_version,
        generated_at=datetime.utcnow(),
        predictions=processed,
    )
