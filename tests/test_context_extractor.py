# tests/test_context_extractor.py

"""
context_extractor 모듈 단위 테스트.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.core.context_extractor import extract_context
from app.core.errors import ContextValidationError
from app.models.common import MCPContext


def test_extract_context_valid():
    """유효한 context 딕셔너리를 MCPContext로 변환."""
    raw_context = {
        "context_id": "test-1",
        "timestamp": datetime.utcnow(),
        "service_type": "web",
        "runtime_env": "prod",
        "time_slot": "normal",
        "weight": 1.0,
    }
    
    ctx = extract_context(raw_context)
    
    assert isinstance(ctx, MCPContext)
    assert ctx.context_id == "test-1"
    assert ctx.service_type == "web"
    assert ctx.runtime_env == "prod"
    assert ctx.time_slot == "normal"


def test_extract_context_with_defaults():
    """기본값이 적용되는지 확인."""
    raw_context = {
        "context_id": "test-2",
        "timestamp": datetime.utcnow(),
        "service_type": "api",
        # runtime_env, time_slot는 기본값 사용
    }
    
    ctx = extract_context(raw_context)
    
    assert ctx.runtime_env == "prod"  # 기본값
    assert ctx.time_slot == "normal"  # 기본값
    assert ctx.weight == 1.0  # 기본값


def test_extract_context_invalid_service_type():
    """잘못된 service_type은 ValidationError 발생."""
    raw_context = {
        "context_id": "test-3",
        "timestamp": datetime.utcnow(),
        "service_type": "invalid_type",  # "web", "api", "db"만 허용
        "runtime_env": "prod",
    }
    
    with pytest.raises(ContextValidationError):
        extract_context(raw_context)


def test_extract_context_missing_required_field():
    """필수 필드가 없으면 ValidationError 발생."""
    raw_context = {
        "context_id": "test-4",
        # timestamp, service_type 누락
    }
    
    with pytest.raises(ContextValidationError):
        extract_context(raw_context)


def test_extract_context_invalid_time_slot():
    """잘못된 time_slot은 ValidationError 발생."""
    raw_context = {
        "context_id": "test-5",
        "timestamp": datetime.utcnow(),
        "service_type": "web",
        "time_slot": "invalid_slot",  # "peak", "normal", "low", "weekend"만 허용
    }
    
    with pytest.raises(ContextValidationError):
        extract_context(raw_context)


def test_extract_context_invalid_weight():
    """음수 weight는 ValidationError 발생."""
    raw_context = {
        "context_id": "test-6",
        "timestamp": datetime.utcnow(),
        "service_type": "web",
        "weight": -1.0,  # 음수는 허용되지 않음
    }
    
    with pytest.raises(ContextValidationError):
        extract_context(raw_context)


def test_extract_context_with_optional_fields():
    """선택적 필드가 포함된 경우 정상 처리."""
    raw_context = {
        "context_id": "test-7",
        "timestamp": datetime.utcnow(),
        "service_type": "web",
        "region": "us-east-1",
        "expected_users": 1000,
        "curr_cpu": 0.5,
        "curr_mem": 0.7,
    }
    
    ctx = extract_context(raw_context)
    
    assert ctx.region == "us-east-1"
    assert ctx.expected_users == 1000
    assert ctx.curr_cpu == 0.5
    assert ctx.curr_mem == 0.7

