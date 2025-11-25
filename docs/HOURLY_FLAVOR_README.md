# Hourly Flavor (Per-Hour LSTM Output)

This module produces **24 hourly flavor recommendations** directly from the model's per-hour predictions. It is independent of the existing `/plans` flow and does not change its behavior.

## 파일
- `app/models/hourly_plans.py` — 시간별 플레이버 요청/응답 모델
- `app/core/hourly_flavor_mapper.py` — 데이터 기반 플레이버 매핑 및 비용 계산
- `app/routes/hourly_plans.py` — FastAPI 라우터(프리픽스 `/hourly-flavor`), 기본 미등록
- `tests/test_hourly_flavor.py` — 매퍼 로직 단위 테스트

## 매핑 방식 (고정 임계값)
1) 예측기(LSTM 기본, 필요 시 베이스라인 대체)를 실행해 24시간 예측을 얻는다.  
2) 24개 값으로 퍼센타일(p25/p50/p75), 평균, 표준편차를 계산해 참고용으로 반환한다.  
3) 각 시간대별 플레이버는 **고정 임계값**으로 결정:
   - 값 ≤ `HOURLY_FLAVOR_SMALL_MAX` (기본 300) → `small`
   - 값 ≤ `HOURLY_FLAVOR_MEDIUM_MAX` (기본 900) → `medium`
   - 그 이상 → `large`
4) 시간당 비용(USD): `small` 0.05, `medium` 0.117, `large` 0.229. 24시간 비용은 시간당 비용의 합.

> 기본 임계값(300/900)은 OpenStack m1.small/medium/large 자원 비율을 참고해 설정했으며, 환경변수로 조정 가능합니다.

## API (독립)
`app/main.py`에 기본으로 연결하지 않는다. 필요하면 수동으로 추가:
```python
from app.routes import hourly_plans
app.include_router(hourly_plans.router)
```

**엔드포인트**
- `POST /hourly-flavor`

**요청 본문**
```json
{
  "github_url": "https://github.com/example/repo",
  "metric_name": "total_events",
  "context": {
    "context_id": "ctx-123",
    "timestamp": "2025-11-25T00:00:00Z",
    "service_type": "web",
    "runtime_env": "dev",
    "time_slot": "normal",
    "weight": 1.0,
    "expected_users": 800
  },
  "model_version": "lstm_v1",
  "fallback_to_baseline": true
}
```

**응답 형태 (예시)**
```json
{
  "github_url": "...",
  "metric_name": "total_events",
  "model_version": "lstm_v1",
  "generated_at": "2025-11-25T07:00:00Z",
  "breakpoints": { "p25": 92.4, "p50": 118.9, "p75": 161.2, "mean": 130.1, "stdev": 28.7 },
  "hourly_recommendations": [
    {
      "hour_index": 0,
      "timestamp": "2025-11-25T08:00:00Z",
      "predicted_value": 95.1,
      "percentile": 0.29,
      "recommended_flavor": "small",
      "hourly_cost": 0.05
    }
    // ... 23 more entries ...
  ],
  "total_expected_cost_24h": 2.81,
  "notes": "24 hourly flavors derived directly from model outputs."
}
```

## 테스트
모델 로드 없이 매퍼 중심 테스트 실행:
```powershell
pytest tests/test_hourly_flavor.py
```
