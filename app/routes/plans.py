"""
/plans 라우트.

역할:
- 클라이언트가 특정 서비스(github_url)에 대해 특정 metric(metric_name)의
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

from calendar import week
from fastapi import APIRouter
from datetime import datetime
import logging

from app.models.plans import PlansRequest, PlansResponse, MultiPlansRequest, MultiPlansResponse
from app.core.context_extractor import extract_context
from app.core.router import select_route
from app.core.predictor import BaselinePredictor, LSTMPredictor
from app.core.predictor.base import BasePredictor
from app.core.policy import postprocess_predictions
from app.core.errors import PredictionError

from app.core.predictor.baseline_predictor import BaselinePredictor
from app.core.predictor.lstm_predictor import LSTMPredictor
from app.core.anomaly import detect_anomaly
from app.core.alerts.discord_alert import send_discord_dev_alert
from app.core.alerts.dedupe import should_send, mark_sent
import os

router = APIRouter()

# 지연 생성용 레지스트리: 앱 시작 시 무거운 모델/IO를 실행하지 않기 위함
_PREDICTORS: dict[str, BasePredictor] = {}


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
        raw_pred = predictor.run(github_url=req.github_url, metric_name=req.metric_name, ctx=ctx, model_version=model_version)
    except PredictionError as e:
        # LSTM 등 예측 실패 시 안전하게 baseline으로 폴백
        logging.exception("Predictor failed, falling back to baseline: %s", e)
        fallback = get_predictor("baseline")
        raw_pred = fallback.run(github_url=req.github_url, metric_name=req.metric_name, ctx=ctx, model_version=model_version)

    final_pred = postprocess_predictions(raw_pred, ctx)

    # Flavor 추천 로직: 사용자 수와 시간대 기반
    expected_users = ctx.expected_users or 100
    time_slot = ctx.time_slot or "normal"
    
    # 1단계: 사용자 수 기반 기본 사이즈
    if expected_users <= 500:
        base_flavor = "small"
    elif expected_users <= 5000:
        base_flavor = "medium"
    else:
        base_flavor = "large"
    
    # 2단계: 시간대 고려
    recommended_flavor = base_flavor
    if time_slot == "peak":
        # 피크 타임에는 한 단계 업그레이드
        if base_flavor == "small":
            recommended_flavor = "medium"
        elif base_flavor == "medium":
            recommended_flavor = "large"
    elif time_slot == "low":
        # 저사용 시간대는 한 단계 다운그레이드
        if base_flavor == "large":
            recommended_flavor = "medium"
        elif base_flavor == "medium":
            recommended_flavor = "small"
    
    # 3단계: 예측값 기반 안전장치 (극단적 케이스만)
    max_val = max((p.value for p in final_pred.predictions), default=0)
    avg_val = sum(p.value for p in final_pred.predictions) / len(final_pred.predictions) if final_pred.predictions else 0
    
    # 예측값이 비정상적으로 높으면 large 강제
    if max_val > 1000 or avg_val > 500:
        recommended_flavor = "large"
    
    expected_cost_per_day = {"small": 1.2, "medium": 2.8, "large": 5.5}[recommended_flavor]

    # 이상 탐지 및 Discord 알림 (비차단)
    try:
        # Z-score 임계값: 기본 5.0 (더 높게 설정하여 false positive 감소)
        z_thresh = float(os.getenv("ANOMALY_Z_THRESH", "5.0"))
        anomaly = detect_anomaly(final_pred, ctx, z_thresh=z_thresh)
        if anomaly.get("anomaly_detected"):
            webhook = os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK")
            username = os.getenv("DISCORD_BOT_NAME", "MCP-dangerous")
            avatar_url = os.getenv("DISCORD_BOT_AVATAR")

            # 중복 방지 키(동일 저장소/지표/모델/시간대 기준)
            dedup_key = "|".join(
                [
                    str(final_pred.github_url),
                    str(final_pred.metric_name),
                    str(final_pred.model_version),
                    str(getattr(ctx, 'time_slot', 'unknown')),
                ]
            )

            # 한국어 메시지 + 중복 방지 적용
            if should_send(dedup_key):
                # 컨텍스트/통계 구성
                ctx_dict = {
                    "runtime_env": getattr(ctx, "runtime_env", None),
                    "time_slot": getattr(ctx, "time_slot", None),
                    "expected_users": getattr(ctx, "expected_users", None),
                    "service_type": getattr(ctx, "service_type", None),
                    "model_version": str(final_pred.model_version),
                }

                stats = {
                    "hist_mean": anomaly.get("hist_mean"),
                    "hist_std": anomaly.get("hist_std"),
                    "hist_median": anomaly.get("hist_median"),
                    "max_pred": anomaly.get("max_pred"),
                    "avg_pred": anomaly.get("avg_pred"),
                    "score": anomaly.get("score"),
                    "score_breakdown": anomaly.get("score_breakdown"),
                    "data_points_used": anomaly.get("data_points_used"),
                    "outliers_removed": anomaly.get("outliers_removed"),
                }

                # 권고 조치 메시지
                action_msg = (
                    f"현재 추천 스펙: {recommended_flavor}. 트래픽 급증이 지속되면 임시 스케일 업을 검토하세요."
                )

                if webhook:
                    send_discord_dev_alert(
                        webhook_url=webhook,
                    service_url=final_pred.github_url,
                    metric_name=final_pred.metric_name,
                    current_value=float(anomaly.get("score", 0.0)),
                    threshold_value=float(anomaly.get("threshold", 0.0)),
                    context=ctx_dict,
                    stats=stats,
                    action=action_msg,
                    dedup_key=dedup_key,
                    username=username,
                    avatar_url=avatar_url,
                )
                mark_sent(dedup_key)
    except Exception as _:
        # 알림 실패는 비차단. 로그만 남긴다.
        logging.exception("Discord alert failed (non-blocking)")

    return PlansResponse(
        prediction=final_pred,
        recommended_flavor=recommended_flavor,
        expected_cost_per_day=expected_cost_per_day,
        generated_at=datetime.utcnow(),
        notes="(더미) cost/flavor 룰 기반 산정",
    )   


@router.post("/multi", response_model=MultiPlansResponse)
def make_multi_plan(req: MultiPlansRequest):
    """
    여러 metric_name에 대해 24시간 예측을 한 번에 반환한다.

    기존 /plans 계약을 깨지 않기 위해 별도의 경로(/plans/multi)와
    응답 스키마(MultiPlansResponse)를 사용한다.
    각 metric의 값은 기존 PlansResponse와 동일한 형태로 담긴다.
    """
    ctx = extract_context(req.context.model_dump())
    model_version, path = select_route(ctx)
    predictor = pick_engine(model_version)

    results: dict[str, PlansResponse] = {}

    for metric in req.metric_names:
        try:
            raw_pred = predictor.run(
                github_url=req.github_url, metric_name=metric, ctx=ctx, model_version=model_version
            )
        except PredictionError as e:
            logging.exception("Predictor failed for %s, falling back to baseline: %s", metric, e)
            fallback = get_predictor("baseline")
            raw_pred = fallback.run(
                github_url=req.github_url, metric_name=metric, ctx=ctx, model_version=model_version
            )

        final_pred = postprocess_predictions(raw_pred, ctx)

        # Flavor 추천 (단일 엔드포인트와 동일 로직 복제)
        expected_users = ctx.expected_users or 100
        time_slot = ctx.time_slot or "normal"

        if expected_users <= 500:
            base_flavor = "small"
        elif expected_users <= 5000:
            base_flavor = "medium"
        else:
            base_flavor = "large"

        recommended_flavor = base_flavor
        if time_slot == "peak":
            if base_flavor == "small":
                recommended_flavor = "medium"
            elif base_flavor == "medium":
                recommended_flavor = "large"
        
        elif time_slot == "normal":
            base_flavor = recommended_flavor

        elif time_slot == "low" or time_slot == "weekend":
            if base_flavor == "large":
                recommended_flavor = "medium"
            elif base_flavor == "medium":
                recommended_flavor = "small"
        

        max_val = max((p.value for p in final_pred.predictions), default=0)
        avg_val = sum(p.value for p in final_pred.predictions) / len(final_pred.predictions) if final_pred.predictions else 0
        if max_val > 1000 or avg_val > 500:
            recommended_flavor = "large"

        expected_cost_per_day = {"small": 1.2, "medium": 2.8, "large": 5.5}[recommended_flavor]

        # 이상 탐지 및 Discord 알림 (비차단) - 멀티 호출에서 스팸 방지를 위해 그대로 두되 dedup_key에 metric 포함
        try:
            z_thresh = float(os.getenv("ANOMALY_Z_THRESH", "5.0"))
            anomaly = detect_anomaly(final_pred, ctx, z_thresh=z_thresh)
            if anomaly.get("anomaly_detected"):
                webhook = os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK")
                username = os.getenv("DISCORD_BOT_NAME", "MCP-dangerous")
                avatar_url = os.getenv("DISCORD_BOT_AVATAR")

                dedup_key = "|".join(
                    [
                        str(final_pred.github_url),
                        str(final_pred.metric_name),
                        str(final_pred.model_version),
                        str(getattr(ctx, "time_slot", "unknown")),
                    ]
                )

                if should_send(dedup_key):
                    ctx_dict = {
                        "runtime_env": getattr(ctx, "runtime_env", None),
                        "time_slot": getattr(ctx, "time_slot", None),
                        "expected_users": getattr(ctx, "expected_users", None),
                        "service_type": getattr(ctx, "service_type", None),
                        "model_version": str(final_pred.model_version),
                    }

                    stats = {
                        "hist_mean": anomaly.get("hist_mean"),
                        "hist_std": anomaly.get("hist_std"),
                        "hist_median": anomaly.get("hist_median"),
                        "max_pred": anomaly.get("max_pred"),
                        "avg_pred": anomaly.get("avg_pred"),
                        "score": anomaly.get("score"),
                        "score_breakdown": anomaly.get("score_breakdown"),
                        "data_points_used": anomaly.get("data_points_used"),
                        "outliers_removed": anomaly.get("outliers_removed"),
                    }

                    action_msg = (
                        f"현재 추천 스펙: {recommended_flavor}. 트래픽 급증이 지속되면 임시 스케일 업을 검토하세요."
                    )

                    if webhook:
                        send_discord_dev_alert(
                            webhook_url=webhook,
                            service_url=final_pred.github_url,
                            metric_name=final_pred.metric_name,
                            current_value=float(anomaly.get("score", 0.0)),
                            threshold_value=float(anomaly.get("threshold", 0.0)),
                            context=ctx_dict,
                            stats=stats,
                            action=action_msg,
                            dedup_key=dedup_key,
                            username=username,
                            avatar_url=avatar_url,
                        )
                        mark_sent(dedup_key)
        except Exception:
            logging.exception("Discord alert failed (non-blocking) [multi]")

        results[metric] = PlansResponse(
            prediction=final_pred,
            recommended_flavor=recommended_flavor,
            expected_cost_per_day=expected_cost_per_day,
            generated_at=datetime.utcnow(),
            notes="(더미) cost/flavor 룰 기반 산정",
        )

    return MultiPlansResponse(results=results, generated_at=datetime.utcnow())