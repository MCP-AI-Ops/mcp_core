# app/routes/plans.py

"""
/plans 라우트.

역할:
- 클라이언트가 특정 서비스(service_id)에 대해 특정 metric(metric_name)의
  향후 리소스 사용량 예측을 요청하면,
  1) context 파싱/검증
  2) router 기반 모델 버전 선택
  3) predictor 실행 (LSTM 또는 Baseline)
  4) policy 후처리(가중치/클램프)
  5) 추천 인스턴스 스펙 및 비용 산출
  까지 한 번에 수행하고 응답한다.

이 엔드포인트의 응답은 프론트엔드와 CI/CD 파이프라인(배포 결정)에서 그대로 소비된다.
즉, 여기서 리턴하는 JSON 스키마가 사실상 이 프로젝트의 "계약(Contract)"이다.
"""

from fastapi import APIRouter
from datetime import datetime
import logging

from app.models.plans import PlansRequest, PlansResponse
from app.core.context_extractor import extract_context
from app.core.router import select_route
from app.core.predictor import BaselinePredictor, LSTMPredictor
from app.core.policy import postprocess_predictions
from app.core.errors import PredictionError

from app.core.predictor.baseline_predictor import BaselinePredictor
from app.core.predictor.lstm_predictor import LSTMPredictor

router = APIRouter()

# 지연 생성용 레지스트리: 앱 시작 시 무거운 모델/IO를 실행하지 않기 위함
_PREDICTORS: dict[str, object] = {}


def get_predictor(kind: str):
    """첫 사용 시 인스턴스 생성 (lazy init)."""
    if kind not in _PREDICTORS:
        if kind == "lstm":
            _PREDICTORS[kind] = LSTMPredictor()
        else:
            _PREDICTORS[kind] = BaselinePredictor()
    return _PREDICTORS[kind]


def pick_engine(model_version: str):
    # 규칙: 이름에 "lstm" 있으면 lstm 예측기, 아니면 baseline
    """
    model_version 문자열에 'lstm'이 포함된 경우 LSTMPredictor,
    그 외에는 BaselinePredictor를 반환한다.
    """
    
    if "lstm" in model_version:
        return get_predictor("lstm")
    return get_predictor("baseline")


@router.post("", response_model=PlansResponse)
def make_plan(req: PlansRequest):
    """
    핵심 예측 플로우:

    1) context 추출/검증
    2) router로 모델 버전 결정
    3) predictor.run()으로 원시 예측 생성
    4) policy.postprocess_predictions()로 안정화
    5) 최대 usage 기반으로 flavor(small/medium/large) 추천 및 예상 비용 산출

    Notes
    -----
    - 이후 LSTM predictor가 실제 모델로 치환되면 이 엔드포인트는 그대로 유지된다.
      즉, /plans의 요청/응답 스펙은 프런트와 배포 파이프라인이 의존하는 계약(Contract)이므로
      함부로 깨면 안 된다.
    """
    
    ctx = extract_context(req.context.model_dump())
    model_version, path = select_route(ctx)

    predictor = pick_engine(model_version)

    try:
        raw_pred = predictor.run(service_id=req.service_id, metric_name=req.metric_name, ctx=ctx, model_version=model_version)
    except PredictionError as e:
        # LSTM 등 예측 실패 시 안전하게 baseline으로 폴백
        logging.exception("Predictor failed, falling back to baseline: %s", e)
        fallback = get_predictor("baseline")
        raw_pred = fallback.run(service_id=req.service_id, metric_name=req.metric_name, ctx=ctx, model_version=model_version)

    final_pred = postprocess_predictions(raw_pred, ctx)

    # (더미) cost 룰
    max_val = max((p.value for p in final_pred.predictions), default=0)
    recommended_flavor = "small"
    if max_val > 0.7:
        recommended_flavor = "medium"
    if max_val > 0.9:
        recommended_flavor = "large"
    expected_cost_per_day = {"small": 1.2, "medium": 2.8, "large": 5.5}[recommended_flavor]

    return PlansResponse(
        prediction=final_pred,
        recommended_flavor=recommended_flavor,
        expected_cost_per_day=expected_cost_per_day,
        generated_at=datetime.utcnow(),
        notes="(더미) cost/flavor 룰 기반 산정",
    )   