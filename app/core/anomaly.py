"""
간단한 통계 기반 이상 탐지 모듈.
최근 예측 결과와 과거 데이터를 비교해 z-score를 계산한다.
"""

from __future__ import annotations

import math
from typing import Dict, Any

import numpy as np

from app.models.common import PredictionResult, MCPContext
from app.core.predictor.data_sources.factory import get_data_source
from app.core.errors import DataSourceError
from app.core.metrics import get_metric_meta


def detect_anomaly(
    pred: PredictionResult,
    ctx: MCPContext,
    hours: int = 168,
    z_thresh: float = 3.0,
) -> Dict[str, Any]:
    """과거 평균·표준편차 대비 이상 여부를 판단한다."""
    try:
        ds = get_data_source()
    except Exception as exc:
        raise DataSourceError(f"데이터 소스를 사용할 수 없음: {exc}")

    try:
        hist = ds.fetch_historical_data(
            github_url=pred.github_url,
            metric_name=pred.metric_name,
            hours=hours,
        )
    except Exception as exc:
        return {
            "anomaly_detected": False,
            "score": 0.0,
            "reason": f"과거 데이터 조회 실패: {exc}",
        }

    if len(hist) == 0:
        return {"anomaly_detected": False, "score": 0.0, "reason": "과거 데이터 없음"}

    meta = get_metric_meta(pred.metric_name)
    if meta.kind == "ratio":
        hi = meta.clamp_max if meta.clamp_max is not None else 1.0
        hist = np.clip(hist, meta.clamp_min, hi)
    else:
        hist = np.maximum(hist, meta.clamp_min)

    hist_mean = float(np.mean(hist))
    hist_std = float(np.std(hist))
    max_pred = float(max((p.value for p in pred.predictions), default=0.0))
    if meta.kind == "ratio":
        max_pred = meta.clamp(max_pred)
    elif max_pred < meta.clamp_min:
        max_pred = meta.clamp_min

    if math.isclose(hist_std, 0.0):
        score = (max_pred / hist_mean) if hist_mean > 0 else float("inf")
    else:
        score = (max_pred - hist_mean) / hist_std

    if hist_std > 0:
        anomaly = score >= z_thresh
    else:
        anomaly = score >= 2.0 if hist_mean > 0 else False

    return {
        "anomaly_detected": bool(anomaly),
        "score": float(score),
        "max_pred": max_pred,
        "hist_mean": hist_mean,
        "hist_std": hist_std,
        "threshold": z_thresh,
    }
