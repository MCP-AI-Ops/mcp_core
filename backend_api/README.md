# Backend API - 완전 자동화

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Claude](https://img.shields.io/badge/Claude-3.5%20Sonnet-orange.svg)](https://www.anthropic.com/)

프론트엔드 자연어 입력을 Claude API로 자동 변환하여 MCP Core에 전달하는 완전 자동화 Backend API

## 📋 목차

- [개요](#개요)
- [아키텍처](#아키텍처)
- [설치](#설치)
- [사용법](#사용법)
- [API 문서](#api-문서)
- [예제](#예제)
- [트러블슈팅](#트러블슈팅)

## 개요

### 주요 기능

- 🤖 **Claude AI 통합**: 자연어를 CPU/Memory/Users로 자동 변환
- 🔄 **완전 자동화**: GitHub URL + 자연어 입력만으로 예측 수행
- 📊 **LSTM 예측**: MCP Core와 연동하여 리소스 예측
- 🚨 **이상 탐지**: 자동 이상 탐지 및 Discord 알림
- 🌐 **CORS 지원**: 모든 오리진에서 접근 가능

### 처리 흐름

```
프론트엔드
  ↓
  ├─ GitHub URL: https://github.com/owner/repo
  └─ 자연어: "피크타임에 1000명 정도 사용할 것 같아요"
  ↓
Backend API (이 서버)
  ↓
  ├─ 1. GitHub API → 저장소 메타데이터 수집
  ├─ 2. Claude API → CPU/Memory/Users 추출
  ├─ 3. MCPContext 생성
  └─ 4. MCP Core /plans 호출
  ↓
MCP Core
  ↓
  ├─ LSTM/Baseline 예측
  ├─ Flavor 권장
  ├─ 이상 탐지
  └─ Discord 알림 (이상 발견 시)
  ↓
Backend API → 프론트엔드로 결과 반환
```

## 아키텍처

```
┌─────────────────┐
│   Frontend      │
│  (React/Vue)    │
└────────┬────────┘
         │ POST /api/predict
         │ {github_url, user_input}
         ↓
┌─────────────────┐
│  Backend API    │  ← 이 서버
│   (FastAPI)     │
├─────────────────┤
│ - GitHub API    │  저장소 정보 수집
│ - Claude API    │  자연어 → JSON
│ - MCP Core API  │  예측 요청
└────────┬────────┘
         │ POST /plans
         │ {context, metric_name}
         ↓
┌─────────────────┐
│   MCP Core      │
│  (LSTM Model)   │
├─────────────────┤
│ - LSTM 예측     │
│ - 이상 탐지     │
│ - Discord 알림  │
### 시나리오 2: 개발 환경 소규모

**입력:**
```json
{
  "github_url": "https://github.com/nodejs/node",
  "user_input": "개발 환경에서 테스트, 50명 정도면 될 것 같아요"
}
```

**Claude가 자동 추출:**
```json
{
  "service_type": "web",
  "expected_users": 50,
  "time_slot": "normal",
  "runtime_env": "dev",
  "curr_cpu": 1.0,
  "curr_mem": 2048.0,
  "reasoning": "개발환경 50명 → 1 CPU, 2GB 충분"
}
```

### 시나리오 3: 주말 트래픽

**입력:**
```json
{
  "github_url": "https://github.com/django/django",
  "user_input": "주말에는 1000명 정도 예상됩니다"
}
```

**Claude가 자동 추출:**
```json
{
  "service_type": "web",
  "expected_users": 1000,
  "time_slot": "weekend",
  "runtime_env": "prod",
  "curr_cpu": 2.0,
  "curr_mem": 4096.0,
  "reasoning": "주말 1000명 → 2 CPU, 4GB"
}
```

## 트러블슈팅

### Claude API 키가 없을 때

**증상:**
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

### MCP Core 연결 실패

**증상:**
```json
{
  "detail": "MCP Core error: 500"
}
```

**해결:**
1. MCP Core 서버 실행 확인:
   ```bash
   curl http://localhost:8000/health
   ```
2. `.env`에서 `MCP_CORE_URL` 확인
3. MCP Core 로그 확인

### GitHub API Rate Limit

**증상:**
```json
{
  "detail": "GitHub API error: 403"
}
```

**해결:**
1. `.env`에 `GITHUB_TOKEN` 설정
2. [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)에서 토큰 생성
3. 권한: `public_repo` (공개 저장소만 접근 시)

### CORS 에러

**증상 (브라우저 콘솔):**
```
Access to fetch at 'http://localhost:8001/api/predict' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**해결:**
- 이 서버는 이미 모든 오리진 허용 (`allow_origins=["*"]`)
- 브라우저 캐시 삭제 후 재시도

### Python 패키지 없음

**증상:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**해결:**
```bash
pip install -r requirements.txt
```

## 환경변수 상세

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | ✅ | - | Claude API 키 |
| `MCP_CORE_URL` | ❌ | `http://localhost:8000` | MCP Core 서버 주소 |
| `GITHUB_TOKEN` | ❌ | - | GitHub API 토큰 (Rate Limit 완화) |
| `BACKEND_PORT` | ❌ | `8001` | Backend API 포트 |

## 성능 최적화

### Rate Limiting

GitHub API Rate Limit:
- **인증 없음**: 60회/시간
- **인증 있음**: 5000회/시간

→ `GITHUB_TOKEN` 설정 권장

### Timeout 설정

```python
# GitHub API: 10초
# Claude API: 30초
# MCP Core: 30초
```

### 캐싱

현재 캐싱 미구현. 추후 Redis 추가 예정.

## 라이센스

MIT License

## 기여

Pull Request 환영합니다!

## 문의

이슈: [GitHub Issues](https://github.com/your-repo/issues)

---

**Made with ❤️ by MCP Team**

## 설치

## 설치

### 1. 환경변수 설정

`.env` 파일 생성:

```bash
# 필수: Claude API 키
ANTHROPIC_API_KEY=sk-ant-api03-...

# 선택: MCP Core 서버 주소 (기본: http://localhost:8000)
MCP_CORE_URL=http://localhost:8000

# 선택: GitHub API 토큰 (Rate Limit 완화용)
GITHUB_TOKEN=ghp_...

# 선택: Backend API 포트 (기본: 8001)
BACKEND_PORT=8001
```

**Claude API 키 발급:**
1. [Anthropic Console](https://console.anthropic.com/) 접속
2. API Keys → Create Key
3. `.env` 파일에 `ANTHROPIC_API_KEY` 설정

### 2. 패키지 설치

```bash
cd backend_api
pip install -r requirements.txt
```

**필요한 패키지:**
- `fastapi`: Web 프레임워크
- `uvicorn`: ASGI 서버
- `httpx`: 비동기 HTTP 클라이언트
- `anthropic`: Claude API 클라이언트
- `pydantic`: 데이터 검증
- `python-dotenv`: 환경변수 로드

### 3. 서버 시작

**방법 1: 직접 실행**
```bash
python main.py
```

**방법 2: uvicorn 사용**
```bash
uvicorn main:app --reload --port 8001
```

**성공 시 출력:**
```
🚀 Backend API: http://localhost:8001
🤖 Claude: enabled
📡 MCP Core: http://localhost:8000
🔑 GitHub Token: configured

💡 Tip: Set ANTHROPIC_API_KEY in .env file
INFO:     Uvicorn running on http://0.0.0.0:8001
```

## 사용법

### 프론트엔드에서 호출

#### JavaScript (Fetch API)

```javascript
async function predictResources() {
  const response = await fetch('http://localhost:8001/api/predict', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      github_url: 'https://github.com/fastapi/fastapi',
      user_input: '피크타임에 5000명 예상됩니다. CPU는 많이 필요할 것 같아요.'
    })
  });
  
  const result = await response.json();
  console.log(result);
}
```

#### React Example

```jsx
import { useState } from 'react';

function PredictForm() {
  const [githubUrl, setGithubUrl] = useState('');
  const [userInput, setUserInput] = useState('');
  const [result, setResult] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const response = await fetch('http://localhost:8001/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        github_url: githubUrl,
        user_input: userInput
      })
    });
    
    const data = await response.json();
    setResult(data);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input 
        value={githubUrl}
        onChange={(e) => setGithubUrl(e.target.value)}
        placeholder="GitHub URL"
      />
      <textarea
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        placeholder="자연어 입력 (예: 피크타임에 1000명 사용)"
      />
      <button type="submit">예측</button>
      
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </form>
  );
}
```

#### Python Example

```python
import requests

response = requests.post('http://localhost:8001/api/predict', json={
    'github_url': 'https://github.com/fastapi/fastapi',
    'user_input': '피크타임에 5000명 정도 사용할 것 같습니다.'
})

print(response.json())
```

### cURL Example

```bash
curl -X POST http://localhost:8001/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/fastapi/fastapi",
    "user_input": "피크타임에 5000명 예상됩니다."
  }'
```

## API 문서

### POST /api/predict

완전 자동화 예측 엔드포인트

#### Request Body

```json
{
  "github_url": "string",    // GitHub 저장소 URL (필수)
  "user_input": "string"     // 자연어 요청사항 (필수)
}
```

**자연어 입력 예시:**
- "피크타임에 1000명 정도 사용할 것 같아요"
- "주말에 100명, CPU 2개면 될 것 같습니다"
- "개발 환경에서 테스트, 50명 정도"
- "프로덕션, 5000명 이상 예상"

#### Response

```json
{
  "success": true,
  "github_info": {
    "full_name": "owner/repo",
    "description": "저장소 설명",
    "language": "Python",
    "stars": 1234,
    "forks": 567
  },
  "extracted_context": {
    "service_type": "web",
    "expected_users": 5000,
    "time_slot": "peak",
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "reasoning": "5000명 사용자 → 4 CPU, 8192 MB 권장"
  },
  "predictions": {
    "lstm": {
      "cpu": 4.2,
      "memory": 8500.0
    },
    "baseline": {
      "cpu": 4.0,
      "memory": 8192.0
    }
  },
  "recommendations": {
    "flavor": "m5.xlarge",
    "cost_per_day": 4.32,
    "notes": "LSTM 모델 기반 권장"
  }
}
```

#### Error Response

```json
{
  "detail": "GitHub API error: 404"
}
```

### GET /health

서버 헬스 체크

#### Response

```json
{
  "status": "healthy",
  "claude_api": "enabled"
}
```

## 예제

### 시나리오 1: 피크타임 대량 사용자

**입력:**
```json
{
  "github_url": "https://github.com/facebook/react",
  "user_input": "피크타임에 10000명 이상 예상됩니다. 트래픽이 많을 것 같아요."
}
```

**Claude가 자동 추출:**
```json
{
  "service_type": "web",
  "expected_users": 10000,
  "time_slot": "peak",
  "runtime_env": "prod",
  "curr_cpu": 8.0,
  "curr_mem": 16384.0,
  "reasoning": "10000명+ → 8 CPU, 16GB 권장"
}
```

### 시나리오 2: 개발 환경 소규모

**입력:**

```json
{
  "success": true,
  "github_info": {
    "full_name": "fastapi/fastapi",
    "language": "Python",
    "stars": 78000
  },
  "extracted_context": {
    "service_type": "api",
    "expected_users": 5000,
    "time_slot": "peak",
    "curr_cpu": 4.0,
    "curr_mem": 8192.0,
    "reasoning": "명시적 사용자 수와 피크타임 지정"
  },
  "predictions": {
    "predictions": [...]
  },
  "recommendations": {
    "flavor": "medium",
    "cost_per_day": 2.8
  }
}
```

## 동작 원리

1. **GitHub 분석**: GitHub API로 저장소 메타데이터
2. **Claude 파싱**: 자연어 → CPU/Memory/Users 자동 추출
3. **MCPContext 생성**: /plans 형식으로 변환
4. **MCP Core 호출**: LSTM 예측, Flavor 추천, 이상 탐지
5. **결과 반환**: 프론트엔드에 JSON 응답

---

**포트**: 8001  
**문서**: http://localhost:8001/docs
