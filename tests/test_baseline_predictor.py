# tests/test_baseline_predictor.py

"""
baseline_predictor 모듈 단위 테스트.
"""

import pytest
from datetime import datetime, timedelta
from typing import cast
from unittest.mock import Mock, patch

from app.core.predictor.baseline_predictor import BaselinePredictor
from app.models.common import MCPContext, PredictionResult, PredictionPoint, ServiceType, RuntimeEnv, TimeSlot
from app.core.errors import DataNotFoundError


@pytest.fixture
def sample_context():
    """테스트용 MCPContext 생성."""
    return MCPContext(
        context_id="test-context-1",
        timestamp=datetime.utcnow(),
        service_type="web",
        runtime_env="prod",
        time_slot="normal",
        weight=1.0,
    )


@pytest.fixture
def baseline_predictor():
    """BaselinePredictor 인스턴스 생성."""
    return BaselinePredictor()


def test_baseline_predictor_init():
    """BaselinePredictor 초기화 테스트."""
    predictor = BaselinePredictor()
    
    assert predictor is not None
    # data_source는 None일 수 있음 (CSV 파일이 없을 경우)


@patch('app.core.predictor.baseline_predictor.get_data_source')
def test_baseline_predictor_run_with_data(mock_get_data_source, sample_context):
    """데이터 소스에서 데이터를 가져올 수 있는 경우."""
    # Mock 데이터 소스 설정
    mock_data_source = Mock()
    mock_data = [0.1, 0.2, 0.3, 0.4, 0.5] * 5  # 25개 값 (24시간보다 많음)
    mock_data_source.fetch_historical_data.return_value = mock_data
    
    mock_get_data_source.return_value = mock_data_source
    
    predictor = BaselinePredictor()
    predictor.data_source = mock_data_source
    
    result = predictor.run(
        service_id="test-service",
        metric_name="total_events",
        ctx=sample_context,
        model_version="baseline_v1",
    )
    
    assert isinstance(result, PredictionResult)
    assert result.service_id == "test-service"
    assert result.metric_name == "total_events"
    assert result.model_version == "baseline_v1"
    assert len(result.predictions) == 24  # 24시간 예측
    assert all(isinstance(p, PredictionPoint) for p in result.predictions)
    assert all(p.value >= 0 for p in result.predictions)  # 값은 0 이상


@patch('app.core.predictor.baseline_predictor.get_data_source')
def test_baseline_predictor_run_fallback(mock_get_data_source, sample_context):
    """데이터 소스에서 데이터를 가져올 수 없는 경우 폴백 사용."""
    # Mock 데이터 소스가 DataNotFoundError 발생
    mock_data_source = Mock()
    mock_data_source.fetch_historical_data.side_effect = DataNotFoundError("No data found")
    
    mock_get_data_source.return_value = mock_data_source
    
    predictor = BaselinePredictor()
    predictor.data_source = mock_data_source
    
    result = predictor.run(
        service_id="test-service",
        metric_name="total_events",
        ctx=sample_context,
        model_version="baseline_v1",
    )
    
    # 폴백 예측이 반환되어야 함
    assert isinstance(result, PredictionResult)
    assert len(result.predictions) == 24
    # 폴백 예측은 모든 값이 0.5 (기본값)
    assert all(p.value == 0.5 for p in result.predictions)


def test_baseline_predictor_run_no_data_source(sample_context):
    """데이터 소스가 None인 경우 폴백 사용."""
    predictor = BaselinePredictor()
    predictor.data_source = None
    
    result = predictor.run(
        service_id="test-service",
        metric_name="total_events",
        ctx=sample_context,
        model_version="baseline_v1",
    )
    
    # 폴백 예측이 반환되어야 함
    assert isinstance(result, PredictionResult)
    assert len(result.predictions) == 24
    assert all(p.value == 0.5 for p in result.predictions)


@patch('app.core.predictor.baseline_predictor.get_data_source')
def test_baseline_predictor_run_with_different_contexts(mock_get_data_source):
    """다양한 context로 예측이 정상 작동하는지 확인."""
    mock_data_source = Mock()
    mock_data = [0.1] * 24
    mock_data_source.fetch_historical_data.return_value = mock_data
    mock_get_data_source.return_value = mock_data_source
    
    predictor = BaselinePredictor()
    predictor.data_source = mock_data_source
    
    contexts = [
        MCPContext(
            context_id=f"test-{i}",
            timestamp=datetime.utcnow(),
            service_type=cast(ServiceType, st),
            runtime_env=cast(RuntimeEnv, re),
            time_slot=cast(TimeSlot, ts),
            weight=1.0,
        )
        for i, (st, re, ts) in enumerate([
            ("web", "prod", "peak"),
            ("api", "dev", "normal"),
            ("db", "prod", "low"),
        ])
    ]
    
    for ctx in contexts:
        result = predictor.run(
            service_id="test-service",
            metric_name="total_events",
            ctx=ctx,
            model_version="baseline_v1",
        )
        
        assert isinstance(result, PredictionResult)
        assert len(result.predictions) == 24


def test_baseline_predictor_predictions_time_sequence(sample_context):
    """예측 결과의 시간 순서가 올바른지 확인."""
    predictor = BaselinePredictor()
    predictor.data_source = None  # 폴백 사용
    
    result = predictor.run(
        service_id="test-service",
        metric_name="total_events",
        ctx=sample_context,
        model_version="baseline_v1",
    )
    
    # 시간이 순차적으로 증가하는지 확인
    times = [p.time for p in result.predictions]
    for i in range(len(times) - 1):
        assert times[i] < times[i + 1]
        # 각 예측은 1시간 간격
        assert (times[i + 1] - times[i]) == timedelta(hours=1)

