#!/usr/bin/env python3
"""
MCP GitHub Analyzer Server - Production Version

Claude Desktop과 통신하여:
1. GitHub 저장소를 분석
2. MCPContext를 생성
3. MCP Core의 /plans 엔드포인트 호출
4. 예측 결과 및 권장사항 반환
"""
import asyncio
import os
from datetime import datetime

import requests
from github import Github, GithubException
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.types as types
import mcp.server.stdio

# 환경 변수
MCP_CORE_URL = os.getenv("MCP_CORE_URL", "http://localhost:8000")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# MCP Server 초기화
server = Server("github-analyzer")


def detect_service_type(repo) -> str:
    """
    저장소 분석을 통한 서비스 타입 추론
    
    Returns:
        "web", "api", "worker", "data" 중 하나
    """
    languages = repo.get_languages()
    readme = ""
    
    try:
        readme_content = repo.get_readme()
        readme = readme_content.decoded_content.decode("utf-8").lower()
    except:
        pass
    
    # 키워드 기반 추론
    if any(keyword in readme for keyword in ["flask", "django", "fastapi", "express", "react", "vue", "next.js"]):
        return "web"
    elif any(keyword in readme for keyword in ["worker", "celery", "sidekiq", "queue", "background"]):
        return "worker"
    elif any(keyword in readme for keyword in ["data", "ml", "machine learning", "tensorflow", "pytorch", "spark"]):
        return "data"
    else:
        # 언어 기반 추론
        if "JavaScript" in languages or "TypeScript" in languages:
            return "web"
        elif "Python" in languages:
            return "api"
        else:
            return "api"


def detect_time_slot(repo) -> str:
    """최근 커밋 기반 활성 시간대 추론"""
    try:
        commits = repo.get_commits()
        latest_commit = commits[0]
        hour = latest_commit.commit.author.date.hour
        
        if 9 <= hour < 18:
            return "peak"
        elif 18 <= hour < 22:
            return "normal"
        elif hour >= 22 or hour < 6:
            return "low"
        else:
            return "weekend"
    except:
        return "peak"


def estimate_users(stars: int, forks: int) -> int:
    """Stars와 Forks 기반 예상 사용자 수"""
    return max(10, int((stars * 0.05 + forks * 1.5)))


