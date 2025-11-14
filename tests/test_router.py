# tests/test_router.py

"""
router 모듈 단위 테스트.
"""

import pytest
from datetime import datetime
from typing import cast

from app.core.router import select_route
from app.models.common import MCPContext, ServiceType, RuntimeEnv, TimeSlot


def test_select_route_prod_peak_web():
    """prod + peak + web 조합 테스트."""
    ctx = MCPContext(
        context_id="test-1",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="prod",
        time_slot="peak",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "web_peak_v1"
    assert path == "forecast_24h"


def test_select_route_prod_normal_web():
    """prod + normal + web 조합 테스트."""
    ctx = MCPContext(
        context_id="test-2",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="prod",
        time_slot="normal",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "web_normal_v1"
    assert path == "forecast_24h"


def test_select_route_dev_peak_web():
    """dev + peak + web 조합 테스트."""
    ctx = MCPContext(
        context_id="test-3",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="dev",
        time_slot="peak",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "web_dev_peak_v1"
    assert path == "forecast_24h"


def test_select_route_default_fallback():
    """매핑되지 않은 조합은 기본값 사용."""
    ctx = MCPContext(
        context_id="test-4",
        timestamp=datetime.utcnow(),
        service_type="api",  # 매핑에 없는 service_type
        runtime_env="prod",
        time_slot="normal",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "default_fallback_v1"
    assert path == "forecast_24h"


def test_select_route_weekend():
    """weekend time_slot 테스트."""
    ctx = MCPContext(
        context_id="test-5",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="prod",
        time_slot="weekend",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "web_weekend_v1"
    assert path == "forecast_24h"


def test_select_route_low():
    """low time_slot 테스트."""
    ctx = MCPContext(
        context_id="test-6",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="prod",
        time_slot="low",
        weight=1.0,
    )
    
    model_version, path = select_route(ctx)
    
    assert model_version == "web_low_v1"
    assert path == "forecast_24h"


def test_select_route_all_combinations():
    """모든 정의된 조합이 올바르게 매핑되는지 확인."""
    test_cases = [
        (("prod", "peak", "web"), "web_peak_v1"),
        (("prod", "normal", "web"), "web_normal_v1"),
        (("prod", "low", "web"), "web_low_v1"),
        (("prod", "weekend", "web"), "web_weekend_v1"),
        (("dev", "peak", "web"), "web_dev_peak_v1"),
        (("dev", "normal", "web"), "web_dev_normal_v1"),
        (("dev", "low", "web"), "web_dev_low_v1"),
        (("dev", "weekend", "web"), "web_dev_weekend_v1"),
    ]
    
    for (runtime_env, time_slot, service_type), expected_model in test_cases:
        ctx = MCPContext(
            context_id=f"test-{runtime_env}-{time_slot}-{service_type}",
            timestamp=datetime.utcnow(),
            service_type=cast(ServiceType, service_type),
            runtime_env=cast(RuntimeEnv, runtime_env),
            time_slot=cast(TimeSlot, time_slot),
            weight=1.0,
        )
        
        model_version, path = select_route(ctx)
        
        assert model_version == expected_model, f"Failed for {runtime_env}/{time_slot}/{service_type}"
        assert path == "forecast_24h"

