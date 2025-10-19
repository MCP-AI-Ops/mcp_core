from fastapi import APIRouter
from datetime import datetime

from app.models.plans import PlansRequest, PlansResponse
from app.core.context_extractor import extract_context
from app.core.router import select_route
from app.core.predictor import BaselinePredictor, LSTMPredictor
from app.core.policy import postprocess_predictions

router = APIRouter()

# 간단한 레지스트리
_PREDICTORS = {
    "baseline": BaselinePredictor(),
    "lstm": LSTMPredictor(),
}

def pick_engine(model_version: str):
    # 규칙: 이름에 "lstm" 있으면 lstm 예측기, 아니면 baseline
    if "lstm" in model_version:
        return _PREDICTORS["lstm"]
    return _PREDICTORS["baseline"]

@router.post("", response_model=PlansResponse)
def make_plan(req: PlansRequest):
    ctx = extract_context(req.context.model_dump())
    model_version, path = select_route(ctx)

    predictor = pick_engine(model_version)
    raw_pred = predictor.run(service_id=req.service_id, metric_name=req.metric_name, ctx=ctx, model_version=model_version)
    final_pred = postprocess_predictions(raw_pred, ctx)

    # (더미)
    max_val = max(p.value for p in final_pred.predictions)
    recommended_flavor = "small"
    if max_val > 0.7: recommended_flavor = "medium"
    if max_val > 0.9: recommended_flavor = "large"
    expected_cost_per_day = {"small": 1.2, "medium": 2.8, "large": 5.5}[recommended_flavor]

    return PlansResponse(
        prediction=final_pred,
        recommended_flavor=recommended_flavor,
        expected_cost_per_day=expected_cost_per_day,
        generated_at=datetime.utcnow(),
        notes="(더미) cost/flavor 룰 기반 산정"
    )