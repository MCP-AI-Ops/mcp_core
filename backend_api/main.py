"""
Backend API Gateway - 프론트엔드와 MCP Core 사이의 중간 레이어

역할:
1. 프론트엔드로부터 GitHub URL 수신
2. MCP Analyzer 로직을 직접 실행 (GitHub 분석)
3. MCP Core /plans 호출
4. 결과를 프론트엔드에 반환

완전 자동화: 프론트엔드는 URL만 보내면 모든 분석/예측 자동 실행
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import os
import logging

from backend_api.services.github_analyzer import GitHubAnalyzer
from backend_api.services.mcp_core_client import MCPCoreClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Backend API",
    description="프론트엔드 → 백엔드 → MCP Core 자동화 파이프라인",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 실제 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
github_analyzer = GitHubAnalyzer(
    github_token=os.getenv("GITHUB_TOKEN")
)
mcp_core_client = MCPCoreClient(
    base_url=os.getenv("MCP_CORE_URL", "http://localhost:8000")
)


class AnalyzeRequest(BaseModel):
    """프론트엔드 요청 스키마"""
    github_url: str = Field(..., description="GitHub 저장소 URL")
    runtime_env: str = Field("prod", description="실행 환경 (prod/dev)")


class AnalyzeResponse(BaseModel):
    """프론트엔드 응답 스키마"""
    success: bool
    repository: Dict[str, Any]
    predictions: Dict[str, Any]
    recommendations: Dict[str, Any]
    cost_estimate: Dict[str, Any]
    message: Optional[str] = None


@app.get("/health")
async def health_check():
    """헬스 체크"""
    mcp_core_health = mcp_core_client.health_check()
    
    return {
        "status": "healthy",
        "service": "backend-api",
        "mcp_core": mcp_core_health.get("status", "unknown")
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_repository(request: AnalyzeRequest):
    """
    🚀 자동화된 저장소 분석 엔드포인트
    
    워크플로우:
    1. GitHub URL 파싱 및 검증
    2. GitHub API로 메타데이터 자동 수집
    3. 서비스 타입/사용자/리소스 자동 추정
    4. MCPContext 자동 생성
    5. MCP Core /plans 호출
    6. 예측 결과 포매팅 및 반환
    
    사용자는 GitHub URL만 제공하면 모든 과정이 자동 실행됩니다.
    """
    try:
        logger.info(f"분석 시작: {request.github_url}")
        
        # 1단계: GitHub 저장소 자동 분석
        logger.info("GitHub 메타데이터 수집 중...")
        repo_analysis = github_analyzer.analyze_repository(request.github_url)
        
        # 2단계: MCPContext 자동 생성 (GitHub 원본 /plans 계약 준수)
        logger.info("MCPContext 생성 중...")
        
        # GitHub 원본 계약: context_id, timestamp는 필수
        # github_url은 선택적 (향후 확장용)
        context_id = f"{repo_analysis['full_name']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        mcp_context = {
            "context_id": context_id,
            "timestamp": datetime.utcnow().isoformat(),
            "service_type": repo_analysis["service_type"],
            "runtime_env": request.runtime_env,
            "time_slot": repo_analysis["time_slot"],
            "weight": 1.0,
            "region": None,
            "expected_users": repo_analysis["estimated_users"],
            "curr_cpu": float(repo_analysis["resources"]["cpu"]),
            "curr_mem": float(repo_analysis["resources"]["memory"]),
        }
        
        # 3단계: MCP Core /plans 자동 호출
        logger.info("MCP Core 예측 요청 중...")
        plans_request = {
            "github_url": repo_analysis["full_name"],
            "metric_name": "total_events",
            "context": mcp_context
        }
        
        prediction_result = mcp_core_client.request_plans(plans_request)
        
        # 4단계: 응답 포매팅
        logger.info("결과 포매팅 중...")
        response = AnalyzeResponse(
            success=True,
            repository={
                "name": repo_analysis["name"],
                "full_name": repo_analysis["full_name"],
                "description": repo_analysis["description"],
                "stars": repo_analysis["stars"],
                "forks": repo_analysis["forks"],
                "language": repo_analysis["language"],
                "service_type": repo_analysis["service_type"],
                "estimated_users": repo_analysis["estimated_users"],
            },
            predictions={
                "24h_forecast": prediction_result["prediction"]["predictions"],
                "is_anomaly": prediction_result["prediction"].get("is_anomaly", False),
                "anomaly_score": prediction_result["prediction"].get("anomaly_score"),
                "model_version": prediction_result["prediction"].get("model_version", "unknown"),
            },
            recommendations={
                "instance_type": prediction_result["recommended_flavor"],
                "cpu": repo_analysis["resources"]["cpu"],
                "memory_mb": repo_analysis["resources"]["memory"],
            },
            cost_estimate={
                "daily_usd": prediction_result["expected_cost_per_day"],
                "monthly_usd": prediction_result["expected_cost_per_day"] * 30,
                "currency": "USD"
            },
            message="분석 완료"
        )
        
        logger.info(f"분석 완료: {repo_analysis['full_name']}")
        return response
        
    except ValueError as e:
        logger.error(f"입력 오류: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except ConnectionError as e:
        logger.error(f"MCP Core 연결 실패: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"MCP Core 서버에 연결할 수 없습니다: {e}"
        )
    
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"내부 서버 오류: {str(e)}"
        )


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "MCP Backend API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/api/analyze",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("BACKEND_PORT", "8001"))
    
    print("=" * 60)
    print("🚀 MCP Backend API 시작")
    print("=" * 60)
    print(f"📍 서버: http://localhost:{port}")
    print(f"📚 문서: http://localhost:{port}/docs")
    print(f"🔗 MCP Core: {os.getenv('MCP_CORE_URL', 'http://localhost:8000')}")
    print("=" * 60)
    print("\n사용법:")
    print("  POST /api/analyze")
    print('  {"github_url": "https://github.com/user/repo"}')
    print("\n→ 자동 분석 → 예측 → 추천 🎯")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
