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
    if "lstm" in model_version:
        return get_predictor("lstm")
    return get_predictor("baseline")


@router.post("", response_model=PlansResponse)
def make_plan(req: PlansRequest):
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