"""
MCP Auto Backend API

완전 자동화된 Backend API 서버
프론트엔드에서 자연어 + GitHub URL을 받아 Claude API로 파싱하고 MCP Core에 전달

흐름:
1. 프론트엔드 → POST /api/predict (github_url, user_input)
2. GitHub API → 저장소 메타데이터 수집
3. Claude API → 자연어를 CPU/Memory/Users로 자동 변환
4. MCPContext 생성
5. MCP Core /plans → LSTM 예측 + 이상 탐지 + Discord 알림
6. 프론트엔드로 결과 반환

환경변수:
- ANTHROPIC_API_KEY: Claude API 키 (필수)
- MCP_CORE_URL: MCP Core 서버 주소 (기본: http://localhost:8000)
- GITHUB_TOKEN: GitHub API 토큰 (선택, Rate Limit 완화용)
- BACKEND_PORT: Backend API 포트 (기본: 8001)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
import httpx
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
# UTF-8 인코딩 문제 처리
try:
    load_dotenv(dotenv_path=env_path, encoding='utf-8')
except UnicodeDecodeError:
    load_dotenv(dotenv_path=env_path, encoding='cp949')  # Windows 기본 인코딩

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="MCP Auto Backend",
    description="자연어를 자동으로 MCPContext로 변환하는 Backend API",
    version="1.0.0"
)

# CORS 설정 - 모든 오리진 허용
DEFAULT_CORS_ORIGINS = ",".join([
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:3000",
    "https://launcha.cloud",
    "https://api.launcha.cloud",
])

_raw_origins = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

logging.info(f"CORS origins = {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경변수 로드
MCP_CORE_URL = os.getenv("MCP_CORE_URL", "http://localhost:8000")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


class PredictRequest(BaseModel):
    """
    예측 요청 모델
    
    Attributes:
        github_url (str): GitHub 저장소 URL (예: https://github.com/owner/repo)
        user_input (str): 자연어 요청사항 (예: "피크타임에 1000명 정도 사용할 것 같아요")
    """
    github_url: str
    user_input: str


def _normalize_claude_response(parsed: dict) -> dict:
    """
    Claude가 반환한 값을 검증하고 정규화합니다.
    
    특히 service_type이 "web|api" 같은 형식으로 오는 경우를 처리합니다.
    """
    # service_type 정규화
    if "service_type" in parsed:
        service_type = str(parsed["service_type"]).strip()
        # 파이프(|)로 구분된 경우 첫 번째 값 사용
        if "|" in service_type:
            service_type = service_type.split("|")[0].strip()
        # 유효한 값인지 확인하고, 아니면 기본값 사용
        valid_types = ["web", "api", "db"]
        if service_type.lower() not in valid_types:
            logger.warning(f"Invalid service_type '{service_type}', using 'web'")
            service_type = "web"
        parsed["service_type"] = service_type.lower()
    
    # time_slot 정규화
    if "time_slot" in parsed:
        time_slot = str(parsed["time_slot"]).strip()
        if "|" in time_slot:
            time_slot = time_slot.split("|")[0].strip()
        valid_slots = ["peak", "normal", "low", "weekend"]
        if time_slot.lower() not in valid_slots:
            logger.warning(f"Invalid time_slot '{time_slot}', using 'normal'")
            time_slot = "normal"
        parsed["time_slot"] = time_slot.lower()
    
    # runtime_env 정규화
    if "runtime_env" in parsed:
        runtime_env = str(parsed["runtime_env"]).strip()
        if "|" in runtime_env:
            runtime_env = runtime_env.split("|")[0].strip()
        valid_envs = ["prod", "dev"]
        if runtime_env.lower() not in valid_envs:
            logger.warning(f"Invalid runtime_env '{runtime_env}', using 'prod'")
            runtime_env = "prod"
        parsed["runtime_env"] = runtime_env.lower()
    
    # 숫자 타입 보장
    if "expected_users" in parsed:
        try:
            parsed["expected_users"] = int(parsed["expected_users"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid expected_users '{parsed.get('expected_users')}', using 1000")
            parsed["expected_users"] = 1000
    
    if "curr_cpu" in parsed:
        try:
            parsed["curr_cpu"] = float(parsed["curr_cpu"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid curr_cpu '{parsed.get('curr_cpu')}', using 2.0")
            parsed["curr_cpu"] = 2.0
    
    if "curr_mem" in parsed:
        try:
            parsed["curr_mem"] = float(parsed["curr_mem"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid curr_mem '{parsed.get('curr_mem')}', using 4096.0")
            parsed["curr_mem"] = 4096.0
    
    return parsed


async def parse_with_claude(user_input: str, github_data: dict) -> dict:
    """
    Claude API를 사용하여 자연어를 구조화된 데이터로 변환
    
    Args:
        user_input (str): 사용자의 자연어 입력
            예: "피크타임에 1000명 정도 사용할 것 같아요"
        github_data (dict): GitHub 저장소 정보
            - full_name: 저장소 전체 이름
            - language: 주 사용 언어
            - stars: 스타 개수
    
    Returns:
        dict: 추출된 컨텍스트 정보
            - service_type: 서비스 타입 (web/api/worker/data)
            - expected_users: 예상 사용자 수
            - time_slot: 시간대 (peak/normal/low/weekend)
            - runtime_env: 런타임 환경 (prod/dev)
            - curr_cpu: 현재 CPU (코어 수)
            - curr_mem: 현재 메모리 (MB)
            - reasoning: 추론 근거
    
    Note:
        - ANTHROPIC_API_KEY가 없으면 기본값 반환
        - Claude 3.5 Sonnet 모델 사용
        - CPU/Memory는 사용자 수에 따라 자동 추정
    """
    # API 키 없을 경우 기본값 반환
    if not ANTHROPIC_API_KEY:
        return {
            "service_type": "web",
            "expected_users": 1000,
            "time_slot": "normal",
            "runtime_env": "prod",
            "curr_cpu": 2.0,
            "curr_mem": 4096.0,
            "reasoning": "Claude API key not set"
        }
    
    # Claude에게 전달할 시스템 프롬프트 구성
    system_prompt = f"""GitHub repo:
- Name: {github_data.get("full_name")}
- Language: {github_data.get("language")}
- Stars: {github_data.get("stars")}

Convert to JSON (choose ONE value for each field):
{{
  "service_type": "web",
  "expected_users": 1000,
  "time_slot": "peak",
  "runtime_env": "prod",
  "curr_cpu": 2.0,
  "curr_mem": 4096.0,
  "service_type": "web",
  "expected_users": 1000,
  "time_slot": "peak",
  "runtime_env": "prod",
  "curr_cpu": 2.0,
  "curr_mem": 4096.0,
  "reasoning": "explanation"
}}

Rules:
- service_type: Choose ONE from ["web", "api", "db"]
  * web: for web applications, frontend services
  * api: for REST API, backend services
  * db: for database, data processing services
  
- time_slot: Choose ONE from ["peak", "normal", "low", "weekend"]
  
- runtime_env: Choose ONE from ["prod", "dev"]
  
- CPU/Memory defaults based on expected_users:
  * 100 users: 1 CPU, 2048 MB
  * 1000 users: 2 CPU, 4096 MB
  * 5000 users: 4 CPU, 8192 MB
  * 10000+ users: 8 CPU, 16384 MB

IMPORTANT: Return ONLY valid JSON with single values (not "web|api", just "web")."""

    try:
        # Claude API 호출
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_input}]
                },
                timeout=30.0
            )
            
            # 응답 상태 확인
            if response.status_code != 200:
                logger.error(f"Claude API HTTP error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise ValueError(f"Claude API returned {response.status_code}")
            
            # 응답에서 JSON 추출
            result = response.json()
            logger.info(f"Claude API response: {json.dumps(result, ensure_ascii=False)}")
            
            # Claude API v2023-06-01 응답 구조: {"content": [{"type": "text", "text": "..."}], ...}
            if "content" not in result:
                logger.error(f"No 'content' in response: {result}")
                raise KeyError("content")
            
            content_blocks = result["content"]
            if not content_blocks or len(content_blocks) == 0:
                logger.error(f"Empty content blocks: {content_blocks}")
                raise ValueError("Empty content")
            
            # 첫 번째 텍스트 블록 추출
            text = content_blocks[0]["text"].strip()
            logger.info(f"Raw Claude text: {text}")
            
            # JSON 마커 제거
            text = text.replace("```json", "").replace("```", "").strip()
            
            # JSON 파싱
            parsed = json.loads(text)
            logger.info(f"Parsed context: {json.dumps(parsed, ensure_ascii=False)}")
            
            # 값 검증 및 정규화
            parsed = _normalize_claude_response(parsed)
            
            return parsed
    
    except KeyError as e:
        # 오류 발생 시 로깅하고 기본값 반환
        logger.error(f"Claude API response KeyError: {e}")
        logger.error(f"Full response: {result if 'result' in locals() else 'N/A'}")
        return {
            "service_type": "web",
            "expected_users": 1000,
            "time_slot": "normal",
            "runtime_env": "prod",
            "curr_cpu": 2.0,
            "curr_mem": 4096.0,
            "reasoning": f"Error: {e}"
        }
    except Exception as e:
        # 오류 발생 시 로깅하고 기본값 반환
        logger.error(f"Claude error: {e}", exc_info=True)
        return {
            "service_type": "web",
            "expected_users": 1000,
            "time_slot": "normal",
            "runtime_env": "prod",
            "curr_cpu": 2.0,
            "curr_mem": 4096.0,
            "reasoning": f"Error: {e}"
        }


async def fetch_github_info(github_url: str) -> dict:
    """
    GitHub API를 사용하여 저장소 정보 수집
    
    Args:
        github_url (str): GitHub 저장소 URL
            예: https://github.com/owner/repo
    
    Returns:
        dict: 저장소 메타데이터
            - full_name: 저장소 전체 이름 (owner/repo)
            - description: 저장소 설명
            - language: 주 사용 프로그래밍 언어
            - stars: 스타 개수
            - forks: 포크 개수
    
    Raises:
        ValueError: GitHub API 호출 실패 시
    
    Note:
        - GITHUB_TOKEN이 설정되어 있으면 Rate Limit 완화
        - Rate Limit: 인증 없이 60회/시간, 인증 시 5000회/시간
    """
    # URL에서 owner와 repo 추출
    parts = github_url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]
    
    # GitHub API 엔드포인트
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    # GitHub API 호출
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers, timeout=10.0)
        
        if response.status_code != 200:
            raise ValueError(f"GitHub API error: {response.status_code}")
        
        # 필요한 정보만 추출하여 반환
        data = response.json()
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description", ""),
            "language": data.get("language", "Unknown"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
        }


async def call_mcp_core(github_url: str, mcp_context: dict) -> dict:
    """
    MCP Core의 /plans 엔드포인트 호출
    
    Args:
        github_url (str): GitHub 저장소 URL
        mcp_context (dict): MCPContext 데이터
            - context_id: 컨텍스트 ID
            - timestamp: 타임스탬프
            - service_type: 서비스 타입
            - runtime_env: 런타임 환경
            - time_slot: 시간대
            - expected_users: 예상 사용자 수
            - curr_cpu: 현재 CPU
            - curr_mem: 현재 메모리
    
    Returns:
        dict: MCP Core 예측 결과
            - prediction: LSTM/Baseline 예측값
            - recommended_flavor: 권장 Flavor
            - expected_cost_per_day: 예상 일일 비용
            - notes: 추가 정보
            - anomalies: 이상 탐지 결과 (있을 경우)
    
    Raises:
        ValueError: MCP Core 호출 실패 시
    
    Note:
        - MCP Core는 LSTM/Baseline 예측 수행
        - 이상 탐지 시 Discord 알림 자동 전송
    """
    url = f"{MCP_CORE_URL}/plans"
    
    # MCP Core 요청 본문 구성
    request_body = {
        "github_url": github_url,
        "github_url": github_url,
        "metric_name": "total_events",
        "context": mcp_context
    }
    
    logger.info(f"Calling MCP Core with: {json.dumps(request_body, default=str, ensure_ascii=False)}")
    
    # MCP Core 호출
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=request_body, timeout=30.0)
        
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"MCP Core error {response.status_code}: {error_detail}")
            raise ValueError(f"MCP Core error: {response.status_code} - {error_detail}")
        
        return response.json()


@app.post("/api/predict")
@app.post("/predict")
async def predict(request: PredictRequest):
    """
    완전 자동화 예측 엔드포인트
    
    프론트엔드에서 GitHub URL과 자연어를 받아 자동으로 변환하고 예측 수행
    
    Args:
        request (PredictRequest): 예측 요청
            - github_url: GitHub 저장소 URL
            - user_input: 자연어 요청사항
    
    Returns:
        dict: 예측 결과
            - success: 성공 여부
            - github_info: GitHub 저장소 정보
            - extracted_context: 추출된 컨텍스트 (CPU, Memory, Users 등)
            - predictions: LSTM/Baseline 예측값
            - recommendations: Flavor 권장사항 및 비용 예측
    
    Raises:
        HTTPException: 처리 중 오류 발생 시
    
    Example:
        Request:
        ```json
        {
            "github_url": "https://github.com/owner/repo",
            "user_input": "피크타임에 1000명 정도 사용할 것 같아요"
        }
        ```
        
        Response:
        ```json
        {
            "success": true,
            "github_info": {...},
            "extracted_context": {
                "service_type": "web",
                "expected_users": 1000,
                "time_slot": "peak",
                "curr_cpu": 2.0,
                "curr_mem": 4096.0,
                "reasoning": "..."
            },
            "predictions": {...},
            "recommendations": {...}
        }
        ```
    
    Workflow:
        1. GitHub API로 저장소 정보 수집
        2. Claude API로 자연어를 CPU/Memory/Users로 변환
        3. MCPContext 생성
        4. MCP Core /plans 호출 (LSTM 예측 + 이상 탐지)
        5. 결과 반환
    """
    try:
        logger.info(f"Request: {request.github_url}")
        
        # 1. GitHub 저장소 정보 수집
        github_data = await fetch_github_info(request.github_url)
        
        # 2. Claude API로 자연어 파싱
        parsed = await parse_with_claude(request.user_input, github_data)
        logger.info(f"Claude parsed result: {json.dumps(parsed, ensure_ascii=False)}")
        
        # service_type 검증 및 수정
        service_type = parsed.get("service_type", "web")
        # MCP Core는 "web", "api", "db"만 허용
        valid_service_types = ["web", "api", "db"]
        if service_type not in valid_service_types:
            logger.warning(f"Invalid service_type '{service_type}', defaulting to 'web'")
            service_type = "web"
        
        logger.info(f"Extracted: {parsed['expected_users']} users, {parsed['curr_cpu']} CPU, service_type: {service_type}")
        
        # 3. MCPContext 생성 (github_url은 context 외부에 위치)
        context_id = f"{github_data['full_name']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        mcp_context = {
            "context_id": context_id,
            "timestamp": datetime.utcnow().isoformat(),
            "service_type": service_type,
            "runtime_env": parsed.get("runtime_env", "prod"),
            "time_slot": parsed.get("time_slot", "normal"),
            "weight": 1.0,
            "region": None,
            "expected_users": int(parsed.get("expected_users", 1000)),
            "curr_cpu": float(parsed.get("curr_cpu", 2.0)),
            "curr_mem": float(parsed.get("curr_mem", 4096.0)),
        }
        
        logger.info(f"MCPContext created: {json.dumps(mcp_context, default=str, ensure_ascii=False)}")
        
        github_url = request.github_url
        
        # 4. MCP Core 호출 (LSTM 예측 + 이상 탐지 + Discord 알림)
        result = await call_mcp_core(github_url, mcp_context)
        
        # 5. 결과 반환
        return {
            "success": True,
            "github_info": github_data,
            "extracted_context": {
                "service_type": mcp_context["service_type"],
                "expected_users": mcp_context["expected_users"],
                "time_slot": mcp_context["time_slot"],
                "curr_cpu": mcp_context["curr_cpu"],
                "curr_mem": mcp_context["curr_mem"],
                "reasoning": parsed.get("reasoning", "")
            },
            "predictions": result.get("prediction", {}),
            "recommendations": {
                "flavor": result.get("recommended_flavor"),
                "cost_per_day": result.get("expected_cost_per_day"),
                "notes": result.get("notes")
            }
        }
    
    except Exception as e:
        # 오류 발생 시 로깅하고 500 에러 반환
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """
    서버 헬스 체크 엔드포인트
    
    Returns:
        dict: 서버 상태
            - status: 서버 상태 (healthy)
            - claude_api: Claude API 활성화 여부
    
    Example:
        ```json
        {
            "status": "healthy",
            "claude_api": "enabled"
        }
        ```
    """
    return {
        "status": "healthy",
        "claude_api": "enabled" if ANTHROPIC_API_KEY else "disabled"
    }


if __name__ == "__main__":
    """
    Backend API 서버 시작
    
    Environment Variables:
        - BACKEND_PORT: 서버 포트 (기본: 8001)
        - ANTHROPIC_API_KEY: Claude API 키
        - MCP_CORE_URL: MCP Core 서버 주소
        - GITHUB_TOKEN: GitHub API 토큰 (선택)
    
    Usage:
        $ python main.py
        
        또는
        
        $ uvicorn main:app --reload --port 8001
    """
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8001"))
    print(f"Backend API: http://localhost:{port}")
    print(f"Claude: {'enabled' if ANTHROPIC_API_KEY else 'disabled'}")
    print(f"MCP Core: {MCP_CORE_URL}")
    print(f"GitHub Token: {'configured' if GITHUB_TOKEN else 'not set'}")
    print(f"\nTip: Set ANTHROPIC_API_KEY in .env file")
    uvicorn.run(app, host="0.0.0.0", port=port)
