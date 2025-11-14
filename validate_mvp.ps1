#!/usr/bin/env pwsh
# MVP 배포 전 검증 스크립트 (PowerShell)
# 사용법: .\validate_mvp.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== MCP Core MVP 배포 전 검증 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 필수 모델 파일 확인
Write-Host "[1/6] 모델 파일 확인..." -ForegroundColor Yellow
$modelFiles = @(
    "models/best_mcp_lstm_model.h5",
    "models/mcp_model_metadata.pkl"
)

$missingModels = @()
foreach ($file in $modelFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length / 1MB
        Write-Host "  ✓ $file ($([Math]::Round($size, 2)) MB)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (없음)" -ForegroundColor Red
        $missingModels += $file
    }
}

if ($missingModels.Count -gt 0) {
    Write-Host "`n필수 모델 파일이 누락되었습니다!" -ForegroundColor Red
    Write-Host "   다음 파일을 준비해주세요:" -ForegroundColor Yellow
    foreach ($file in $missingModels) {
        Write-Host "   - $file"
    }
    Write-Host "`n   자세한 내용: models/README.md 참고" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# 2. .env 파일 확인
Write-Host "`n[2/6] 환경 변수 파일 확인..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ .env 파일 존재" -ForegroundColor Green
    
    # 중요 변수 확인
    $envContent = Get-Content .env -Raw
    $warnings = @()
    
    if ($envContent -notmatch "DATABASE_URL=") {
        $warnings += "DATABASE_URL"
    }
    if ($envContent -match "DISCORD_WEBHOOK_URL=$" -or $envContent -match "DISCORD_WEBHOOK_URL=\s*$") {
        $warnings += "DISCORD_WEBHOOK_URL (선택적, 이상 알림 비활성화)"
    }
    if ($envContent -match "GITHUB_TOKEN=$" -or $envContent -match "GITHUB_TOKEN=\s*$") {
        $warnings += "GITHUB_TOKEN (선택적, Rate Limit 주의)"
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "  다음 환경 변수가 비어있습니다:" -ForegroundColor Yellow
        foreach ($var in $warnings) {
            Write-Host "     - $var"
        }
    }
} else {
    Write-Host "  ✗ .env 파일이 없습니다" -ForegroundColor Red
    Write-Host "     실행: copy .env.example .env" -ForegroundColor Yellow
    exit 1
}

# 3. Docker 확인
Write-Host "`n[3/6] Docker 설치 확인..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    Write-Host "  ✓ $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker를 찾을 수 없습니다" -ForegroundColor Red
    Write-Host "     설치: https://docs.docker.com/get-docker/" -ForegroundColor Yellow
    exit 1
}

# 4. Docker Compose 확인
Write-Host "`n[4/6] Docker Compose 확인..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version 2>$null
    Write-Host "  ✓ $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker Compose를 찾을 수 없습니다" -ForegroundColor Red
    exit 1
}

# 5. 포트 사용 확인
Write-Host "`n[5/6] 포트 충돌 확인..." -ForegroundColor Yellow
$ports = @(3308, 8000, 8001)
$usedPorts = @()

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  ✗ 포트 $port 이미 사용 중" -ForegroundColor Red
        $usedPorts += $port
    } else {
        Write-Host "  ✓ 포트 $port 사용 가능" -ForegroundColor Green
    }
}

if ($usedPorts.Count -gt 0) {
    Write-Host "`n다음 포트가 이미 사용 중입니다:" -ForegroundColor Yellow
    foreach ($port in $usedPorts) {
        Write-Host "   - $port"
    }
    Write-Host "`n   기존 프로세스 종료 또는 docker-compose.yml에서 포트 변경 필요" -ForegroundColor Cyan
}

# 6. 데이터 파일 확인
Write-Host "`n[6/6] 데이터 파일 확인..." -ForegroundColor Yellow
if (Test-Path "data/lstm_ready_cluster_data.csv") {
    $size = (Get-Item "data/lstm_ready_cluster_data.csv").Length / 1MB
    Write-Host "  ✓ data/lstm_ready_cluster_data.csv ($([Math]::Round($size, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "  ✗ data/lstm_ready_cluster_data.csv (없음)" -ForegroundColor Red
    Write-Host "     LSTM 예측이 작동하지 않습니다 (Baseline으로 폴백)" -ForegroundColor Yellow
}

# 최종 요약
Write-Host "`n=== 검증 완료 ===" -ForegroundColor Cyan

if ($missingModels.Count -eq 0 -and (Test-Path ".env")) {
    Write-Host "`nMVP 배포 준비가 완료되었습니다!" -ForegroundColor Green
    Write-Host ""
    Write-Host "다음 명령으로 시작하세요:" -ForegroundColor Cyan
    Write-Host "  docker-compose up -d --build" -ForegroundColor White
    Write-Host ""
    Write-Host "헬스 체크:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:8001/health" -ForegroundColor White
    Write-Host "  curl http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "`n일부 문제를 해결 후 다시 시도하세요" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
