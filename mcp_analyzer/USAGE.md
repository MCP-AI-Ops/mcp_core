# Claude MCP GitHub Analyzer - 사용 가이드

## 개요

Claude Desktop에서 GitHub 저장소를 분석하고 리소스 요구사항을 자동으로 추정하는 MCP 도구입니다.

## 설치 및 설정

### 1. Claude Desktop 설정

설정은 이미 완료되었습니다:
- 경로: `%APPDATA%\Claude\claude_desktop_config.json`
- MCP Server: `server_production.py`

### 2. Claude Desktop 재시작

MCP 서버 변경사항을 적용하려면 Claude Desktop을 재시작하세요.

## 사용 방법

### 도구 1: `estimate-resources` (추천 ⭐)

**용도**: GitHub 저장소의 CPU/Memory만 빠르게 추정하고 `/plans` API 호출 형식 생성

**Claude Desktop에서 사용하는 방법**:

```
@github-analyzer https://github.com/fastapi/fastapi의 리소스를 추정해줘
```

또는

```
fastapi/fastapi 저장소의 CPU와 메모리 요구사항을 알려줘
```

**출력 예시**:

```
🎯 리소스 추정 완료

📦 저장소 정보
- 이름: fastapi/fastapi
- 언어: Python
- Stars: 91,825 ⭐
- Forks: 8,212 🔱

🔍 분석 결과
- 서비스 타입: api
- 추정 사용자: 16,909명
- 활성 시간대: peak

💻 추정 리소스
- CPU: 2 vCPU
- Memory: 4096 MB (4.0 GB)

📋 /plans API 호출 형식

### JSON Payload (복사용)
{
  "service_type": "api",
  "current_users": 16909,
  "time_slot": "peak",
  "cpu": 2,
  "memory": 4096
}
```

**주요 기능**:
1. ✅ GitHub 저장소 메타데이터 분석
2. ✅ 언어/규모/타입 기반 CPU/Memory 자동 추정
3. ✅ `/plans` API 호출 JSON 생성 (복사 가능)
4. ✅ cURL, Python 예제 코드 제공

### 도구 2: `analyze-github-repo` (전체 분석)

**용도**: 저장소 분석 + MCP Core API 호출 + 예측 결과까지 전체 프로세스

**Claude Desktop에서 사용하는 방법**:

```
@github-analyzer https://github.com/fastapi/fastapi를 완전 분석해줘
```

**출력 예시**:

```
🔍 GitHub 저장소 분석 완료

📦 저장소 정보
- 이름: fastapi/fastapi
- 추정 사용자: 16,909명

🤖 AI 예측 모델
- 모델: lstm_v1
- 서비스 타입: API

📊 24시간 리소스 예측
120.5, 115.2, 130.8, 145.3, 140.2, 125.7

💡 권장사항
- 인스턴스 타입: large
- 예상 일일 비용: $5.50
```

**주요 기능**:
1. ✅ 모든 `estimate-resources` 기능
2. ✅ MCP Core API 자동 호출
3. ✅ 24시간 리소스 예측
4. ✅ 이상 징후 감지
5. ✅ 비용 추정

**주의**: MCP Core 서버가 실행 중이어야 합니다!

## 리소스 추정 로직

### 1. 언어별 기본값

| 언어 | CPU | Memory |
|-----|-----|--------|
| Java, Scala, Kotlin | 4 vCPU | 8192 MB |
| C++, Rust, Go | 2-4 vCPU | 2048-4096 MB |
| Python, JavaScript, Ruby | 2 vCPU | 4096 MB |

### 2. 서비스 타입 조정

| 타입 | CPU 배율 | Memory 배율 |
|-----|---------|-------------|
| web | 1.0x | 1.5x |
| api | 1.2x | 1.0x |
| worker | 1.5x | 1.2x |
| data | 2.0x | 2.0x |

### 3. 규모별 스케일링

| Stars | CPU 배율 | Memory 배율 |
|-------|---------|-------------|
| > 50,000 | 4x (최대 16 CPU) | 4x (최대 32 GB) |
| > 10,000 | 2x (최대 8 CPU) | 2x (최대 16 GB) |
| > 1,000 | 1.5x | 1.5x |
| < 1,000 | 1.0x | 1.0x |

### 예시 계산

