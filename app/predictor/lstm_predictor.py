from datetime import datetime, timedelta
from app.models.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor

# NOTE:
# 실제 LSTM 서빙(keras/torch 로드 + scaler 역변환)은 TODO.
# 지금은 인터페이스와 호출 경로만 동일하게 맞춘 더미 반환을 둔다.
# 진호 수정?

class LSTMPredictor(BasePredictor):
    def __init__(self):
        # TODO: 모델/스케일러 로드
        pass

    def run(self, *, service_id: str, metric_name: str, ctx: MCPContext, model_version: str) -> PredictionResult:
        # TODO: 최근 24h metrics 조회 → 전처리 → model.predict → 역변환
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        preds = [PredictionPoint(time=now + timedelta(hours=k), value=0.5) for k in range(1, 25)]
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=preds
        )