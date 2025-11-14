# MCP Core - AI 기반 클라우드 리소스 예측 시스템

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15+-orange.svg)](https://www.tensorflow.org/)
[![Claude](https://img.shields.io/badge/Claude-3.5%20Sonnet-purple.svg)](https://www.anthropic.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**자연어 + GitHub URL**만으로 24시간 클라우드 리소스 사용량을 자동 예측하는 AI 시스템

---

## MVP 핵심 가치

### 사용자 경험
```
프론트엔드에서 입력:
  "피크타임에 5000명 정도 사용할 것 같아요"
  https://github.com/fastapi/fastapi

     ↓ 완전 자동화

결과:
  CPU: 4.2 코어 예측
  Memory: 8500 MB 예측
  권장 Flavor: m5.xlarge
  예상 비용: $4.32/day
  24시간 시계열 그래프
```

### 전체 흐름

```
┌─────────────────┐
│   Frontend      │  사용자 입력
│  (React/Vue)    │  - GitHub URL
└────────┬────────┘  - 자연어 요청
         │
         ↓ POST /api/predict
┌─────────────────┐
│  Backend API    │  자동화 레이어
│   (FastAPI)     │  - GitHub 메타데이터 수집
├─────────────────┤  - Claude API: 자연어 → JSON
│ ⚡ Claude 3.5    │  - MCPContext 생성
└────────┬────────┘
         │ POST /plans
         ↓
┌─────────────────┐
│   MCP Core      │  예측 엔진
│  (LSTM Model)   │  - LSTM/Baseline 예측
├─────────────────┤  - Flavor 권장
│ TensorFlow   │  - 이상 탐지
│ 📊 Time Series  │  - Discord 알림
└────────┬────────┘
         │
         ↓ (선택) MySQL 저장
┌─────────────────┐
│    Database     │  이력 관리
│     (MySQL)     │  - 요청 로그
└─────────────────┘  - 예측 결과
```

---

## 🏗️ 아키텍처

### 시스템 구성

| 컴포넌트 | 기술 스택 | 역할 |
|----------|----------|------|
| **Backend API** | FastAPI + Claude API + httpx | 자연어 → MCPContext 자동 변환 |
| **MCP Core** | FastAPI + TensorFlow + LSTM | 24시간 시계열 예측 엔진 |
| **Predictor** | LSTM / Baseline (Numpy) | CPU/Memory 사용량 예측 |
| **Data Source** | CSV / MySQL (SQLAlchemy) | 히스토리 데이터 조회 (24h/168h) |
| **Policy Engine** | `app/core/policy.py` | Metric 정규화 & Clamp |
| **Anomaly Detection** | Z-Score 기반 | 이상 패턴 감지 → Discord 알림 |
| **Database** | MySQL (선택) | 요청/예측 이력 저장 |
| **MCP Analyzer** | Claude Desktop MCP | Claude Desktop 연동용 MCP 서버 |

### 디렉터리 구조

```
mcp_core/
├── app/                      # MCP Core (예측 엔진)
│   ├── main.py              # FastAPI 앱 (포트 8000)
│   ├── core/
│   │   ├── context_extractor.py   # MCPContext 검증
│   │   ├── router.py              # 모델 라우팅 (LSTM/Baseline)
│   │   ├── policy.py              # Metric 정규화
│   │   ├── anomaly.py             # 이상 탐지
│   │   ├── metrics.py             # Metric 메타데이터
│   │   ├── predictor/
│   │   │   ├── lstm_predictor.py  # TensorFlow LSTM
│   │   │   └── baseline_predictor.py  # Numpy Fallback
│   │   └── alerts/
│   │       └── discord_alert.py   # Discord Webhook
│   ├── routes/              # API 라우터
│   │   ├── plans.py         # POST /plans
│   │   ├── status.py        # GET /status
│   │   └── deploy.py        # POST /deploy
│   └── models/              # Pydantic 스키마
│
├── backend_api/             # 완전 자동화 API (포트 8001)
│   ├── main.py             # FastAPI 앱
│   ├── requirements.txt    # 의존성
│   ├── README.md          # 상세 문서
│   └── test.py            # 통합 테스트
│
├── mcp_analyzer/           # Claude Desktop MCP 서버
│   ├── server.py          # MCP 서버 (Claude Desktop용)
│   ├── setup.ps1          # 자동 설정 스크립트
│   └── README.md          # MCP 설정 가이드
│
├── models/                 # 학습된 LSTM 모델 (.h5)
│   ├── best_mcp_lstm_model.h5
│   ├── complete_mcp_lstm.h5
│   └── training_history.json
│
├── data/                   # 학습/테스트 데이터 (CSV)
│   └── lstm_ready_cluster_data.csv
│
├── db/                     # MySQL 스키마
│   └── schema_mvp.sql
│
├── docs/                   # 문서
│   ├── architecture.md
│   ├── deployment_guide.md
│   ├── api_guide.md
│   └── README_KR.md
│
├── tests/                  # 테스트 스크립트
│   ├── smoke_check.py
│   ├── test_anomaly_discord.py
│   └── discord_test.py
│
├── docker-compose.yml      # Docker 배포 설정
├── Dockerfile             # MCP Core 이미지
├── requirements.txt       # Python 의존성
└── .env.example          # 환경변수 템플릿
```

---

## 📡 API 문서

### Backend API (포트 8001)

완전 자동화 API - 자연어를 자동으로 MCPContext로 변환

#### `POST /api/predict`

**Request:**
```json
{
  "github_url": "https://github.com/owner/repo",
  "user_input": "피크타임에 5000명 정도 사용할 것 같아요"
}
```

**Response:**
```json
{
  "success": true,
  "github_info": {
    "full_name": "owner/repo",
    "language": "Python",
    "stars": 12345
  },
  "extracted_context": {
    "service_type": "web",
    "expected_users": 5000,
    "time_slot": "peak",
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "reasoning": "5000명 사용자 → 4 CPU, 8GB 권장"
  },
  "predictions": {
    "lstm": {"cpu": 4.2, "memory": 8500.0},
    "baseline": {"cpu": 4.0, "memory": 8192.0}
  },
  "recommendations": {
    "flavor": "m5.xlarge",
    "cost_per_day": 4.32,
    "notes": "LSTM 모델 기반 권장"
  }
}
```

**상세 문서:** [`backend_api/README.md`](backend_api/README.md)

### MCP Core (포트 8000)

예측 엔진 - LSTM/Baseline 시계열 예측

#### `POST /plans`

**Request:**
```json
{
  "github_url": "owner/repo",
  "metric_name": "total_events",
  "context": {
    "service_type": "web",
    "runtime_env": "prod",
    "time_slot": "peak",
    "expected_users": 5000,
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "weight": 1.0,
    "region": null
  }
}
```

**Response:**
```json
{
  "prediction": {
    "model_version": "lstm_v2",
    "predictions": [
      {"time": "2025-11-13T00:00:00", "value": 4.2},
      {"time": "2025-11-13T01:00:00", "value": 4.5},
      ...
    ]
  },
  "recommended_flavor": "medium",
  "expected_cost_per_day": 2.8,
  "notes": "Peak at 4.5, normalized to 0.85"
}
```

**상세 문서:** [`docs/api_guide.md`](docs/api_guide.md)

---

## 🎨 주요 기능

### 1. 자연어 처리 (Claude API)

```python
# 입력: "피크타임에 5000명 정도 사용할 것 같아요"
# 
# Claude가 자동 추출:
{
  "service_type": "web",
  "expected_users": 5000,
  "time_slot": "peak",
  "curr_cpu": 4.0,
  "curr_mem": 8192.0
}
```

### 2. LSTM 시계열 예측

- **TensorFlow LSTM**: 24시간 예측 (prod/peak 환경)
- **Baseline Fallback**: LSTM 실패 시 자동 전환
- **Metric 정규화**: ratio/count 메트릭 별도 처리

### 3. 이상 탐지 & 알림

```python
# Z-Score 기반 이상 탐지
if abs(z_score) > 2.0:
    # Discord 알림 자동 전송
    send_discord_alert(
        metric="cpu_usage",
        value=8.5,
        threshold=4.0
    )
```

### 4. Flavor 권장

| Flavor | CPU | Memory | 예상 비용 |
|--------|-----|--------|----------|
| Small | 1-2 | 2-4 GB | $1.2/day |
| Medium | 2-4 | 4-8 GB | $2.8/day |
| Large | 4-8 | 8-16 GB | $5.5/day |

### 5. Claude Desktop 연동 (MCP)

```bash
# Claude Desktop에서 사용
"GitHub URL https://github.com/fastapi/fastapi 분석해줘"

# MCP 서버가 자동으로:
# 1. GitHub 메타데이터 수집
# 2. MCP Core /plans 호출
# 3. 예측 결과 반환
```

**설정 가이드:** [`mcp_analyzer/README.md`](mcp_analyzer/README.md)

---

## 빠른 시작 (MVP)

### 사전 요구사항

- Python 3.11+
- Docker & Docker Compose (배포 시)
- Claude API Key ([Anthropic Console](https://console.anthropic.com/))
- MySQL (선택, 로컬 개발 시 CSV 사용 가능)

### 1. 환경변수 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

**필수 환경변수:**
```env
# Backend API (포트 8001)
ANTHROPIC_API_KEY=sk-ant-api03-...        # Claude API 키 (필수)
BACKEND_PORT=8001
MCP_CORE_URL=http://localhost:8000

# MCP Core (포트 8000)
DATA_SOURCE_BACKEND=csv                    # csv 또는 mysql
MODEL_PATH=models/best_mcp_lstm_model.h5
BASELINE_FALLBACK=true

# GitHub (선택)
GITHUB_TOKEN=ghp_...                       # Rate Limit 완화

# Discord (선택)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# MySQL (선택, DATA_SOURCE_BACKEND=mysql 시)
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/mcp_db
```

### 2. 로컬 개발 (빠른 테스트)

**Option A: MCP Core만 실행**
```bash
# 의존성 설치
pip install -r requirements.txt

# MCP Core 시작 (포트 8000)
python -m uvicorn app.main:app --reload --port 8000
```

**Option B: Backend API + MCP Core**
```bash
# Terminal 1: MCP Core
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Backend API
cd backend_api
pip install -r requirements.txt
python main.py
```

### 3. Docker Compose 배포 (프로덕션)

```bash
# 전체 스택 시작 (Backend API + MCP Core + MySQL)
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps
```

### 4. 헬스 체크

```bash
# MCP Core
curl http://localhost:8000/health

# Backend API
curl http://localhost:8001/health
```

### 5. 첫 예측 요청

**방법 1: Backend API 사용 (권장)**
```bash
curl -X POST http://localhost:8001/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/fastapi/fastapi",
    "user_input": "피크타임에 5000명 정도 사용할 것 같아요"
  }'
```

**방법 2: MCP Core 직접 호출**
```bash
curl -X POST http://localhost:8000/plans \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "fastapi/fastapi",
    "metric_name": "total_events",
    "context": {
      "service_type": "web",
      "expected_users": 5000,
      "time_slot": "peak",
      "runtime_env": "prod",
      "curr_cpu": 4.0,
      "curr_mem": 8192.0
    }
  }'
```

### 6. 테스트 실행

```bash
# Backend API 통합 테스트
cd backend_api
python test.py

# MCP Core 검증
cd tests
python smoke_check.py
python test_anomaly_discord.py
```

---

## 테스트 & 검증

### 자동 테스트

```bash
# Backend API 통합 테스트
cd backend_api
python test.py
# → 3개 시나리오 (피크타임/일반/개발) 자동 테스트

# MCP Core 스모크 테스트
cd tests
python smoke_check.py
# → 데이터 소스, 모델, Baseline 검증

# 이상 탐지 + Discord 알림 테스트
python test_anomaly_discord.py
# → /plans 호출 + Discord 웹훅 확인
```

### MVP 검증 스크립트

**Windows:**
```powershell
.\validate_mvp.ps1
```

**Linux/Mac:**
```bash
./validate_mvp.sh
```

**검증 항목:**
- Python 버전
- 필수 패키지 설치
- 환경변수 설정
- 모델 파일 존재
- 포트 사용 가능 여부
- Docker 실행 여부 (배포 시)

---

## 📚 문서 모음

| 문서 | 설명 |
|------|------|
| **시작하기** |
| [`README.md`](README.md) | 전체 개요 및 빠른 시작 (현재 문서) |
| [`backend_api/README.md`](backend_api/README.md) | Backend API 상세 가이드 |
| [`mcp_analyzer/README.md`](mcp_analyzer/README.md) | Claude Desktop MCP 설정 |
| **아키텍처** |
| [`docs/architecture.md`](docs/architecture.md) | End-to-End 구조, 라우팅 정책 |
| [`docs/MCP_CORE_ARCHITECTURE.md`](docs/MCP_CORE_ARCHITECTURE.md) | MCP Core 상세 설계 |
| **배포 & 운영** |
| [`docs/deployment_guide.md`](docs/deployment_guide.md) | Docker 배포, 트러블슈팅 |
| [`docs/persistence_mvp.md`](docs/persistence_mvp.md) | MySQL 스키마, 데이터 관리 |
| **API** |
| [`docs/api_guide.md`](docs/api_guide.md) | `/plans`, `/api/predict` 호출 예시 |
| **기타** |
| [`models/README.md`](models/README.md) | LSTM 모델 아티팩트 관리 |

---

## 🐛 트러블슈팅

### Backend API 오류

**증상:** `Claude API key not set`
```json
{
  "extracted_context": {
    "reasoning": "Claude API key not set"
  }
}
```

**해결:**
1. `.env` 파일에 `ANTHROPIC_API_KEY` 설정
2. [Anthropic Console](https://console.anthropic.com/)에서 키 발급
3. 서버 재시작

---

**증상:** `GitHub API error: 403` (Rate Limit)

**해결:**
1. `.env`에 `GITHUB_TOKEN` 설정
2. [GitHub Settings → Tokens](https://github.com/settings/tokens)에서 생성
3. 권한: `public_repo` (공개 저장소만)

---

### MCP Core 오류

**증상:** `Model file not found`

**해결:**
```bash
# 모델 파일 확인
ls models/best_mcp_lstm_model.h5

# 없으면 학습 필요 또는 다운로드
# (Git에는 포함되지 않음, 별도 공유)
```

---

**증상:** `LSTM prediction failed, using baseline`

**해결:**
- 정상 동작 (Baseline Fallback)
- LSTM 실패 시 자동으로 Baseline 사용
- 로그 확인: `docker-compose logs app`

---

### Docker 오류

**증상:** `Port 8000 already in use`

**해결:**
```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Mac/Linux

# 프로세스 종료 후 재시작
docker-compose down
docker-compose up -d
```

---

**증상:** MySQL 연결 실패

**해결:**
```bash
# MySQL 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs mysql

# 환경변수 확인
cat .env | grep DATABASE_URL
```

---

## 배포 체크리스트

### 배포 전

- [ ] `.env` 파일 설정 완료
  - [ ] `ANTHROPIC_API_KEY` 설정
  - [ ] `DATA_SOURCE_BACKEND` 설정 (csv/mysql)
  - [ ] `DISCORD_WEBHOOK_URL` 설정 (선택)
  - [ ] `GITHUB_TOKEN` 설정 (선택)
- [ ] 모델 파일 존재 확인
  - [ ] `models/best_mcp_lstm_model.h5`
  - [ ] `models/complete_mcp_lstm.h5`
- [ ] 검증 스크립트 실행
  - [ ] `validate_mvp.ps1` (Windows)
  - [ ] `validate_mvp.sh` (Linux/Mac)
- [ ] 테스트 실행
  - [ ] `backend_api/test.py`
  - [ ] `tests/smoke_check.py`

### Docker 배포

```bash
# 1. 전체 스택 시작
docker-compose up -d --build

# 2. 헬스 체크
curl http://localhost:8000/health
curl http://localhost:8001/health

# 3. 테스트 요청
cd backend_api
python test.py

# 4. 로그 모니터링
docker-compose logs -f
```

### 로컬 개발

```bash
# Terminal 1: MCP Core
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Backend API
cd backend_api
python main.py

# Terminal 3: 테스트
cd backend_api
python test.py
```

---

## 🤝 기여 가이드

### 이슈 제보

**버그 리포트 시 포함할 내용:**
- 요청 JSON (`/api/predict` 또는 `/plans`)
- 응답 JSON (에러 메시지)
- 로그 (`docker-compose logs app`)
- 환경변수 설정 (민감 정보 제외)

**예시:**
```markdown
### 버그 설명
Backend API에서 자연어 파싱 실패

### 재현 방법
1. POST /api/predict
2. user_input: "..."
3. 응답: {"detail": "..."}

### 환경
- OS: Windows 11
- Python: 3.11.5
- Docker: 사용 안함
- ANTHROPIC_API_KEY: 설정됨

### 로그
```
ERROR: Claude error: ...
```
```

### Pull Request

1. Fork 후 브랜치 생성
2. 코드 수정 + 테스트 작성
3. `README.md` 업데이트 (필요 시)
4. PR 생성

---

## 📄 라이센스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 👥 팀

**MCP AI Ops Team**

- Backend API: FastAPI + Claude API 자동화
- MCP Core: LSTM 예측 엔진
- Frontend: React/Vue (별도 레포)
- CI/CD: GitHub Actions (별도 설정)

---

## 📞 문의

- **이슈:** [GitHub Issues](https://github.com/MCP-AI-Ops/mcp_core/issues)
- **이메일:** team@mcp-ai-ops.com (예시)
- **문서:** 이 레포의 `docs/` 디렉터리

---

**Made with ❤️ by MCP Team** | **Powered by Claude 3.5 Sonnet & TensorFlow**
