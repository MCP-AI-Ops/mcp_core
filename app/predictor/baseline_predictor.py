from datetime import datetime, timedelta
from app.modles.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor


#이동평균/표준편차 등 간단 통계 기반 더미 예측기. 진호 수정?
class BaselinePredictor(BasePredictor):
    def run(self, *, service_id: str, metric_name: str, ctx: MCPContext, model_version: str) -> PredictionResult:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        preds = []
        base = 0.3  # 임시 값
        slope = 0.01 if ctx.time_slot in ("normal", "low") else 0.02
        for k in range(1, 25):
            preds.append(PredictionPoint(time=now + timedelta(hours=k), value=base + slope * k))
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=preds
        )