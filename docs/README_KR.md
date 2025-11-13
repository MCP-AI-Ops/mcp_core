# MCP Core Orchestrator (한국어 안내)

이 저장소는 `/plans` API를 통해 서비스의 향후 리소스 사용량(예: total_events)을 24시간 단위로 예측하고, 간단한 추천 스펙/비용을 반환하는 FastAPI 기반 코어입니다. 목표는 “컨텍스트 → 모델 선택 → 예측 → 정책 후처리 → 이상 탐지 → 계약(/plans) 응답”의 흐름을 안정적으로 제공하는 것입니다.

본 문서는 팀원이 빠르게 이해하고 실행할 수 있도록 핵심만 한국어로 정리했습니다.

---

## 1) 빠른 시작

### 가상환경 준비
```bash
# PowerShell (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 환경 변수(.env) 예시
프로젝트 루트에 `.env` 생성 (또는 `.env.example` 복사):
```bash
DATA_SOURCE_BACKEND=csv
CSV_DATA_PATH=data/lstm_ready_cluster_data.csv
DISCORD_WEBHOOK_URL=
DISCORD_BOT_NAME=MCP-dangerous
ANOMALY_Z=3.0
```

### 서버 실행
```bash
python -m uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs 확인
```

---

## 2) /plans 계약(Contract)
- 요청 스키마: `app/models/plans.py`의 `PlansRequest`
- 응답 스키마: `PlansResponse`
- 실제 처리 위치: `app/routes/plans.py`

핵심 흐름:
1. `context_extractor.extract_context()`로 `MCPContext` 검증
2. `router.select_route()`가 모델 버전 결정
3. 예측 엔진 호출: `LSTMPredictor` 또는 `BaselinePredictor`
4. `policy.postprocess_predictions()`로 안정화 및 이상 탐지
5. 추천 스펙/비용 산출 후 `PlansResponse`로 응답

이 스키마는 프론트/CI 파이프라인이 의존하는 계약이므로 임의 변경을 지양합니다.

---

## 3) 예측 엔진
- LSTM: `app/core/predictor/lstm_predictor.py`
  - 모델/메타데이터/CSV 위치는 `models/` 및 `data/`
  - 메타데이터(`mcp_model_metadata.pkl`)에 스케일러/특징명/시퀀스 길이 포함
- Baseline: `app/core/predictor/baseline_predictor.py`
  - 최근 데이터 통계 기반 예측 + 폴백 시나리오

### 3-1) Metric 메타데이터
- `app/core/metrics.py`에서 ratio/count 메트릭 분류를 단일화
- Policy(`app/core/policy.py`)와 `/plans` 추천 로직이 동일 메타를 공유
- 신규 메트릭 추가 시 `MetricMeta`를 확장하면 자동으로 clamp/정규화 적용

데이터 소스 선택: `app/core/predictor/data_sources/factory.py`
- `DATA_SOURCE_BACKEND=csv` 또는 `mysql`

---

## 4) 이상 탐지 및 알림
- 이상 탐지: `app/core/anomaly.py` (z-score, 기본 168시간)
- Discord 알림: `app/core/alerts/discord_alert.py`
- 알림은 정책 단계에서 비동기 스레드로 전송되어 예측 경로를 방해하지 않음

---

## 5) 프로젝트 구조(간략)
```
app/
  core/
    context_extractor.py  # 컨텍스트 → MCPContext
    router.py             # 모델 버전 선택
    policy.py             # 가중치/클램프/이상탐지/알림
    predictor/
      base.py
      baseline_predictor.py
      lstm_predictor.py
      data_sources/
        base.py, csv_source.py, mysql_source.py, factory.py
  routes/
    plans.py, deploy.py, destroy.py, status.py
  models/
    common.py, plans.py, ... (Pydantic 스키마)
```

---

## 6) 테스트
```bash
# Discord 웹훅 점검
setx DISCORD_WEBHOOK_URL "<your_webhook>"
python tests/discord_test.py

# 스모크 테스트
python tests/smoke_check.py
```

---

## 7) OpenStack 브랜치와의 병합 전략(feat/#9/openstack)
- 해당 브랜치는 배포 계층(OpenStack 연동, deploy/destroy 라우터/어댑터)에 집중되어 있습니다.
- 현재 코어의 `/plans` 처리 로직(app/routes/plans.py) 및 모델 엔진은 브랜치 변경과 충돌 가능성이 낮습니다.
- 병합 시 체크 리스트:
  1. `/plans` 요청/응답 스키마가 그대로 유지되는지 확인
  2. `policy.postprocess_predictions()`의 인터페이스/리턴 타입 유지
  3. 라우터/컨텍스트 추출 단계에서 새 필드가 추가되면 기본값/호환 처리
  4. 배포용 어댑터(openstack)가 코어 엔드포인트와 강한 결합을 만들지 않는지 확인 (분리 권장)
- 권장: 배포/인프라 모듈을 `gateway/` 또는 별도 레포로 유지하고, 코어는 `/plans`에 집중

---

## 8) 정리 규칙(이번 커밋 기준)
- `.env`는 커밋 금지 → `.env.example`만 제공, `.gitignore`에 `.env` 추가
- MVP 범위에 불필요한 실험 레이어(게이트웨이/HTTP 래퍼)는 제거되었습니다.
- Docker Compose는 `docker-compose.yml` 한 개로 통일(앱+MySQL만 포함)

---

## 9) 자주 묻는 질문
- 모델 파일/메타데이터/CSV가 안 맞으면? → `models/*.h5`, `models/mcp_model_metadata.pkl`, `data/*.csv`는 동일 학습 시점 산출물로 맞추세요.
- LSTM이 실패할 때? → 자동으로 Baseline으로 폴백합니다. 로그 확인 후 모델 자산/경로 점검.
- MySQL로 데이터 소스 바꾸려면? → `.env`에 `DATA_SOURCE_BACKEND=mysql`과 DB 접속 정보를 추가하고 `mysql_source.py` 설정 확인.

---

문의: 코드 상단 모듈/주석과 `docs/operations_update.md`를 함께 참고하세요.
