#!/usr/bin/env python3
"""
Simple GitHub to MCP Core Converter
GitHub URL을 MCPContext로 변환하여 MCP Core /plans API에 전달하는 간단한 MCP 서버

역할:
- GitHub URL 입력 받기
- 저장소 메타데이터 분석
- MCPContext 생성
- MCP Core /plans API 호출 및 결과 반환

실제 예측/정책/이상탐지/알림은 MCP Core가 수행
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("github-mcp")

# 환경변수
MCP_CORE_URL = os.getenv("MCP_CORE_URL", "http://localhost:8000")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# MCP Server
app = Server("github-mcp")


async def fetch_github_repo(github_url: str) -> dict[str, Any]:
    """GitHub 저장소 정보 가져오기"""
    # URL 파싱
    parts = github_url.rstrip('/').split('/')
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")
    
    owner = parts[-2]
    repo = parts[-1]
    
    # GitHub API 호출
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers, timeout=10.0)
        
        if response.status_code == 404:
            raise ValueError(f"Repository not found: {owner}/{repo}")
        elif response.status_code != 200:
            raise ValueError(f"GitHub API error: {response.status_code}")
        
        data = response.json()
    
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description", ""),
        "language": data.get("language", "Unknown"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "size": data.get("size", 0),
        "topics": data.get("topics", []),
    }


def infer_service_type(repo_data: dict) -> str:
    """서비스 타입 추론"""
    language = (repo_data.get("language") or "").lower()
    topics = [t.lower() for t in repo_data.get("topics", [])]
    desc = (repo_data.get("description") or "").lower()
    
    # 키워드 기반
    if any(k in topics or k in desc for k in ["api", "backend", "rest"]):
        return "api"
    elif any(k in topics or k in desc for k in ["frontend", "react", "vue"]):
        return "web"
    elif any(k in topics or k in desc for k in ["database", "sql", "redis"]):
        return "data"
    elif any(k in topics or k in desc for k in ["worker", "queue", "batch"]):
        return "worker"
    
    # 언어 기반
    if language in ["javascript", "typescript", "html"]:
        return "web"
    elif language in ["python", "java", "go"]:
        return "api"
    
    return "web"


def estimate_resources(repo_data: dict) -> tuple[float, float, int]:
    """리소스 추정 (CPU, Memory MB, Users)"""
    stars = repo_data.get("stars", 0)
    
    if stars < 100:
        return 1.0, 2048, 100
    elif stars < 1000:
        return 2.0, 4096, 1000
    elif stars < 10000:
        return 4.0, 8192, 5000
    else:
        return 8.0, 16384, 10000


def create_mcp_context(repo_data: dict, github_url: str) -> dict[str, Any]:
    """MCPContext 생성"""
    service_type = infer_service_type(repo_data)
    cpu, memory, users = estimate_resources(repo_data)
    
    context_id = f"{repo_data['full_name']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "context_id": context_id,
        "timestamp": datetime.utcnow().isoformat(),
        "service_type": service_type,
        "runtime_env": "prod",
        "time_slot": "normal",
        "weight": 1.0,
        "region": None,
        "expected_users": users,
        "curr_cpu": cpu,
        "curr_mem": memory,
        "github_url": github_url,
    }


async def call_mcp_core(mcp_context: dict) -> dict[str, Any]:
    """MCP Core /plans API 호출"""
    url = f"{MCP_CORE_URL}/plans"
    
    request_body = {
        "github_url": mcp_context.get("github_url", "unknown"),
        "metric_name": "total_events",
        "context": mcp_context
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=request_body, timeout=30.0)
            
            if response.status_code != 200:
                raise ValueError(f"MCP Core error: {response.status_code}")
            
            return response.json()
        
        except httpx.ConnectError:
            raise ConnectionError(
                f"MCP Core 연결 실패: {MCP_CORE_URL}\n"
                "MCP Core 서버가 실행 중인지 확인하세요."
            )


@app.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 도구"""
    return [
        Tool(
            name="analyze_github_repo",
            description=(
                "GitHub 저장소를 분석하고 리소스 예측을 받습니다.\n\n"
                "워크플로우:\n"
                "1. GitHub 저장소 메타데이터 수집\n"
                "2. 서비스 타입/리소스 추정\n"
                "3. MCPContext 생성\n"
                "4. MCP Core /plans 호출\n"
                "5. 24시간 예측 결과 반환\n\n"
                "입력: GitHub URL (예: https://github.com/fastapi/fastapi)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "github_url": {
                        "type": "string",
                        "description": "GitHub 저장소 URL"
                    }
                },
                "required": ["github_url"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """도구 실행"""
    
    if name != "analyze_github_repo":
        raise ValueError(f"Unknown tool: {name}")
    
    github_url = arguments.get("github_url")
    if not github_url:
        raise ValueError("github_url is required")
    
    try:
        logger.info(f"분석 시작: {github_url}")
        
        # 1. GitHub 분석
        repo_data = await fetch_github_repo(github_url)
        logger.info(f"저장소: {repo_data['full_name']}")
        
        # 2. MCPContext 생성
        mcp_context = create_mcp_context(repo_data, github_url)
        logger.info(f"컨텍스트 생성: {mcp_context['service_type']}, {mcp_context['expected_users']}명")
        
        # 3. MCP Core 호출
        result = await call_mcp_core(mcp_context)
        logger.info("예측 완료")
        
        # 4. 결과 포매팅
        output = f"""# 🎯 GitHub 저장소 분석 결과

## 📦 저장소 정보
- **이름**: {repo_data['full_name']}
- **설명**: {repo_data['description'] or 'N/A'}
- **언어**: {repo_data['language']}
- **스타**: ⭐ {repo_data['stars']:,}
- **포크**: 🍴 {repo_data['forks']:,}

## 🔍 추론된 컨텍스트
- **서비스 타입**: `{mcp_context['service_type']}`
- **예상 사용자**: {mcp_context['expected_users']:,}명
- **CPU**: {mcp_context['curr_cpu']} 코어
- **메모리**: {mcp_context['curr_mem']:,} MB

## 📈 24시간 예측

### 추천 인스턴스
- **Flavor**: `{result.get('recommended_flavor', 'N/A')}`
- **예상 비용**: ${result.get('expected_cost_per_day', 0):.2f} / day

### 예측 데이터
```json
{json.dumps(result.get('prediction', {}).get('predictions', [])[:6], indent=2, ensure_ascii=False)}
... (총 24개 포인트)
```

### 참고사항
{result.get('notes', 'N/A')}

---
**MCP Core가 LSTM/Baseline 예측, 정책 적용, 이상 탐지를 수행했습니다.**
"""
        
        return [TextContent(type="text", text=output)]
    
    except ValueError as e:
        logger.error(f"입력 오류: {e}")
        return [TextContent(type="text", text=f"❌ 오류: {str(e)}")]
    
    except ConnectionError as e:
        logger.error(f"연결 오류: {e}")
        return [TextContent(type="text", text=f"❌ MCP Core 연결 실패:\n{str(e)}")]
    
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ 오류:\n{str(e)}")]


async def main():
    """MCP Server 실행"""
    logger.info("=" * 50)
    logger.info("🚀 GitHub MCP Server 시작")
    logger.info(f"🔗 MCP Core: {MCP_CORE_URL}")
    logger.info(f"🔑 GitHub Token: {'설정됨' if GITHUB_TOKEN else '미설정'}")
    logger.info("=" * 50)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
