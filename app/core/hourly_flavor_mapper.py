from __future__ import annotations

import os
import statistics
from datetime import datetime
from typing import Sequence

from app.models.common import PredictionPoint
from app.models.hourly_plans import (
    FlavorBreakpoints,
    FlavorType,
    HourlyFlavorRecommendation,
)

# 플레이버별 시간당 비용 (USD)
HOURLY_COST: dict[FlavorType, float] = {
    "small": 0.05,
    "medium": 0.117,
    "large": 0.229,
}

# 고정 임계값 (OpenStack m1.small/medium/large 용량 비율에 맞춰 기본 설정)
# 환경변수로 조정 가능:
#   HOURLY_FLAVOR_SMALL_MAX: small 상한 (포함)
#   HOURLY_FLAVOR_MEDIUM_MAX: medium 상한 (포함)
# 기본값: small ≤ 300, medium ≤ 900, 그 이상은 large
SMALL_MAX = float(os.getenv("HOURLY_FLAVOR_SMALL_MAX", "300"))
MEDIUM_MAX = float(os.getenv("HOURLY_FLAVOR_MEDIUM_MAX", "900"))


def _percentile(values: Sequence[float], pct: float) -> float:
    """퍼센타일 계산 (리포팅용, 단순 선형 보간)."""
    if not values:
        raise ValueError("Cannot compute percentile on empty sequence.")
    if pct < 0 or pct > 100:
        raise ValueError("Percentile must be between 0 and 100.")

    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (pct / 100.0)
    low = int(k)
    high = min(low + 1, len(sorted_values) - 1)

    if low == high:
        return float(sorted_values[int(k)])

    weight = k - low
    return float(sorted_values[low] * (1 - weight) + sorted_values[high] * weight)


def compute_breakpoints(values: Sequence[float]) -> FlavorBreakpoints:
    """분포 요약 (디버그/리포팅용)."""
    if len(values) != 24:
        raise ValueError(f"Expected 24 hourly predictions, got {len(values)}.")

    p25 = _percentile(values, 25)
    p50 = _percentile(values, 50)
    p75 = _percentile(values, 75)
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)

    return FlavorBreakpoints(p25=p25, p50=p50, p75=p75, mean=mean, stdev=stdev)


def pick_flavor_by_threshold(value: float) -> FlavorType:
    """고정 임계값 기반 플레이버 선택."""
    if value <= SMALL_MAX:
        return "small"
    if value <= MEDIUM_MAX:
        return "medium"
    return "large"


def map_predictions_to_flavors(
    predictions: Sequence[PredictionPoint],
) -> tuple[list[HourlyFlavorRecommendation], FlavorBreakpoints, float]:
    """
    24개 예측값을 고정 임계값으로 매핑해 24개 플레이버를 추천한다.

    Returns:
        recommendations: 시간별 HourlyFlavorRecommendation 24개
        breakpoints: 분포 요약(참고용)
        total_hourly_cost: 24시간 전체 비용 합계
    """
    if len(predictions) != 24:
        raise ValueError(f"Expected 24 hourly predictions, got {len(predictions)}.")

    values = [p.value for p in predictions]
    breakpoints = compute_breakpoints(values)

    recommendations: list[HourlyFlavorRecommendation] = []
    total_cost = 0.0

    for hour_idx, point in enumerate(predictions):
        flavor = pick_flavor_by_threshold(point.value)
        hourly_cost = HOURLY_COST[flavor]
        total_cost += hourly_cost

        recommendations.append(
            HourlyFlavorRecommendation(
                hour_index=hour_idx,
                timestamp=point.time if isinstance(point.time, datetime) else datetime.fromisoformat(str(point.time)),
                predicted_value=float(point.value),
                percentile=0.0,  # 단순 임계값 모드에서는 퍼센타일 미사용
                recommended_flavor=flavor,
                hourly_cost=hourly_cost,
            )
        )

    return recommendations, breakpoints, total_cost
