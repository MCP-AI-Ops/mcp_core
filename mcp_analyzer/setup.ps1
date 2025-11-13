# GitHub MCP Server 설정
# Claude Desktop에 간단한 GitHub 분석 서버를 등록합니다

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  GitHub MCP Server 자동 설정" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Python 경로
$pythonPath = "C:\Users\wjdwl\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python).Source
}
Write-Host "✓ Python: $pythonPath" -ForegroundColor Green

# 서버 스크립트
$serverPath = Join-Path $PSScriptRoot "server.py"
Write-Host "✓ Server: $serverPath" -ForegroundColor Green

# MCP Core URL
$mcpCoreUrl = "http://localhost:8000"
Write-Host "✓ MCP Core: $mcpCoreUrl" -ForegroundColor Green

# GitHub Token (선택)
Write-Host "`n⚠️  GitHub Token을 입력하세요 (선택, Enter=건너뛰기):" -ForegroundColor Yellow
$githubToken = Read-Host "   Token (ghp_...)"

# 설정 생성
$envConfig = @{
    "MCP_CORE_URL" = $mcpCoreUrl
}

if (-not [string]::IsNullOrWhiteSpace($githubToken)) {
    $envConfig["GITHUB_TOKEN"] = $githubToken
    Write-Host "✓ Token 설정됨" -ForegroundColor Green
} else {
    Write-Host "⚠️  Token 없이 진행 (Rate Limit 60회/시간)" -ForegroundColor Yellow
}

$config = @{
    mcpServers = @{
        "github-analyzer" = @{
            command = $pythonPath
            args = @($serverPath)
            env = $envConfig
        }
    }
} | ConvertTo-Json -Depth 10

# Claude Desktop 설정 파일에 저장
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($configPath, $config, $utf8)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  ✅ 설정 완료!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "📁 설정 파일: $configPath`n" -ForegroundColor Cyan

Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "1. MCP Core 시작:" -ForegroundColor White
Write-Host "   python -m uvicorn app.main:app --port 8000`n" -ForegroundColor Gray

Write-Host "2. Claude Desktop 재시작`n" -ForegroundColor White

Write-Host "3. Claude에게 요청:" -ForegroundColor White
Write-Host '   "GitHub 저장소 https://github.com/fastapi/fastapi 분석해줘"' -ForegroundColor Gray
Write-Host "`n========================================`n" -ForegroundColor Cyan
