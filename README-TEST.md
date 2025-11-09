# 프로젝트 실행 방법

## 1. Poetry 설치 확인

Poetry가 설치되어 있는지 확인:
```bash
poetry --version
```

설치되어 있지 않다면:
```bash
# macOS (Homebrew)
brew install poetry

# 또는 공식 설치 스크립트
curl -sSL https://install.python-poetry.org | python3 -
```

## 2. 의존성 설치

프로젝트 루트에서 의존성 설치:
```bash
poetry install
```

개발 의존성까지 모두 설치됩니다 (black, isort, ruff, pytest, mypy 포함).

프로젝트 package 한번 update하고 들어가기!
```bash
poetry lock
```

## 3. 가상환경 사용 방법

### 방법 1: Poetry shell (추천)
```bash
poetry env activate
# 가상환경이 활성화된 상태로 쉘이 시작됩니다
```

### 방법 2: poetry run으로 명령 실행
가상환경을 활성화하지 않고도 Poetry 가상환경에서 명령 실행:
```bash
poetry run python app/main.py
poetry run pytest
poetry run black .
```

### 방법 3: 가상환경 직접 활성화
```bash
# 가상환경 경로 확인
poetry env info --path

# 활성화 (경로는 위 명령어 결과로 대체)
source $(poetry env info --path)/bin/activate
```

## 4. 프로젝트 실행

### FastAPI 서버 실행
```bash
# Poetry shell 안에서
poetry shell
uvicorn app.main:app --reload

# 또는 poetry run 사용
poetry run uvicorn app.main:app --reload
```

### 개발 모드로 실행 (코드 변경 시 자동 재시작)
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. 개발 도구 사용

### 코드 포맷팅
```bash
poetry run black .
poetry run isort .
```

### 린팅
```bash
poetry run ruff check .
poetry run ruff check --fix .
```

### 타입 체크
```bash
poetry run mypy app/
```

### 테스트 실행
```bash
poetry run pytest
poetry run pytest tests/ -v
```

## 6. 의존성 관리

### 새 패키지 추가
```bash
poetry add <package-name>
poetry add --group dev <package-name>  # 개발 의존성
```

### 패키지 제거
```bash
poetry remove <package-name>
```

### 의존성 업데이트
```bash
poetry update  # 모든 패키지 업데이트
poetry update <package-name>  # 특정 패키지만 업데이트
```

### lock 파일 업데이트
```bash
poetry lock  # pyproject.toml 변경 후 lock 파일 재생성
```

## 7. 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:
```bash
# 데이터 소스
DATA_SOURCE_BACKEND=csv
CSV_DATA_PATH=data/lstm_ready_cluster_data.csv

# Discord 알림 (선택)
DISCORD_WEBHOOK_URL=your_webhook_url
DISCORD_BOT_NAME=MCP-dangerous

# OpenStack 설정 (VM 배포 시 필요)
OS_AUTH_URL=http://localhost:5000/v3
OS_USERNAME=admin
OS_PASSWORD=secretadmin
OS_PROJECT_NAME=admin
OS_REGION_NAME=RegionOne
```

### ⚠️ 중요: .env 파일 변경 후 재시작 필요

`.env` 파일을 수정한 후에는 **반드시 서버를 재시작**해야 변경사항이 반영됩니다:

```bash
# 실행 중인 서버를 중지 (Ctrl+C) 후 다시 시작
poetry run uvicorn app.main:app --reload

# 또는 poetry shell 사용 시
poetry env activate
uvicorn app.main:app --reload
```

**참고:** `--reload` 옵션은 코드 변경 시 자동 재시작하지만, `.env` 파일 변경은 감지하지 않습니다. 수동으로 재시작해야 합니다.

## 8. 프로젝트 구조

- `app/`: 메인 애플리케이션 코드
- `app/main.py`: FastAPI 앱 진입점
- `app/routes/`: API 라우터
- `app/core/`: 핵심 비즈니스 로직
- `models/`: 학습된 모델 파일
- `data/`: 데이터 파일
- `tests/`: 테스트 코드

## 9. 주의사항

- 이 프로젝트는 `package-mode = false`로 설정되어 있어 의존성 관리만 Poetry로 수행합니다
- Python 3.10 이상이 필요합니다
- 가상환경은 Poetry가 자동으로 관리하므로 별도로 생성할 필요가 없습니다

## 10. 현재 사용 버전 상태
- python: 3.12

## 11. FastAPI 서버 띄우기

구조가 README대로라면 대략:

poetry run uvicorn app.main:app --reload


브라우저에서 http://localhost:8000/docs 열어 Swagger UI 들어가지는지 확인
👉 여기까지 되면 MCP Core를 로컬에서 돌릴 수 있는 상태가 됨.

### /plans Contact 예시
```
curl -X 'POST' \
  'http://localhost:8000/plans' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "service_id": "demo-service",
  "metric_name": "total_events",
  "context": {
    "context_id": "ctx-1234",
    "timestamp": "2025-11-08T18:44:10.519Z",
    "service_type": "web",
    "runtime_env": "prod",
    "time_slot": "normal",
    "weight": 1,
    "region": "ap-northeast-2",
    "expected_users": 100,
    "curr_cpu": 0.25,
    "curr_mem": 0.35
  }
}
'
```