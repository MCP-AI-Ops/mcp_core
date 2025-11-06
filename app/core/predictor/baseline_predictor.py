# app/core/predictor/baseline_predictor.py

"""
BaselinePredictor.

역할:
- 간단한 통계/휴리스틱 기반 예측을 생성한다.
- 현재 버전은 시뮬레이션 전용(데모용)으로, 향후 LSTM 모델이 붙기 전까지
  end-to-end 흐름(/plans -> predictor -> policy)을 검증하는 용도다.

동작:
- 현재 시간(now) 기준으로 다음 24시간에 대한 usage 값을 완만하게 증가시키는 형태로 만든다.
- time_slot(peak vs normal/low)에 따라 증가 속도(slope)를 달리 준다.
"""

from datetime import datetime, timedelta
from app.models.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor

#이동평균/표준편차 등 간단 통계 기반 더미 예측기. 진호 수정?
class BaselinePredictor(BasePredictor):
    def run(self, *, service_id: str, metric_name: str, ctx: MCPContext, model_version: str) -> PredictionResult:
        """
        Baseline 예측 수행.

        현재 구현은 실제 관측 데이터 없이도 예측 파이프라인을 테스트하기 위한 더미 로직이다.
        slope는 time_slot에 따라 달라지며, 이를 통해 peak 시간대에는 더 공격적인 리소스 사용량을
        가정한다.
        """
        
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