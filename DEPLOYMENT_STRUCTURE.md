# 배포용 폴더 구조 (feat/#13/db)

## ✅ 프로덕션 배포 파일 구조

```
mcp_core/
├── .env                      # ⚠️ Git 제외 (서버에서 직접 작성)
├── .env.mysql               # ⚠️ Git 제외 (MySQL 전용 env)
├── .gitignore               # ✅ 업데이트됨
├── docker-compose.yml       # ✅ 통합 compose (MySQL + App + Backend)
├── Dockerfile               # ✅ 최적화됨 (선택적 COPY)
├── requirements.txt         # ✅ Python 의존성
├── README.md                # ✅ 메인 문서
├── README_MYSQL.md          # ✅ MySQL 설정 가이드
├── CLEANUP_NOTES.md         # ✅ 정리 가이드
│
├── app/                     # ✅ MCP Core (8000 포트)
│   ├── main.py             # FastAPI 진입점
│   ├── config/
│   │   └── settings.py
│   ├── core/
│   │   ├── context_extractor.py
│   │   ├── router.py
│   │   ├── policy.py
│   │   ├── errors.py
│   │   ├── db_sqlalchemy.py        # ✅ 프로덕션 ORM
│   │   ├── db.py                   # ⚠️ deprecated (다음 제거)
│   │   ├── persistence_models.py   # ✅ SQLAlchemy 모델
│   │   ├── metric_history.py
│   │   └── predictor/
│   │       ├── base.py
│   │       ├── lstm_predictor.py
│   │       └── baseline_predictor.py
│   ├── routes/
│   │   ├── plans.py         # ✅ /plans 엔드포인트
│   │   ├── status.py        # ✅ /status 엔드포인트
│   │   └── destroy.py       # ✅ /destroy 엔드포인트
│   └── models/
│       ├── plans.py
│       ├── status.py
│       └── common.py
│
├── backend_api/             # ✅ Backend Gateway (8001 포트)
│   ├── main.py             # Claude + GitHub 자동화
│   ├── requirements.txt
│   └── README.md
│
├── db/                      # ✅ 데이터베이스
│   └── schema_unified.sql  # ✅ 통합 스키마 (최신)
│
├── models/                  # ✅ LSTM 모델 파일
│   ├── best_mcp_lstm_model.h5
│   └── README.md
│
├── data/                    # ✅ 학습 데이터
│   └── lstm_ready_cluster_data.csv
│
├── scripts/                 # ✅ 프로덕션 스크립트만 유지
│   ├── start_mysql.sh              # MySQL 시작
│   ├── stop_mysql.sh               # MySQL 중지
│   ├── backup_mysql.sh             # MySQL 백업
│   ├── ingest_metric_history.py    # 메트릭 적재
│   └── call_multi_plans.py         # 멀티 메트릭 테스트
│
├── tests/                   # ✅ 테스트 스위트
│   ├── smoke_check.py
│   ├── test_anomaly_discord.py
│   └── discord_test.py
│
└── docs/                    # ✅ 문서
    ├── architecture.md      # ✅ 아키텍처 설명
    ├── api_guide.md
    ├── deployment_guide.md
    └── DATA_FLOW.md
```

---

## 🗑️ 삭제된 파일 (feat/#13/db)

### 문서
- ❌ `docs/MCP_CORE_ARCHITECTURE.md` - 인코딩 손상
- ❌ `docs/persistence_mvp.md` - 구식 스키마 참조
- ❌ `docs/README_KR.md` - README.md와 중복
- ❌ `README-TEST.md` - Poetry 가이드 (미사용)

### 코드/라우터
- ❌ `app/routes/router_auth.py` - 미사용 (main.py에서 비활성화)
- ❌ `app/models/model_user.py` - User 테이블 (auth 미사용)
- ⚠️ `app/core/db.py` - deprecated (다음 제거 예정)

### 스키마
- ❌ `schema_mcp.txt` - 구식 스키마
- ❌ `app/core/predictor/data_sources/schema_mcp.txt` - 중복

