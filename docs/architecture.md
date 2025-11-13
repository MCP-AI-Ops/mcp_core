# MCP Core Architecture

본 문서는 MCP Core의 End-to-End 동작, 내부 모듈, 데이터/모델 파이프라인, 운영 관점을 한 번에 정리한 아키텍처 가이드입니다.

---

## 1. Mission & Context
- **입력**: 사용자가 GitHub 리포지토리 URL 하나를 전달
- **출력**: 향후 24h 리소스 예측, 권장 인스턴스 플레버, 예상 비용, 이상 감지 결과
- **Automation 목표**: GitHub 분석 → 컨텍스트 생성 → 모델 라우팅/예측 → 이상 감지/알림까지 전 자동화

### Claude MCP에서 Backend API로
초기에는 Claude Desktop MCP 플러그인(`mcp_analyzer/server_production.py`)만 염두에 두고 “@github-analyzer …” 형태로 대화형 명령을 보내면 MCP 서버가 GitHub 분석과 `/plans` 호출을 대신하는 구조를 실험했습니다.  
하지만 실무 환경에서는 프론트엔드·CI/CD 파이프라인이 동일한 기능을 자동화해야 했기 때문에, MCP 사용 여부와 관계없이 HTTP 호출만으로 동일한 결과를 얻을 수 있는 **Backend API 게이트웨이**를 추가로 설계했습니다.  
현재는 두 경로가 공존합니다.
1. **Backend API**: 프론트엔드 혹은 배치 시스템이 직접 `/api/analyze`를 호출(권장 흐름)  
2. **Claude MCP**: 개발자가 Claude Desktop에서 빠르게 결과를 확인하고 싶을 때 사용하는 편의 채널  
모두 최종적으로 MCP Core `/plans` 계약을 그대로 사용하므로, 한쪽을 개선하면 다른 쪽도 자동으로 혜택을 받습니다.

### 상위 구성
```
Frontend / Claude MCP
        │  (GitHub URL)
        ▼
Backend API (/api/analyze) ──> MCP Core (/plans) ──> Discord & Optional MySQL
```

---

## 2. Request Flow
1. **Frontend / MCP**: 사용자가 “repo 분석”을 요청하면 GitHub URL을 Backend API로 전달.
2. **Backend API (`backend_api/main.py`)**  
   - `GitHubAnalyzer`로 stars/forks/언어/README를 수집.  
   - 규칙 기반으로 `service_type`, `expected_users`, `curr_cpu/mem`, `time_slot` 추정.  
   - `MCPCoreClient`를 통해 `/plans` POST 호출.
3. **MCP Core FastAPI (`app/routes/plans.py`)**  
   - `context_extractor`: `MCPContext` Pydantic 검증 + 기본값 보강.  
   - `router`: `(runtime_env, time_slot, service_type)` 규칙으로 모델 버전을 선택. prod-peak web은 `*lstm*` 모델로 라우팅하여 LSTM이 기본값이 되도록 구성.  
   - `predictor`: LSTM 실패 시 Baseline 자동 페일백. 데이터 소스는 env(`DATA_SOURCE_BACKEND`)로 전환.  
   - `policy`: metric 메타데이터(`app/core/metrics.py`)를 참조해 ratio/count에 서로 다른 clamp 규칙 적용.  
   - `anomaly`: 168h 히스토리 대비 z-score. 감지 시 Discord Webhook 및 (옵션) MySQL 기록.
4. **응답**: Predictions + 추천 플레버 + 비용 + 노트(정규화 피크 값).  
5. **Logging & Persistence (선택)**  
   - `DATABASE_URL`이 유효하면 repositories / plan_requests / predictions / anomaly_detections / alert_history에 기록.  
   - 실패 시에도 API 응답은 영향받지 않으며 내부적으로 DEBUG 로그만 남김.

---

## 3. Core Modules
| 모듈 | 역할 | 비고 |
|------|------|------|
| `context_extractor.py` | `MCPContext` 변환/검증 | timestamp 기본값, 필수 필드 체크 |
| `router.py` | 모델 버전 결정 | prod-peak web → `*_lstm_*`, dev → baseline |
| `predictor/*.py` | Baseline / LSTM 구현 | 데이터 소스 factory 기반 |
| `metrics.py` | Metric 메타데이터 | kind, clamp, flavor 정규화 기준 |
| `policy.py` | 가중치 & clamp 후속 처리 | ratio는 [0,1], count는 0 미만 차단 |
| `anomaly.py` | z-score 기반 이상 감지 | metric 메타데이터 재사용 |
| `alerts/discord_alert.py` | Webhook 송신 | username/avatar 커스터마이즈 가능 |

