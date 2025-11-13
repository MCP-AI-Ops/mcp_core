# API Usage Guide

MCP Core 배포 후 상태 점검 및 주요 엔드포인트(`/api/analyze`, `/plans`)를 호출하는 방법을 정리했습니다. PowerShell과 curl 예제를 모두 제공합니다.

---

## 1. Health Checks

```bash
# Backend API (port 8001)
curl http://localhost:8001/health | jq

# MCP Core (port 8000)
curl http://localhost:8000/health | jq
```

PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/health" | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json
```

---

## 2. `/api/analyze` (Backend API)
Backend API는 GitHub 분석 + MCP Core `/plans` 호출까지 자동으로 수행합니다.

```bash
curl -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/fastapi/fastapi"}' | jq
```

PowerShell:
```powershell
$body = @{ github_url = "https://github.com/fastapi/fastapi" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/analyze" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

응답 예시(요약):
```json
{
  "success": true,
  "repository": {
    "full_name": "fastapi/fastapi",
    "service_type": "web",
    "estimated_users": 12483,
    "resources": { "cpu": 4, "memory": 8192 }
  },
  "predictions": {
    "model_version": "web_peak_lstm_v1",
    "24h_forecast": [...]
  },
  "recommendations": {
    "instance_type": "medium",
    "daily_usd": 2.8
  }
}
```

---

## 3. `/plans` 직접 호출
Backend API 없이 MCP Core를 바로 테스트하고 싶을 때 사용합니다.

```bash
curl -X POST http://localhost:8000/plans \
  -H "Content-Type: application/json" \
  -d '{
        "github_url": "demo-service",
        "metric_name": "total_events",
        "context": {
          "github_url": "https://github.com/owner/repo",
          "timestamp": "2025-11-13T12:00:00Z",
          "service_type": "web",
          "runtime_env": "prod",
          "time_slot": "peak",
          "weight": 1.0,
          "expected_users": 5000,
          "curr_cpu": 4,
          "curr_mem": 8192
        }
      }' | jq
```

응답 예시:
```json
{
  "prediction": {
    "model_version": "web_peak_lstm_v1",
    "predictions": [
      {"time": "2025-11-13T13:00:00Z", "value": 120.3},
      ...
    ]
  },
  "recommended_flavor": "medium",
  "expected_cost_per_day": 2.8,
  "notes": "(MVP) total_events peak=320.0, normalized=0.32",
  "generated_at": "2025-11-13T12:01:23.456Z"
}
```

---

## 4. 오류/예외 확인
### 잘못된 GitHub URL
```bash
curl -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://invalid-url"}' -w "\nHTTP Code: %{http_code}\n"
```
- 400 / 422 응답과 상세 메시지를 확인합니다.

### 존재하지 않는 리포지토리
```bash
curl -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/user/repo-not-exist"}'
```
- HTTP 404 및 오류 메시지를 반환합니다.

---

## 5. 성능 측정 (선택)
```bash
time curl -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/fastapi/fastapi"}' -o /dev/null -s
```
PowerShell:
```powershell
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Invoke-RestMethod -Uri "http://localhost:8001/api/analyze" -Method Post `
  -ContentType "application/json" `
  -Body (@{ github_url = "https://github.com/fastapi/fastapi" } | ConvertTo-Json) | Out-Null
$sw.Stop()
Write-Host "Elapsed: $($sw.ElapsedMilliseconds) ms"
```

---

## 6. Discord 알림 테스트
1. `.env`에 `DISCORD_WEBHOOK_URL` 입력 후 `docker-compose restart`.
2. 이상 감지 조건을 강제로 만들기 위해 `ANOMALY_Z`를 낮추거나 테스트 스크립트를 사용합니다.
   ```bash
   python tests/test_anomaly_discord.py   # MCP Core 실행 중이어야 함
   ```

---

## 7. 로그 & 모니터링
```bash
docker-compose logs -f backend
docker-compose logs -f app
```
에러가 발생하면 `/plans` 요청과 응답 JSON을 함께 캡처해 Issue에 첨부해 주세요.

---

### 참고 문서
- [`docs/deployment_guide.md`](./deployment_guide.md): 배포 절차 & 트러블슈팅
- [`docs/architecture.md`](./architecture.md): 내부 구조
- [`README.md`](../README.md): 프로젝트 개요 및 빠른 시작