def estimate_cpu_memory(repo, service_type: str, stars: int) -> dict:
    """
    GitHub 저장소 특성 기반 CPU/Memory 추정
    
    Args:
        repo: GitHub repository object
        service_type: 서비스 타입 (web/api/worker/data)
        stars: Star 개수
    
    Returns:
        {"cpu": int, "memory": int} (memory는 MB 단위)
    """
    # 1. 기본값 설정 (언어 기반)
    language = repo.language or "Unknown"
    base_cpu = 2
    base_memory = 4096  # MB
    
    # 언어별 기본 리소스
    language_resources = {
        "Java": {"cpu": 4, "memory": 8192},
        "Scala": {"cpu": 4, "memory": 8192},
        "Kotlin": {"cpu": 4, "memory": 8192},
        "C++": {"cpu": 4, "memory": 4096},
        "Rust": {"cpu": 2, "memory": 2048},
        "Go": {"cpu": 2, "memory": 2048},
        "Python": {"cpu": 2, "memory": 4096},
        "JavaScript": {"cpu": 2, "memory": 4096},
        "TypeScript": {"cpu": 2, "memory": 4096},
        "Ruby": {"cpu": 2, "memory": 4096},
        "PHP": {"cpu": 2, "memory": 4096},
    }
    
    if language in language_resources:
        base_cpu = language_resources[language]["cpu"]
        base_memory = language_resources[language]["memory"]
    
    # 2. 서비스 타입별 조정
    service_multipliers = {
        "web": {"cpu": 1.0, "memory": 1.5},      # 웹은 메모리 많이 필요
        "api": {"cpu": 1.2, "memory": 1.0},      # API는 CPU 약간 많이
        "worker": {"cpu": 1.5, "memory": 1.2},   # Worker는 CPU 많이 필요
        "data": {"cpu": 2.0, "memory": 2.0},     # 데이터 처리는 둘 다 많이
    }
    
    multiplier = service_multipliers.get(service_type, {"cpu": 1.0, "memory": 1.0})
    base_cpu = int(base_cpu * multiplier["cpu"])
    base_memory = int(base_memory * multiplier["memory"])
    
    # 3. 규모별 스케일링 (Stars 기반)
    if stars > 50000:  # 대형 프로젝트
        base_cpu = min(base_cpu * 4, 16)
        base_memory = min(base_memory * 4, 32768)
    elif stars > 10000:  # 중대형 프로젝트
        base_cpu = min(base_cpu * 2, 8)
        base_memory = min(base_memory * 2, 16384)
    elif stars > 1000:  # 중형 프로젝트
        base_cpu = int(base_cpu * 1.5)
        base_memory = int(base_memory * 1.5)
    
    return {
        "cpu": base_cpu,
        "memory": base_memory
    }


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    사용 가능한 도구 목록
    """
    return [
        types.Tool(
            name="analyze-github-repo",
            description="GitHub 저장소를 분석하고 AI 기반 리소스 예측 및 비용 추정 제공",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub 저장소 URL (예: https://github.com/owner/repo)"
                    },
                    "runtime_env": {
                        "type": "string",
                        "description": "실행 환경",
                        "enum": ["prod", "dev"],
                        "default": "prod"
                    }
                },
                "required": ["repo_url"]
            }
        ),
        types.Tool(
            name="estimate-resources",
            description="GitHub 저장소의 CPU/Memory 요구사항만 빠르게 추정하고 /plans API 형식으로 출력",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub 저장소 URL (예: https://github.com/owner/repo)"
                    }
                },
                "required": ["repo_url"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    도구 호출 처리
    """
    if name == "estimate-resources":
        return await handle_estimate_resources(arguments)
    elif name == "analyze-github-repo":
        return await handle_analyze_github_repo(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_estimate_resources(arguments: dict) -> list[types.TextContent]:
    """
    CPU/Memory 추정 및 /plans API 형식 출력
    """
    repo_url = arguments["repo_url"]
    
    try:
        # 1. GitHub 저장소 분석
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        
        # URL 파싱
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("❌ 잘못된 GitHub URL 형식입니다. 예: https://github.com/owner/repo")
        
        owner, repo_name = parts[-2], parts[-1]
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        # 2. 서비스 특성 분석
        service_type = detect_service_type(repo)
        time_slot = detect_time_slot(repo)
        estimated_users = estimate_users(repo.stargazers_count, repo.forks_count)
        
        # 3. CPU/Memory 추정
        resources = estimate_cpu_memory(repo, service_type, repo.stargazers_count)
        
        # 4. /plans API 형식으로 출력
        plans_payload = {
            "service_type": service_type,
            "current_users": estimated_users,
            "time_slot": time_slot,
            "cpu": resources["cpu"],
            "memory": resources["memory"]
        }
        
        output = f"""
🎯 **리소스 추정 완료**

## 📦 저장소 정보
- **이름**: `{repo.full_name}`
- **언어**: {repo.language or 'N/A'}
- **Stars**: {repo.stargazers_count:,} ⭐
- **Forks**: {repo.forks_count:,} 🔱

## 🔍 분석 결과
- **서비스 타입**: `{service_type}`
- **추정 사용자**: {estimated_users:,}명
- **활성 시간대**: `{time_slot}`

## 💻 추정 리소스
- **CPU**: **{resources['cpu']} vCPU**
- **Memory**: **{resources['memory']} MB** ({resources['memory'] / 1024:.1f} GB)

## 📋 /plans API 호출 형식

### cURL
```bash
curl -X POST http://localhost:8000/plans \\
  -H "Content-Type: application/json" \\
  -d '{{
  "service_type": "{service_type}",
  "current_users": {estimated_users},
  "time_slot": "{time_slot}",
  "cpu": {resources['cpu']},
  "memory": {resources['memory']}
}}'
```

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/plans",
    json={{
        "service_type": "{service_type}",
        "current_users": {estimated_users},
        "time_slot": "{time_slot}",
        "cpu": {resources['cpu']},
        "memory": {resources['memory']}
    }}
)
print(response.json())
```

### JSON Payload (복사용)
```json
{{
  "service_type": "{service_type}",
  "current_users": {estimated_users},
  "time_slot": "{time_slot}",
  "cpu": {resources['cpu']},
  "memory": {resources['memory']}
}}
```

---
💡 **추정 로직**:
- 언어별 기본값: Java/Scala (4 CPU, 8GB), Go/Rust (2 CPU, 2GB), Python/JS (2 CPU, 4GB)
- 서비스 타입 조정: web (+50% memory), api (+20% CPU), worker (+50% CPU), data (+100% both)
- 규모별 스케일: >50k stars (4x), >10k stars (2x), >1k stars (1.5x)
"""
        
        return [types.TextContent(type="text", text=output.strip())]
    
    except GithubException as e:
        error_msg = f"""
❌ **GitHub API 오류**

{str(e)}

**가능한 원인**:
- 저장소가 존재하지 않거나 비공개입니다
- GitHub API rate limit 초과 (60 req/h without token)

**해결 방법**:
- GITHUB_TOKEN 환경 변수를 설정하세요 (5000 req/h)
"""
        return [types.TextContent(type="text", text=error_msg)]
    
    except Exception as e:
        error_msg = f"""
❌ **예상치 못한 오류**

```
{type(e).__name__}: {str(e)}
```

저장소 URL을 확인하거나 관리자에게 문의하세요.
"""
        return [types.TextContent(type="text", text=error_msg)]


async def handle_analyze_github_repo(arguments: dict) -> list[types.TextContent]:
    """
    전체 GitHub 분석 및 예측 (기존 기능)
    """
    repo_url = arguments["repo_url"]
    runtime_env = arguments.get("runtime_env", "prod")
    
    try:
        # 1. GitHub 저장소 분석
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        
        # URL 파싱
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("❌ 잘못된 GitHub URL 형식입니다. 예: https://github.com/owner/repo")
        
        owner, repo_name = parts[-2], parts[-1]
        repo = g.get_repo(f"{owner}/{repo_name}")
        
        # 2. MCPContext 생성
        service_type = detect_service_type(repo)
        resources = estimate_cpu_memory(repo, service_type, repo.stargazers_count)
        context = {
            "github_url": f"github-{repo.id}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service_type": service_type,
            "runtime_env": runtime_env,
            "time_slot": detect_time_slot(repo),
            "weight": 1.0,
            "expected_users": estimate_users(repo.stargazers_count, repo.forks_count),
            "curr_cpu": resources["cpu"],
            "curr_mem": resources["memory"],
            "region": "us-east-1"
        }
        
        # 3. MCP Core API 호출
        response = requests.post(
            f"{MCP_CORE_URL}/plans",
            json={
                "github_url": repo.full_name,
                "metric_name": "total_events",
                "context": context
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 4. 결과 포매팅
        predictions = result["prediction"]["predictions"]
        
        # 6시간 샘플링
        sample_hours = [0, 4, 8, 12, 16, 20]
        sampled_preds = [predictions[i] for i in sample_hours if i < len(predictions)]
        pred_text = ", ".join([f"{p['value']:.2f}" for p in sampled_preds])
        
        # 이상 징후 확인
        anomaly_info = ""
        if result.get("anomaly_detected"):
            severity = result["anomaly_info"]["severity"]
            emoji = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
            anomaly_info = f"""
⚠️ **이상 징후 감지** {emoji}
- 심각도: {severity.upper()}
- Z-Score: {result['anomaly_info']['anomaly_score']:.2f}
- 상세: {result['anomaly_info']['detail']}
"""
        
        output = f"""
🔍 **GitHub 저장소 분석 완료**

## 📦 저장소 정보
- **이름**: {repo.full_name}
- **설명**: {repo.description or 'N/A'}
- **주 언어**: {repo.language or 'N/A'}
- **Stars**: {repo.stargazers_count:,} ⭐
- **Forks**: {repo.forks_count:,} 🔱
- **추정 사용자**: {context['expected_users']:,}명 👥

## 🤖 AI 예측 모델
- **모델**: {result['prediction']['model_version']}
- **서비스 타입**: {context['service_type'].upper()}
- **실행 환경**: {context['runtime_env'].upper()}
- **시간대**: {context['time_slot']}

## 📊 24시간 리소스 예측
**6시간 단위 샘플** (0h, 4h, 8h, 12h, 16h, 20h):
{pred_text}

*총 {len(predictions)}개 시간대 예측 완료*
{anomaly_info}
## 💡 권장사항
- **인스턴스 타입**: `{result['recommended_flavor']}`
- **예상 일일 비용**: **${result['expected_cost_per_day']:.2f}**

## 📝 추가 정보
{result.get('notes', 'N/A')}

---
*생성 시각: {result['generated_at']}*
*MCP Core: {MCP_CORE_URL}*
"""
        
        return [types.TextContent(type="text", text=output.strip())]
    
    except requests.exceptions.ConnectionError:
        error_msg = f"""
❌ **MCP Core 서버 연결 실패**

MCP Core 서버({MCP_CORE_URL})에 연결할 수 없습니다.

**해결 방법**:
1. MCP Core 서버 실행:
   ```bash
   cd {os.path.dirname(os.path.dirname(__file__))}
   python -m uvicorn app.main:app --reload
   ```

2. 환경 변수 확인:
   - MCP_CORE_URL이 올바른지 확인하세요
   - 현재 설정: {MCP_CORE_URL}
"""
        return [types.TextContent(type="text", text=error_msg)]
    
    except requests.exceptions.Timeout:
        error_msg = "❌ **요청 시간 초과**: MCP Core 서버가 응답하지 않습니다. 서버 상태를 확인하세요."
        return [types.TextContent(type="text", text=error_msg)]
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"❌ **MCP Core API 오류**: {e.response.status_code} - {e.response.text[:200]}"
        return [types.TextContent(type="text", text=error_msg)]
    
    except GithubException as e:
        error_msg = f"""
❌ **GitHub API 오류**

{str(e)}

**가능한 원인**:
- 저장소가 존재하지 않거나 비공개입니다
- GitHub API rate limit 초과 (60 req/h without token)

**해결 방법**:
- GITHUB_TOKEN 환경 변수를 설정하세요 (5000 req/h)
"""
        return [types.TextContent(type="text", text=error_msg)]
    
    except Exception as e:
        error_msg = f"""
❌ **예상치 못한 오류**

```
{type(e).__name__}: {str(e)}
```

저장소 URL을 확인하거나 관리자에게 문의하세요.
"""
        return [types.TextContent(type="text", text=error_msg)]


async def main():
    """MCP 서버 실행"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="github-analyzer",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
