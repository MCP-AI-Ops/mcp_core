# MCP Core Orchestrator

GitHub 리포지토리 URL만 입력하면 자동으로 컨텍스트를 수집하고 `/plans` API를 호출해 향후 24시간의 리소스 사용량을 예측·추천하는 MCP Core 백엔드입니다.  
Frontend · CI/CD는 별도 팀이 담당하며, 이 레포는 Claude MCP와 모델/데이터 계층을 포함한 백엔드에 집중합니다.

---

## 전체 흐름
1. **Frontend** 또는 **Claude MCP**가 GitHub URL을 받아 `/api/analyze`(Backend API)를 호출합니다.  
2. Backend API는 GitHub 메타데이터를 수집하고 `MCPContext`를 조립한 뒤 MCP Core `/plans`로 전달합니다.  
3. MCP Core는 `context_extractor → router → predictor → policy → anomaly` 순으로 예측을 수행합니다.  
4. `/plans` 응답에는 24시간 예측 결과, 권장 인스턴스(flavor), 예상 비용, 이상 징후 여부가 포함됩니다.  
5. 이상 감지 시 Discord Webhook으로 알림이 전송되고, 선택적으로 MySQL에 이력(요청/예측/알림)을 기록합니다.

---

## 구성 요소 & 스택
| 영역 | 기술 | 설명 |
|------|------|------|
| Interface | **FastAPI** (`backend_api`, `app.main`) | `/api/analyze`, `/plans` 등 HTTP 엔드포인트 |
| GitHub 분석 | **PyGithub**, 커스텀 Heuristic | service_type, expected_users, cpu/memory 추정 |
| 예측기 | **TensorFlow(LSTM)**, **Baseline(Numpy)** | 24시간 시계열 예측, Baseline 자동 페일백 |
| 데이터 소스 | CSV / MySQL (SQLAlchemy + PyMySQL) | 최근 24h/168h 히스토리 조회, factory로 전환 |
| 정책 & 이상 감지 | `app/core/policy.py`, `app/core/anomaly.py` | Metric 메타데이터 기반 clamp, z-score alert |
| 알림 | Discord Webhook | `app/core/alerts/discord_alert.py` |
| 배포 | Docker Compose (app/backend/mysql) | `docker-compose.yml` |

주요 디렉터리 구조:
```
app/
  core/        # context, router, policy, predictor, anomaly, alerts
  routes/      # /plans FastAPI 라우터
  models/      # Pydantic 스키마
backend_api/   # GitHub 분석 + MCP Core 프락시 (Claude/Frontend 연동)
docs/          # 아키텍처/배포/API 문서
models/        # 학습된 LSTM 아티팩트(.h5/.pkl) - Git 미포함
```

---

## `/plans` 계약 요약
```json
{
  "github_url": "github-owner/repo",
  "metric_name": "total_events",
  "context": {
    "github_url": "...",
    "timestamp": "...",
    "service_type": "web|api|db",
    "runtime_env": "prod|dev",
    "time_slot": "peak|normal|low|weekend",
    "weight": 1.0,
    "expected_users": 1200,
    "curr_cpu": 4,
    "curr_mem": 8192
  }
}
```
- `context_extractor`는 필수 필드를 검증하고 기본값을 보강합니다.
- `router`는 `runtime_env/time_slot/service_type` 조합으로 모델 버전을 선택하며, prod/peak web 트래픽은 LSTM으로 라우팅됩니다.
- `policy`는 `app/core/metrics.py`의 메타데이터를 사용해 ratio/count 메트릭을 서로 다른 방식으로 정규화합니다.

응답(`PlansResponse`) 주요 필드:
- `prediction.predictions`: 24개 `time/value` 포인트
- `recommended_flavor`: small · medium · large
- `expected_cost_per_day`: 소규모 1.2 / 중간 2.8 / 대형 5.5 USD
- `notes`: 예측 피크와 정규화 값

---

## 빠른 시작
> 전체 배포 및 운영 플로우는 [`docs/deployment_guide.md`](docs/deployment_guide.md)를 참고하세요.

1. **모델 파일 확보**  
   `models/best_mcp_lstm_model.h5`, `models/mcp_model_metadata.pkl`을 다운로드하여 `models/`에 둡니다. (Git 미포함)

2. **환경 설정**
   ```bash
   cp .env.example .env
   # 필요한 값 수정: DATA_SOURCE_BACKEND, DATABASE_URL, DISCORD_WEBHOOK_URL, GITHUB_TOKEN 등
   ```

3. **의존성 (선택)**  
   로컬에서 실행하려면 `pip install -r requirements.txt` 후 `uvicorn app.main:app --reload`.

4. **Docker Compose 배포**
   ```bash
   docker-compose up -d --build
   docker-compose ps
   ```

5. **헬스 체크 & 샘플 요청**
   ```bash
   curl http://localhost:8000/health
   curl -X POST http://localhost:8001/api/analyze \
     -H "Content-Type: application/json" \
     -d '{"github_url": "https://github.com/fastapi/fastapi"}'
   ```

---

## 테스트 & 검증
- `tests/smoke_check.py`: 데이터 소스/모델 존재 여부, Baseline 예측 가능 여부 확인
- `tests/test_anomaly_discord.py`: /plans 호출 + Discord 경보 시나리오
- `validate_mvp.sh` / `validate_mvp.ps1`: 배포 전 필수 의존성, 포트, 모델 파일 체크

---

## 문서 모음
| 문서 | 설명 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | End-to-End 구조, 라우팅·정책·Persistence 개요 |
| [`docs/deployment_guide.md`](docs/deployment_guide.md) | 환경 준비, Docker 배포, 체크리스트, 트러블슈팅 |
| [`docs/api_guide.md`](docs/api_guide.md) | Health, `/api/analyze`, `/plans` 호출 예시 |
| [`docs/README_KR.md`](docs/README_KR.md) | 한국어 요약 및 계약 설명 |
| [`models/README.md`](models/README.md) | LSTM 모델 아티팩트 관리 방법 |

---

## 기여 & 이슈
- **이슈 등록**: GitHub Issues
- **버그 리포트 시** `/plans` 요청/응답 JSON, 로그(`docker-compose logs app/backend`)를 첨부해 주세요.
- 코드 리뷰를 위해 주요 로직(메트릭 메타, 정책, 배포 문서)이 간결하게 정리되어 있습니다.  
  새로운 문서를 추가할 때는 `docs/` 하위에 위치시키고 README에서 링크를 갱신해 주세요.

---