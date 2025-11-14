# GitHub MCP Server ?ㅼ젙
# Claude Desktop??媛꾨떒??GitHub 遺꾩꽍 ?쒕쾭瑜??깅줉?⑸땲??

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  GitHub MCP Server ?먮룞 ?ㅼ젙" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Python 寃쎈줈
$pythonPath = "C:\Users\wjdwl\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python).Source
}
Write-Host "??Python: $pythonPath" -ForegroundColor Green

# ?쒕쾭 ?ㅽ겕由쏀듃
$serverPath = Join-Path $PSScriptRoot "server.py"
Write-Host "??Server: $serverPath" -ForegroundColor Green

# MCP Core URL
$mcpCoreUrl = "http://localhost:8000"
Write-Host "??MCP Core: $mcpCoreUrl" -ForegroundColor Green

# GitHub Token (?좏깮)
Write-Host "`n?좑툘  GitHub Token???낅젰?섏꽭??(?좏깮, Enter=嫄대꼫?곌린):" -ForegroundColor Yellow
$githubToken = Read-Host "   Token (ghp_...)"

# ?ㅼ젙 ?앹꽦
$envConfig = @{
    "MCP_CORE_URL" = $mcpCoreUrl
}

if (-not [string]::IsNullOrWhiteSpace($githubToken)) {
    $envConfig["GITHUB_TOKEN"] = $githubToken
    Write-Host "??Token ?ㅼ젙?? -ForegroundColor Green
} else {
    Write-Host "?좑툘  Token ?놁씠 吏꾪뻾 (Rate Limit 60???쒓컙)" -ForegroundColor Yellow
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

# Claude Desktop ?ㅼ젙 ?뚯씪?????
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($configPath, $config, $utf8)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  ???ㅼ젙 ?꾨즺!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "?뱚 ?ㅼ젙 ?뚯씪: $configPath`n" -ForegroundColor Cyan

Write-Host "?ㅼ쓬 ?④퀎:" -ForegroundColor Yellow
Write-Host "1. MCP Core ?쒖옉:" -ForegroundColor White
Write-Host "   python -m uvicorn app.main:app --port 8000`n" -ForegroundColor Gray

Write-Host "2. Claude Desktop ?ъ떆??n" -ForegroundColor White

Write-Host "3. Claude?먭쾶 ?붿껌:" -ForegroundColor White
Write-Host '   "GitHub ??μ냼 https://github.com/fastapi/fastapi 遺꾩꽍?댁쨾"' -ForegroundColor Gray
Write-Host "`n========================================`n" -ForegroundColor Cyan