**fastapi/fastapi** (Python, API, 91k stars):
1. 기본값: 2 CPU, 4096 MB (Python)
2. 서비스 타입: 2 × 1.2 = 2.4 → 2 CPU (API)
3. 규모: 2 × 4 = 8 CPU, 4096 × 4 = 16384 MB (>50k stars)
4. **최종**: 8 CPU, 16384 MB (16 GB)

## 워크플로우

### 1. 빠른 리소스 확인

```
Claude Desktop:
"fastapi/fastapi의 리소스 요구사항 알려줘"

↓

estimate-resources 도구 실행

↓

JSON 복사

↓

/plans API 호출 또는 Gateway API 사용
```

### 2. 완전 자동화 (MCP Core 연동)

```
Claude Desktop:
"fastapi/fastapi를 분석하고 예측해줘"

↓

analyze-github-repo 도구 실행

↓

GitHub 분석 + CPU/Memory 추정 + /plans API 호출 + 예측

↓

결과 확인 (비용, 인스턴스 타입, 이상 징후 등)
```

## 자주 묻는 질문

### Q1: MCP Core 서버가 꺼져 있으면?

**A**: `estimate-resources` 도구를 사용하세요. MCP Core 없이 CPU/Memory만 추정합니다.

### Q2: GitHub API Rate Limit?

**A**: `GITHUB_TOKEN` 환경 변수를 설정하면 시간당 5000 요청으로 증가합니다.

```json
{
  "env": {
    "MCP_CORE_URL": "http://localhost:8000",
    "GITHUB_TOKEN": "ghp_your_token_here"
  }
}
```

### Q3: private 저장소는?

**A**: GITHUB_TOKEN이 해당 저장소 접근 권한이 있으면 가능합니다.

### Q4: /plans API 형식이 다른데?

**A**: MCP Core의 `/plans` 엔드포인트 스키마에 맞춰 수정하면 됩니다.

## 개발자를 위한 팁

### 1. 출력 JSON을 바로 복사

출력된 JSON Payload를 복사해서 다음과 같이 사용:

```bash
# cURL
curl -X POST http://localhost:8000/plans \
  -H "Content-Type: application/json" \
  -d '<복사한 JSON>'

# HTTPie
http POST :8000/plans < payload.json

# Postman
Body → raw → JSON → 붙여넣기
```

### 2. CI/CD 통합

GitHub Actions에서 자동화:

```yaml
- name: Estimate Resources
  run: |
    # Claude MCP 대신 Gateway API 사용
    curl -X POST http://gateway:8001/api/analyze-repo \
      -d '{"github_url": "${{ github.server_url }}/${{ github.repository }}"}'
```

### 3. 배치 처리

여러 저장소를 한 번에:

```
Claude:
"다음 저장소들의 리소스를 추정해줘:
1. fastapi/fastapi
2. django/django
3. pallets/flask"
```

## 트러블슈팅

### 문제: Claude Desktop에서 도구가 안 보여요

**해결**:
1. Claude Desktop 완전 종료 (작업 관리자에서 확인)
2. 재시작
3. 설정 파일 확인: `%APPDATA%\Claude\claude_desktop_config.json`

### 문제: "MCP Core 연결 실패"

**해결**:
1. MCP Core 서버 실행:
   ```bash
   cd C:\Users\wjdwl\mcp_core
   python -m uvicorn app.main:app --reload
   ```
2. 또는 `estimate-resources` 도구 사용 (MCP Core 불필요)

### 문제: GitHub API Rate Limit

**해결**:
1. GitHub Personal Access Token 생성
2. `claude_desktop_config.json`에 추가:
   ```json
   "env": {
     "GITHUB_TOKEN": "ghp_xxxxx"
   }
   ```
3. Claude Desktop 재시작

## 다음 단계

1. **Gateway API 사용**: 프론트엔드 통합을 위해 `gateway/` 사용
2. **MCP Core**: 예측 모델 학습 및 개선
3. **자동화**: CI/CD 파이프라인에 통합

---

📌 **요약**:
- `estimate-resources`: 빠른 CPU/Memory 추정 + JSON 생성
- `analyze-github-repo`: 전체 분석 + 예측 + 비용 추정
- 둘 다 Claude Desktop에서 자연어로 사용 가능!
