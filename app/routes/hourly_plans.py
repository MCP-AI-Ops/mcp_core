from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.errors import PredictionError
from app.core.hourly_flavor_mapper import map_predictions_to_flavors
from app.core.policy import postprocess_predictions
from app.core.predictor.base import BasePredictor
from app.core.predictor.baseline_predictor import BaselinePredictor
from app.core.predictor.lstm_predictor import LSTMPredictor
from app.models.hourly_plans import HourlyPlansRequest, HourlyPlansResponse

router = APIRouter(prefix="/hourly-flavor", tags=["hourly-flavor"])

_PREDICTOR_CACHE: dict[str, BasePredictor] = {}


def _get_predictor(kind: str) -> BasePredictor:
    if kind not in _PREDICTOR_CACHE:
        if kind == "baseline":
            _PREDICTOR_CACHE[kind] = BaselinePredictor()
        else:
            _PREDICTOR_CACHE[kind] = LSTMPredictor()
    return _PREDICTOR_CACHE[kind]


@router.post("", response_model=HourlyPlansResponse)
async def recommend_hourly_flavor(req: HourlyPlansRequest) -> HourlyPlansResponse:
    """
    모델의 시간별 예측을 그대로 사용해 24개의 시간별 플레이버를 추천한다.

    기존 /plans 흐름과 독립적으로 동작하며, 필요한 경우 FastAPI에 따로 연결해 사용한다.
    """
    model_version = req.model_version or os.getenv("MODEL_VERSION", "lstm_v1")

    try:
        predictor = _get_predictor("lstm")
        raw_pred = predictor.run(
            github_url=req.github_url,
            metric_name=req.metric_name,
            ctx=req.context,
            model_version=model_version,
        )
    except PredictionError as exc:
        logging.exception("LSTM hourly prediction failed: %s", exc)
        if not req.fallback_to_baseline:
            raise HTTPException(status_code=500, detail="Hourly prediction failed") from exc

        fallback = _get_predictor("baseline")
        raw_pred = fallback.run(
            github_url=req.github_url,
            metric_name=req.metric_name,
            ctx=req.context,
            model_version=f"{model_version}_baseline",
        )

    final_pred = postprocess_predictions(raw_pred, req.context)

    try:
        recommendations, breakpoints, total_cost = map_predictions_to_flavors(
            final_pred.predictions
        )
    except Exception as exc:
        logging.exception("Hourly flavor mapping failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return HourlyPlansResponse(
        github_url=req.github_url,
        metric_name=req.metric_name,
        model_version=final_pred.model_version,
        generated_at=datetime.utcnow(),
        hourly_recommendations=recommendations,
        breakpoints=breakpoints,
        total_expected_cost_24h=round(total_cost, 3),
        notes="24 hourly flavors derived directly from model outputs.",
    )
