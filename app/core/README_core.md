# MCP Core (Orchestrator)

## 목적
MCP Core는 서비스별 자원 사용량(CPU, Memory 등)을 예측하고,
그 결과를 기반으로 배포/스케일링 의사결정에 사용할 정보를 API 형태로 제공하는 FastAPI 기반 오케스트레이터입니다.

요청 -> 컨텍스트 파싱 -> 모델 라우팅 -> 예측 -> 정책 후처리 -> 추천/코스트 계산
까지의 전체 파이프라인을 담당합니다.

---

## 전체 흐름 (요약)

1. 클라이언트가 `/plans`에 예측 요청을 보낸다.
2. 요청 안의 `context` JSON을 `context_extractor`가 `MCPContext`로 변환하고 검증한다.
3. `router`는 이 컨텍스트를 보고 어떤 모델 버전(예: "web_peak_lstm_v1")을 쓸지 결정한다.
4. 선택된 모델 버전에 따라 `BaselinePredictor` 또는 `LSTMPredictor`를 사용해 예측 시계열을 생성한다.
5. `policy`가 예측값에 weight, clamp 등을 적용해 안전한 값으로 후처리한다.
6. `/plans`는 최종 예측, 추천 flavor(small/medium/large), 예상 비용을 응답한다.

`/plans` 응답 스키마는 프론트엔드와 배포 파이프라인(CI/CD)이 그대로 의존하므로 "계약(Contract)"으로 취급하며 함부로 바꾸면 안 됩니다.

---

## 디렉토리 구조 (핵심만)

```text
app/
  core/
    context_extractor.py   # 요청 context -> MCPContext 변환/검증
    router.py              # 컨텍스트 기반 모델 버전 선택
    policy.py              # 예측값 후처리 (가중치, 클램핑)
    predictor/
      base.py              # Predictor 공통 인터페이스(run)
      baseline_predictor.py# 단순 통계/휴리스틱 기반 mock predictor
      lstm_predictor.py    # LSTM predictor stub (실제 모델 붙일 자리)
  routes/
    plans.py               # /plans 엔드포인트 (전체 파이프라인 조립)
    deploy.py              # (stub) 배포 요청
    status.py              # (stub) 상태 조회
    destroy.py             # (stub) 자원 정리
  models/
    ...                    # Pydantic 요청/응답 스키마
  config/
    settings.py            # ENV, 경로, DB 정보 등
```

```
POST /plans
{
  "service_id": "svc-1",
  "metric_name": "cpu_usage",
  "context": {
    "context_id": "ctx-1",
    "timestamp": "2025-10-19T12:00:00Z",
    "service_type": "web",
    "runtime_env": "prod",
    "time_slot": "peak",
    "weight": 1.0
  }
}
```

```
{
  "prediction": {
    "service_id": "svc-1",
    "metric_name": "cpu_usage",
    "model_version": "web_peak_lstm_v1",
    "generated_at": "2025-10-19T12:00:05Z",
    "predictions": [
      { "time": "2025-10-19T13:00:00Z", "value": 0.54 },
      { "time": "2025-10-19T14:00:00Z", "value": 0.56 }
      // ... up to +24h
    ]
  },
  "recommended_flavor": "medium",
  "expected_cost_per_day": 2.8,
  "generated_at": "2025-10-19T12:00:05Z",
  "notes": "(mock) cost/flavor rule 기반 산정"
}
```