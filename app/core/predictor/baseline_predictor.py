"""
Baseline Predictor
간단한 통계 기반 예측과 폴백 로직을 제공한다.
"""

from datetime import datetime, timedelta

import numpy as np

from app.models.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor
from .data_sources import get_data_source
from app.core.errors import DataNotFoundError


class BaselinePredictor(BasePredictor):
    """최근 데이터의 통계값으로 24시간 예측을 생성한다."""

    def __init__(self) -> None:
        try:
            self.data_source = get_data_source()
            print("[정보] Baseline Predictor 초기화 완료")
        except Exception as exc:
            print(f"[경고] 데이터 소스를 초기화할 수 없음: {exc}")
            self.data_source = None

    def run(
        self,
        *,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
    ) -> PredictionResult:
        try:
            if self.data_source is not None:
                recent = self.data_source.fetch_historical_data(
                    service_id=service_id,
                    metric_name=metric_name,
                    hours=24,
                )
                return self._statistical_prediction(
                    service_id, metric_name, ctx, model_version, recent
                )
        except (DataNotFoundError, Exception) as exc:
            print(f"[경고] 데이터 수집 실패: {exc}, 폴백 경로 사용")

        return self._fallback_prediction(service_id, metric_name, ctx, model_version)

    def _statistical_prediction(
        self,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
        recent_data: np.ndarray,
    ) -> PredictionResult:
        avg = float(recent_data.mean())
        std = float(recent_data.std())
        last_value = float(recent_data[-1])
        trend = float(recent_data[-1] - recent_data[0]) / len(recent_data)

        print(
            f"[디버그] 통계값: 평균={avg:.2f}, 표준편차={std:.2f}, 추세={trend:.2f}"
        )

        if ctx.time_slot == "peak":
            slope_factor = 1.2
        elif ctx.time_slot == "low":
            slope_factor = 0.8
        else:
            slope_factor = 1.0

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        predictions = []

        for step in range(1, 25):
            value = last_value + trend * step * slope_factor
            noise = np.random.normal(0, std * 0.05)
            value = max(0, value + noise)

            if metric_name == "total_events":
                value = round(value)

            predictions.append(
                PredictionPoint(time=now + timedelta(hours=step), value=float(value))
            )

        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=f"{model_version}_statistical",
            generated_at=datetime.utcnow(),
            predictions=predictions,
        )

    def _fallback_prediction(
        self,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
    ) -> PredictionResult:
        print("[경고] 데이터 부족으로 폴백 예측 실행")

        if metric_name == "total_events":
            base = 50.0
            slope = 0.5
        elif metric_name in ("avg_cpu", "avg_memory"):
            base = 0.3
            slope = 0.01
        else:
            base = 10.0
            slope = 0.1

        if ctx.time_slot == "peak":
            slope *= 2
        elif ctx.time_slot == "low":
            slope *= 0.5

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        predictions = []

        for step in range(1, 25):
            value = base + slope * step

            if metric_name == "total_events":
                value = round(value)

            predictions.append(
                PredictionPoint(time=now + timedelta(hours=step), value=float(value))
            )

        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=f"{model_version}_fallback",
            generated_at=datetime.utcnow(),
            predictions=predictions,
        )