### 테스트/검증
- ❌ `check_claude_api.py` - API 키 확인 (개발용)
- ❌ `test_claude_status.py` - 백엔드 상태 확인 (개발용)
- ❌ `test_full_flow.py` - 전체 플로우 테스트
- ❌ `run_full_flow_via_backend.py` - 백엔드 통합 테스트
- ❌ `validate_mvp.ps1` - MVP 검증 (로컬용)
- ❌ `validate_mvp.sh` - MVP 검증 (로컬용)

### 기타
- ❌ `demoMCPproject.ipynb` - 데모 노트북
- ❌ `24h_forecast_example.png` - 예시 이미지
- ❌ `__pycache__/` - Python 캐시 (전체)
- ❌ `.env.backup` - 환경변수 백업

---

## 📦 Docker 배포 순서

### 1. 로컬 정리
```powershell
# 캐시 삭제
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# Git 상태 확인
git status
```

### 2. Git 커밋
```powershell
git add .
git commit -m "feat(db): Production-ready structure optimization

- Remove deprecated/duplicate files (20+ files)
- Update .gitignore with legacy patterns
- Optimize Dockerfile with selective COPY
- Mark db.py as deprecated (use db_sqlalchemy.py)
- Clean up auth routes (unused)
- Update documentation references"

git push origin feat/#13/db
```

### 3. 서버 배포
```bash
# SSH 접속
ssh mcp

# 프로젝트 디렉토리
cd /opt/mcp

# 최신 코드 가져오기
git pull origin feat/#13/db

# 스키마 적용 (옵션 A: 깨끗한 시작)
docker compose down
docker volume rm mcp_mysql_data
docker compose up -d

# 또는 (옵션 B: 기존 데이터 유지)
docker exec -i mcp_mysql mysql -u root -padmin mcp_core < db/schema_unified.sql

# 헬스체크
docker ps
docker logs -f mcp-core
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### 4. 테이블 확인
```bash
docker exec -it mcp_mysql mysql -u root -padmin -e "USE mcp_core; SHOW TABLES;"
```

### 5. ORM 테스트
```bash
docker exec -it mcp-core python -m app.core.db_sqlalchemy
```

---

## 🔒 민감 정보 보호

### Git에서 제외되는 파일 (.gitignore)
- `.env` / `.env.backup` / `.env.local`
- `.env.mysql`
- `__pycache__/`
- `*.log`
- `.venv/`
- `.vscode/`

### 서버에서 직접 작성
```bash
# .env 파일
DATABASE_URL=mysql+pymysql://mcp_user:PASSWORD@mysql:3306/mcp_core
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 📊 배포 전 체크리스트

- [ ] `__pycache__` 폴더 삭제 완료
- [ ] `.env` 파일이 Git staged 안 되었는지 확인
- [ ] 불필요한 문서/테스트 파일 삭제 확인
- [ ] `db/schema_unified.sql` 존재 확인
- [ ] `models/best_mcp_lstm_model.h5` 존재 확인
- [ ] `requirements.txt` 최신 의존성 확인
- [ ] Docker Compose 파일 검증
- [ ] 서버 환경변수 설정 확인
- [ ] MySQL 볼륨 백업 (필요 시)

---

## 🚀 다음 단계

1. **로컬 테스트**
   ```powershell
   docker compose up -d
   curl http://localhost:8000/health
   ```

2. **원격 배포**
   ```bash
   git push origin feat/#13/db
   ssh mcp "cd /opt/mcp && git pull && docker compose up -d"
   ```

3. **연결 테스트**
   ```bash
   docker exec -it mcp-core python -m app.core.db_sqlalchemy
   ```

4. **메트릭 적재**
   ```bash
   docker exec -it mcp-core python scripts/ingest_metric_history.py \
     --csv data/lstm_ready_cluster_data.csv \
     --github-url https://github.com/MCP-AI-Ops/mcp_core \
     --metric total_events \
     --time-column timestamp \
     --value-column total_events \
     --limit 1000
   ```
