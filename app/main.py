import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv

from app.core import projects_store
from app.routes import deploy, destroy, plans, projects, status
from app.routes import router_auth

load_dotenv()

app = FastAPI(title="MCP Orchestrator", version="0.1.0")

# CORS 설정 (프론트엔드와 연동을 위해)
# 환경 변수에서 허용할 origin을 가져오거나 기본값 사용
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://localhost:5173,http://localhost:3000,https://launcha.cloud,https://api.launcha.cloud",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(deploy.router, prefix="/deploy", tags=["deploy"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(destroy.router, prefix="/destroy", tags=["destroy"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(router_auth.router)


@app.on_event("startup")
def _seed_demo_projects() -> None:
    """
    선택적 프로젝트 목데이터 시드.

    PROJECTS_DEMO_SEED=true 인 경우에만,
    기존 프로젝트가 없을 때 간단한 데모 프로젝트를 두 개 생성한다.
    """
    flag = os.getenv("PROJECTS_DEMO_SEED", "").lower()
    enabled = flag in {"1", "true", "yes", "on"}
    if not enabled:
        return

    # 이미 프로젝트가 있으면 시드하지 않음
    if projects_store.list_projects():
        return

    projects_store.create_project(
        name="Demo Web Service",
        repository="https://github.com/example/demo-web-service",
        status="deployed",
        url="https://demo-web.example.com",
    )
    projects_store.create_project(
        name="Demo API Service",
        repository="https://github.com/example/demo-api-service",
        status="building",
    )


@app.exception_handler(Exception)
async def unhandled_ex(request: Request, exc: Exception):
    # 전역 예외 처리: JSON 형태로 에러를 반환
    return JSONResponse(status_code=500, content={"detail": str(exc)})
