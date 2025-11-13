# Deployment & Operations Guide

MCP Core MVP를 설치·운영할 때 필요한 모든 절차(체크리스트, 스크립트, Docker, 트러블슈팅)를 한 문서로 통합했습니다.

---

## 1. 필수 준비물
| 항목 | 설명 |
|------|------|
| Docker & Docker Compose v2+ | `docker --version`, `docker compose version`으로 확인 |
| Git |
| Python 3.11+ (선택) | 로컬에서 직접 실행할 경우 |
| GitHub Personal Access Token (권장) | Rate limit 완화를 위해 `GITHUB_TOKEN`에 설정 |
| Discord Webhook (선택) | 이상 감지 알림 채널 |
| LSTM 모델 아티팩트 | `models/best_mcp_lstm_model.h5`, `models/mcp_model_metadata.pkl` |

### 포트 사용
- 3308 (MySQL)
- 8000 (MCP Core)
- 8001 (Backend API)

---

## 2. 파일 & 환경 체크
1. `.env.example`를 복사해 `.env` 생성  
   ```bash
   cp .env.example .env  # Windows는 copy 사용
   ```
2. 최소 설정
   ```dotenv
   DATA_SOURCE_BACKEND=csv            # 또는 mysql
   CSV_DATA_PATH=data/lstm_ready_cluster_data.csv
   DISCORD_WEBHOOK_URL=...            # 선택
   GITHUB_TOKEN=...                   # 선택 권장
   DATABASE_URL=mysql+pymysql://...   # Persistence 사용 시
   ```
3. 모델 파일 존재 여부
   ```bash
   ls models/*.h5 models/*.pkl
   ```
4. 검증 스크립트
   ```bash
   # Windows
   .\validate_mvp.ps1
   # Linux / macOS
   bash validate_mvp.sh
   ```
   > 포트 충돌, Docker 설치 여부, 모델 파일 누락 등을 자동 점검합니다.

---

## 3. Docker Compose 배포
```bash
docker-compose up -d --build
docker-compose ps
```

헬스 체크:
```bash
curl http://localhost:8000/health   # MCP Core
curl http://localhost:8001/health   # Backend API
```

샘플 분석 요청:
```bash
curl -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/fastapi/fastapi"}'
```

로그 추적:
```bash
docker-compose logs -f
docker-compose logs -f app
docker-compose logs -f backend
```

---

## 4. 배포 체크리스트
- [ ] `models/best_mcp_lstm_model.h5`, `models/mcp_model_metadata.pkl` 존재
- [ ] `.env` 생성 및 민감 정보 입력 (Git 커밋 금지)
- [ ] 포트 3308 / 8000 / 8001 사용 가능
- [ ] Docker/Compose 설치 및 버전 확인
- [ ] (선택) `DISCORD_WEBHOOK_URL`, `GITHUB_TOKEN` 설정
- [ ] `validate_mvp.(ps1|sh)` 실행 완료

---

## 5. 플랫폼별 팁

### Windows
- PowerShell에서 `Set-ExecutionPolicy RemoteSigned` 필요할 수 있음
- `validate_mvp.ps1` 실행 시 관리자 권한 권장

### Ubuntu (예: EC2)
1. Docker 설치  
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg lsb-release
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
     https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" |
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker $USER
   ```
2. 재로그인 후 `docker compose version` 확인
3. Git clone → `.env` 작성 → `docker compose up -d`

---

## 6. 운영 명령 모음
```bash
# 재시작
docker-compose restart
# 특정 서비스만
docker-compose restart app
# 중지 & 삭제
docker-compose down          # 컨테이너만
docker-compose down -v       # + 볼륨
# 이미지 포함 삭제
docker-compose down --rmi all -v
# 실시간 리소스
docker stats
```

---

## 7. Troubleshooting
| 증상 | 원인 & 해결 |
|------|------------|
| `PredictionError: LSTM 모델 로드 실패` | 모델 파일 미배치 → `models/` 폴더 확인, 권한 644 |
| `403 API rate limit exceeded` | `GITHUB_TOKEN` 미설정 → `.env`에 토큰 추가 후 `docker-compose restart backend` |
| `address already in use` (8000/8001/3308) | 포트 충돌 → 기존 프로세스 종료 또는 `docker-compose.yml`에서 포트 변경 |
| `Can't connect to MySQL server` | MySQL 초기화 지연 → `docker-compose logs mysql` 확인 후 app 재시작 |
| Discord 알림 미전송 | Webhook 미설정 → `.env` 값 확인 후 `tests/discord_test.py`로 테스트 |

---

## 8. Docs & Reference
- 아키텍처: [`docs/architecture.md`](./architecture.md)
- API 호출 예시: [`docs/api_guide.md`](./api_guide.md)
- 한국어 요약: [`docs/README_KR.md`](./README_KR.md)
- 모델 관리: [`models/README.md`](../models/README.md)

필요한 문서를 추가로 작성할 경우 `docs/` 하위에 배치하고 README에 링크를 업데이트해 주세요.
