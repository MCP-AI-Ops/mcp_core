"""
Google Cluster 데이터의 극값과 long-tail 분포 특성을 고려한 이상 탐지.
노트북의 EnhancedLSTMPredictor 알고리즘 기반.
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
    z_thresh: float = 5.0,
) -> Dict[str, Any]:
    """
    노트북의 robust 알고리즘 기반 이상 탐지:
    1. Percentile 기반 이상치 제거 (5%-95%)
    2. 동적 임계값 (mean + threshold_multiplier * std)
    3. 다차원 특성 고려 (현재값, 6시간 평균, 변화율, 표준편차)
    """
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

    # === 1. Robust 통계 계산 (노트북 방식) ===
    # Percentile 기반 이상치 제거: 상하위 5% 제거
    p5, p95 = np.percentile(hist, [5, 95])
    hist_clean = hist[(hist >= p5) & (hist <= p95)]
    
    if len(hist_clean) < 10:  # 최소 데이터 보장
        hist_clean = hist
    
    # IQR 기반 추가 필터링 (노트북의 _handle_outliers 방식)
    Q1 = np.percentile(hist_clean, 25)
    Q3 = np.percentile(hist_clean, 75)
    IQR = Q3 - Q1
    
    if IQR > 0:
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        hist_robust = hist_clean[(hist_clean >= lower_bound) & (hist_clean <= upper_bound)]
        
        if len(hist_robust) >= 10:
            hist_clean = hist_robust

    meta = get_metric_meta(pred.metric_name)
    if meta.kind == "ratio":
        hi = meta.clamp_max if meta.clamp_max is not None else 1.0
        hist_clean = np.clip(hist_clean, meta.clamp_min, hi)
    else:
        hist_clean = np.maximum(hist_clean, meta.clamp_min)

    # Robust 통계 (median 기반)
    hist_median = float(np.median(hist_clean))
    hist_mean = float(np.mean(hist_clean))
    hist_std = float(np.std(hist_clean))
    
    # === 2. 예측값 처리 ===
    pred_values = np.array([p.value for p in pred.predictions])
    max_pred = float(np.max(pred_values))
    avg_pred = float(np.mean(pred_values))
    
    if meta.kind == "ratio":
        max_pred = meta.clamp(max_pred)
        avg_pred = meta.clamp(avg_pred)
    else:
        max_pred = max(max_pred, meta.clamp_min)
        avg_pred = max(avg_pred, meta.clamp_min)

    # === 3. 다차원 이상 탐지 (노트북 방식) ===
    # 3.1 평균 기반 점수 (더 안정적)
    if hist_std > 0:
        score_avg = (avg_pred - hist_mean) / hist_std
    else:
        score_avg = (avg_pred / hist_median) - 1.0 if hist_median > 0 else 0.0
    
    # 3.2 최대값 기반 점수
    if hist_std > 0:
        score_max = (max_pred - hist_mean) / hist_std
    else:
        score_max = (max_pred / hist_median) - 1.0 if hist_median > 0 else 0.0
    
    # 3.3 변화율 점수 (노트북의 change_rate)
    if hist_median > 0:
        change_rate = (avg_pred - hist_median) / hist_median
    else:
        change_rate = 0.0
    
    # 3.4 종합 점수 (가중 평균)
    combined_score = (
        0.4 * score_avg +      # 평균 기반 (안정성)
        0.3 * score_max +      # 최대값 기반 (극값 감지)
        0.3 * abs(change_rate) # 변화율 (급격한 변화)
    )
    
    # === 4. 동적 임계값 (노트북의 threshold_multiplier 방식) ===
    # z_thresh를 표준편차 배수로 사용
    # 예: z_thresh=5.0 → 평균에서 5 표준편차 이상 벗어나면 이상
    # 예: z_thresh=2.0 (테스트용) → 2 표준편차 이상
    dynamic_threshold = z_thresh
    
    # === 5. 이상 판정 ===
    # 보수적 판정: 여러 조건 중 여러 개가 동시에 만족해야 이상
    # 또는 극단적인 스파이크만 이상으로 판정
    
    # 조건 1: 종합 점수가 임계값 초과
    condition1 = combined_score >= dynamic_threshold
    
    # 조건 2: 극값 스파이크 (임계값의 1.5배 이상)
    condition2 = score_max >= (dynamic_threshold * 1.5)
    
    # 조건 3: 급격한 변화 (200% 이상 증가)
    condition3 = change_rate >= 2.0
    
    # 조건 4: 과거 데이터 대비 예측값이 지나치게 큼
    # (평균의 3배 이상 && 표준편차의 10배 이상)
    condition4 = (
        avg_pred >= (hist_mean * 3.0) and 
        hist_std > 0 and 
        (avg_pred - hist_mean) >= (hist_std * 10)
    )
    
    # 최종 판정: 극단적인 경우만 이상으로 분류
    is_anomaly = (
        (condition1 and condition2) or  # 종합 점수 + 극값 동시 초과
        condition3 or                    # 극단적 급증
        condition4                       # 과거 대비 비정상적 예측
    )

    return {
        "anomaly_detected": bool(is_anomaly),
        "score": float(combined_score),
        "score_breakdown": {
            "avg_based": float(score_avg),
            "max_based": float(score_max),
            "change_rate": float(change_rate),
        },
        "max_pred": float(max_pred),
        "avg_pred": float(avg_pred),
        "hist_mean": float(hist_mean),
        "hist_median": float(hist_median),
        "hist_std": float(hist_std),
        "threshold": float(dynamic_threshold),
        "data_points_used": len(hist_clean),
        "outliers_removed": len(hist) - len(hist_clean),
    }