### Predictor & Data Source
- **Baseline**: 최근 24h 평균/분산/추세를 사용, 데이터 없을 경우 fallback 곡선.
- **LSTM**:  
  - 모델: `models/best_mcp_lstm_model.h5` (Git 미포함)  
  - 메타: `models/mcp_model_metadata.pkl` (scaler, feature_names, sequence_length 등)  
  - 입력 데이터: `data/lstm_ready_cluster_data.csv` (1,439 x 84)  
  - 학습 스크립트: `app/core/predictor/train_from_notebook.py`
- **DataSource Factory** (`app/core/predictor/data_sources/factory.py`)  
  - CSV: 빠른 데모용 (`DATA_SOURCE_BACKEND=csv`)  
  - MySQL: `metric_history` 테이블, `mysql+pymysql://` 연결  
  - 데이터가 부족하면 padding하여 horizon을 맞춤

---

## 4. Metric Policy & Recommendations
`app/core/metrics.py`에서 메트릭마다 kind(clamp, planning_max)를 정의합니다.

- `total_events`: count, planning_max=1000 → 100/1000 기준으로 flavor 결정  
- `avg_cpu`, `avg_memory`, `cpu_utilization`, `memory_utilization`: ratio, [0,1] clamp  
- 새 메트릭은 `MetricMeta`만 추가하면 Policy·Anomaly·Flavor 계산이 자동 반영됩니다.

플레버 결정 로직 (`app/routes/plans.py`)
```
normalized_peak ≥ 0.85 → large
normalized_peak ≥ 0.55 → medium
else → small
```
예상 비용은 small 1.2 / medium 2.8 / large 5.5 USD/day로 단순화된 MVP 휴리스틱입니다.

---

## 5. Persistence & Ops Notes
- **옵션 DB**: `db/schema_mvp.sql` (repositories, plan_requests, predictions, anomaly_detections, alert_history)
- **환경 변수 요약**
  - `DATABASE_URL` (미설정 시 no-op)
  - `DATA_SOURCE_BACKEND=csv|mysql`
  - `DISCORD_WEBHOOK_URL`, `DISCORD_BOT_NAME`, `DISCORD_BOT_AVATAR`
  - `ANOMALY_Z` (기본 3.0)
  - `GITHUB_TOKEN` (Backend API rate limit 완화)
- **알림**: Discord Webhook 실패는 예외를 삼키고 로그만 남김. 테스트 스크립트 `tests/discord_test.py`.
- **모델 관리**: `.h5`, `.pkl`은 Git에 포함되지 않으며 배포 전 반드시 배치해야 함.

---

## 6. Data Processing Rules
1. **결측치**: feature는 forward-fill 후 0, target은 음수 컷+`log1p`(학습 시)  
2. **Outlier**: 학습 스크립트에서 IQR 기반 Winsorize  
3. **Policy Clamp**: ratio metric은 [0,1], count metric은 음수만 0 처리  
4. **Anomaly**: 168h 히스토리 vs 24h 예측 peak의 z-score. std=0인 경우 mean 기반 비율 비교.

---

## 7. Deployment Footprint
자세한 배포·트러블슈팅은 [`docs/deployment_guide.md`](./deployment_guide.md) 참고.

요약:
- Docker Compose (mysql/app/backend)
- 모델 파일 존재 여부 검증
- 포트 3308/8000/8001 사용
- `validate_mvp.(ps1|sh)`로 환경 자동 체크

---

## 8. 앞으로의 확장 포인트
- **Frontend 연동**: `/api/analyze` 응답을 UI에 시각화
- **CI/CD**: GitHub Actions로 테스트/빌드 → Docker Registry 푸시
- **Observability**: FastAPI `/metrics`, 중앙 로깅, Prometheus/Grafana 연동
- **Model Ops**: 다중 모델 실험, 주기적 재학습 파이프라인, GitHub Release로 모델 배포 자동화

---

### Reference Files
- `docs/deployment_guide.md`: 배포/운영/체크리스트
- `docs/api_guide.md`: curl & PowerShell 예제
- `docs/README_KR.md`: 한글 요약/계약
- `models/README.md`: 모델 아티팩트 관리
