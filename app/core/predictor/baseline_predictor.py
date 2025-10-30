"""
Baseline Predictor
간단한 통계 기반 예측 + 폴백(fallback) 역할
"""

from datetime import datetime, timedelta
import numpy as np

from app.models.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor
from .data_sources import get_data_source
from app.core.errors import DataNotFoundError


class BaselinePredictor(BasePredictor):
    """
    통계 기반 간단 예측기
    - LSTM 대비 성능 비교용
    - 데이터 없거나 에러 시 폴백용
    """
    
    def __init__(self):
        """데이터 소스 초기화"""
        try:
            self.data_source = get_data_source()
            print("✅ Baseline Predictor initialized")
        except Exception as e:
            print(f"⚠️ Data source unavailable: {e}")
            self.data_source = None
    
    def run(
        self,
        *,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str
    ) -> PredictionResult:
        """간단한 통계 기반 예측"""
        
        # 1. 데이터 조회 시도
        try:
            if self.data_source is not None:
                recent_data = self.data_source.fetch_historical_data(
                    service_id=service_id,
                    metric_name=metric_name,
                    hours=24
                )
                return self._statistical_prediction(
                    service_id, metric_name, ctx, model_version, recent_data
                )
        except (DataNotFoundError, Exception) as e:
            print(f"⚠️ Data fetch failed: {e}, using fallback")
        
        # 2. 데이터 없으면 더미 예측
        return self._fallback_prediction(service_id, metric_name, ctx, model_version)
    
    def _statistical_prediction(
        self,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
        recent_data: np.ndarray
    ) -> PredictionResult:
        """실제 데이터 기반 통계 예측"""
        
        # 통계 계산
        avg = float(recent_data.mean())
        std = float(recent_data.std())
        last_value = float(recent_data[-1])
        trend = float(recent_data[-1] - recent_data[0]) / len(recent_data)
        
        print(f"📊 Stats: avg={avg:.2f}, std={std:.2f}, trend={trend:.2f}")
        
        # Context에 따라 기울기 조정
        if ctx.time_slot == "peak":
            slope_factor = 1.2
        elif ctx.time_slot == "low":
            slope_factor = 0.8
        else:
            slope_factor = 1.0
        
        # 예측 생성
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        preds = []
        
        for k in range(1, 25):
            value = last_value + (trend * k * slope_factor)
            noise = np.random.normal(0, std * 0.05)
            value = max(0, value + noise)
            
            if metric_name == "total_events":
                value = round(value)
            
            preds.append(
                PredictionPoint(
                    time=now + timedelta(hours=k),
                    value=float(value)
                )
            )
        
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=f"{model_version}_statistical",
            generated_at=datetime.utcnow(),
            predictions=preds
        )
    
    def _fallback_prediction(
        self,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str
    ) -> PredictionResult:
        """데이터 없을 때 더미 예측"""
        
        print("⚠️ Using fallback prediction (no data)")
        
        # metric별 기본값
        if metric_name == "total_events":
            base = 50.0
            slope = 0.5
        elif metric_name in ("avg_cpu", "avg_memory"):
            base = 0.3
            slope = 0.01
        else:
            base = 10.0
            slope = 0.1
        
        # Context에 따라 기울기 조정
        if ctx.time_slot == "peak":
            slope *= 2
        elif ctx.time_slot == "low":
            slope *= 0.5
        
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        preds = []
        
        for k in range(1, 25):
            value = base + slope * k
            
            if metric_name == "total_events":
                value = round(value)
            
            preds.append(
                PredictionPoint(
                    time=now + timedelta(hours=k),
                    value=float(value)
                )
            )
        
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=f"{model_version}_fallback",
            generated_at=datetime.utcnow(),
            predictions=preds
        )