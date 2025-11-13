# GitHub MCP Server# MCP GitHub Analyzer



GitHub 저장소를 분석하여 MCP Core로 리소스 예측을 받는 간단한 MCP 서버입니다.Claude Desktop용 GitHub 저장소 분석 및 AI 기반 리소스 예측 MCP 서버



## 역할 분담## 🎯 주요 기능



### 이 MCP 서버 (server.py)- **GitHub 저장소 자동 분석**: 언어, Stars, Forks 등 메타데이터 수집

- ✅ GitHub URL 입력- **서비스 타입 자동 감지**: web, api, worker, data 타입 자동 분류  

- ✅ 저장소 메타데이터 분석- **AI 기반 리소스 예측**: LSTM 모델을 통한 24시간 리소스 사용량 예측

- ✅ MCPContext 생성- **이상 징후 탐지**: Z-score 기반 anomaly detection

- ✅ MCP Core 호출- **비용 추정**: 권장 인스턴스 타입 및 예상 일일 비용 제공



### MCP Core (app/main.py)## 📋 사전 요구사항

- ✅ LSTM/Baseline 예측

- ✅ Flavor 추천- Python 3.11+

- ✅ 이상 탐지- Claude Desktop 1.0.0+

- ✅ Discord 알림- MCP Core 서버 실행 중 (`http://localhost:8000`)



---## 🚀 설치



## 빠른 시작### 1. 패키지 설치



### 1. 자동 설정 (권장)```bash

cd mcp_core

```powershellpip install -r mcp_analyzer/requirements.txt

cd mcp_analyzer```

.\setup.ps1

```### 2. MCP Core 서버 실행



### 2. MCP Core 시작```bash

python -m uvicorn app.main:app --reload

```bash```

python -m uvicorn app.main:app --port 8000

```서버가 `http://localhost:8000`에서 실행됩니다.



### 3. Claude Desktop 재시작### 3. Claude Desktop 설정



### 4. 사용#### Windows



```설정 파일 위치: `%APPDATA%\Claude\claude_desktop_config.json`

GitHub 저장소 https://github.com/fastapi/fastapi 분석해줘

``````json

{

---  "mcpServers": {

    "github-analyzer": {

## 수동 설정      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",

      "args": ["C:\\FULL\\PATH\\TO\\mcp_core\\mcp_analyzer\\server_production.py"],

`%APPDATA%\Claude\claude_desktop_config.json`:      "env": {

        "MCP_CORE_URL": "http://localhost:8000"

```json      }

{    }

  "mcpServers": {  }

    "github-analyzer": {}

      "command": "python.exe 전체 경로",```

      "args": ["server.py 전체 경로"],

      "env": {**⚠️ 주의**: 절대 경로를 사용하세요!

        "MCP_CORE_URL": "http://localhost:8000"

      }#### Mac/Linux

    }파일: `~/Library/Application Support/Claude/claude_desktop_config.json`

  }

}```json

```{

  "mcpServers": {

---    "github-analyzer": {

      "command": "python3",

## 환경변수      "args": ["/path/to/mcp_core/mcp_analyzer/server.py"],

      "env": {

- `MCP_CORE_URL`: MCP Core 서버 URL (기본: http://localhost:8000)        "GITHUB_TOKEN": "ghp_your_token_here",

- `GITHUB_TOKEN`: GitHub Token (선택, Rate Limit 회피용)        "MCP_CORE_URL": "http://localhost:8000"

      }

---    }

  }

## 예시}

```

### 입력

```## 📝 사용 방법

https://github.com/tensorflow/tensorflow 분석해줘

```1. MCP Core 서버 실행

```bash

### 출력cd ../  # mcp_core 루트로

```docker compose up -d

# 🎯 GitHub 저장소 분석 결과# 또는

uvicorn app.main:app --reload

## 📦 저장소 정보```

- 이름: tensorflow/tensorflow

- 언어: Python2. Claude Desktop 재시작

- 스타: ⭐ 185,000

3. Claude Desktop에서 사용

## 🔍 추론된 컨텍스트```

- 서비스 타입: api"이 GitHub 저장소를 분석해줘: https://github.com/fastapi/fastapi"

- 예상 사용자: 10,000명

- CPU: 8.0 코어"https://github.com/openai/whisper 프로젝트의 리소스 예측 부탁해"

- 메모리: 16,384 MB```



## 📈 24시간 예측## 🛠️ 테스트

- Flavor: large

- 비용: $5.50 / day```bash

```# 서버 직접 실행 (디버그 모드)

python server.py

---

# 그리고 stdin으로 입력:

## 트러블슈팅# {"jsonrpc":"2.0","id":1,"method":"tools/list"}

```

### MCP Core 연결 실패

```bash## 🔍 동작 방식

python -m uvicorn app.main:app --port 8000

``````

Claude Desktop

### GitHub Rate Limit    ↓ (MCP 프로토콜)

`.env`에 `GITHUB_TOKEN` 추가MCP Analyzer Server (server.py)

    ↓ (GitHub API)

---GitHub Repository 분석

    ↓ (MCPContext 생성)

**버전**: 1.0.0MCP Core API (localhost:8000/plans)

    ↓ (예측 실행)
LSTM/Baseline Predictor
    ↓ (결과 반환)
Claude Desktop에 표시
```

## 📊 기능

- **analyze-github-repo**: GitHub 저장소 분석 및 리소스 예측
  - 저장소 정보 수집 (언어, Stars, Forks 등)
  - 서비스 타입 자동 감지 (web/api/worker/data)
  - 예상 사용자 수 추정
  - 24시간 리소스 사용량 예측
  - 권장 인스턴스 타입 및 비용 산출

## 🔐 GitHub Token 발급

1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. 권한: `public_repo` (공개 저장소만) 또는 `repo` (전체)
4. 토큰 복사 → 환경 변수 설정

## ⚠️ 문제 해결

### "MCP Core API 호출 실패"
- MCP Core 서버가 실행 중인지 확인
- `http://localhost:8000/health` 접속 테스트
- `MCP_CORE_URL` 환경 변수 확인

### "GitHub API 오류"
- 저장소 URL 형식 확인
- GitHub Token 설정 (rate limit 회피)
- 비공개 저장소는 적절한 권한 필요

### "Claude Desktop에 나타나지 않음"
- `claude_desktop_config.json` 경로 확인
- Python 경로가 절대 경로인지 확인
- Claude Desktop 재시작

## 📚 참고

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP](https://modelcontextprotocol.io/)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
