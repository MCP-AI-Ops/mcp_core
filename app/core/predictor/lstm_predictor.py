# app/core/predictor/lstm_predictor.py

"""
LSTMPredictor (stub).

역할:
- 실제 LSTM 기반 예측 모델을 연결할 위치.
- 향후 TensorFlow/PyTorch 모델(.h5 / .pt)과 scaler.pkl을 로드하고,
  최근 24h metrics를 기반으로 24h 후 예측을 생성할 예정이다.

현재 상태:
- run()은 고정값(0.5)을 반환하는 mock이다.
- 이 mock은 /plans 엔드포인트와 policy 후처리 흐름을 점검하기 위한 용도다.

향후 계획:
- settings.MODEL_PATH, settings.SCALER_PATH에서 모델/스케일러 로드
- metrics_repo.fetch_last_24h_metrics()로 DB에서 최근 관측값 수집
- 스케일링 → model.predict() → inverse scaling → PredictionResult 구성
"""

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
        """
        LSTM 기반 예측 (현재는 mock).

        now 기준으로 다음 24시간에 대해 value=0.5 고정값을 반환한다.
        이 값은 policy에서 가중치/클램핑을 거쳐 안정화된 후 /plans 응답에 포함된다.
        """
        
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