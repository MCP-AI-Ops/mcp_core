# app/core/predictor/base.py

"""
Predictor interface definition.

역할:
- 모든 예측 모델(Baseline, LSTM 등)이 동일한 호출 방식(run)을 갖도록 강제한다.
- /plans 같은 상위 레이어는 어떤 predictor가 오더라도 동일한 방식으로 호출 가능하다.
"""

from abc import ABC, abstractmethod
from app.models.common import MCPContext, PredictionResult

class BasePredictor(ABC):
    """
    Base class for all predictors.

    모든 Predictor 구현체는 run()을 제공해야 한다.
    run()은 service_id/metric_name/ctx/model_version을 받아서
    PredictionResult를 반환해야 한다.
    """

    @abstractmethod
    def run(self, *, service_id: str, metric_name: str, ctx: MCPContext, model_version: str) -> PredictionResult:
        """
        Execute prediction for the given (service_id, metric_name) under context ctx.

        Returns
        -------
        PredictionResult
            예측된 시계열 데이터 목록(predictions[])과 메타정보(model_version 등)를 포함한다.
        """
        
        ...