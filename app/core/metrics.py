"""
Metric metadata helpers.

모든 메트릭을 ratio(0~1 비율) / count(절대값)로 분류해
정규화 / clamp 정책을 한 곳에서 관리한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


MetricKind = Literal["ratio", "count"]


@dataclass(frozen=True)
class MetricMeta:
    name: str
    kind: MetricKind = "count"
    clamp_min: float = 0.0
    clamp_max: float | None = None
    planning_max: float = 1.0  # flavor 추천을 위한 정규화 기준값

    def clamp(self, value: float) -> float:
        if value != value:  # NaN
            return 0.0
        if value < self.clamp_min:
            return self.clamp_min
        if self.clamp_max is not None and value > self.clamp_max:
            return self.clamp_max
        return value

    def normalize_for_planning(self, value: float) -> float:
        """
        flavor 추천을 위한 값(0~1 스케일)을 반환한다.
        planning_max 가 0 이하이면 clamp_max 를 사용한다.
        """
        if self.kind == "ratio":
            return self.clamp(value)  # 이미 0~1 범위
        denom = self.planning_max if self.planning_max > 0 else (self.clamp_max or 1.0)
        if denom <= 0:
            denom = 1.0
        ratio = value / denom
        if ratio < 0:
            return 0.0
        if ratio > 1.0:
            return 1.0
        return ratio


_METRICS: Dict[str, MetricMeta] = {
    "total_events": MetricMeta(name="total_events", kind="count", planning_max=1000.0),
    "avg_cpu":      MetricMeta(name="avg_cpu", kind="ratio", clamp_max=1.0, planning_max=1.0),
    "avg_memory":   MetricMeta(name="avg_memory", kind="ratio", clamp_max=1.0, planning_max=1.0),
    "cpu_utilization":    MetricMeta(name="cpu_utilization", kind="ratio", clamp_max=1.0, planning_max=1.0),
    "memory_utilization": MetricMeta(name="memory_utilization", kind="ratio", clamp_max=1.0, planning_max=1.0),
}

_DEFAULT_METRIC = MetricMeta(name="default", kind="count", planning_max=100.0)


def get_metric_meta(metric_name: str) -> MetricMeta:
    """
    메트릭 이름에 해당하는 메타데이터를 반환한다.
    등록되지 않은 메트릭은 기본 정책(count)으로 처리한다.
    """
    return _METRICS.get(metric_name, _DEFAULT_METRIC)
