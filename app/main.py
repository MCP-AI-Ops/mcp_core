import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routes import plans, status, destroy
from app.routes import router_auth

app = FastAPI(title="MCP Orchestrator", version="0.1.0")

# CORS 설정 (프론트엔드와 연동을 위해)
# 환경 변수에서 허용할 origin을 가져오거나 기본값 사용
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(plans.router, prefix="/plans", tags=["plans"])
# deploy 라우터는 deploy_main.py에서 별도 포트(8001)로 제공
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(destroy.router, prefix="/destroy", tags=["destroy"])
app.include_router(router_auth.router, prefix="/auth", tags=["auth"])

@app.exception_handler(Exception)
async def unhandled_ex(request: Request, exc: Exception):
    # 전역 예외 처리: JSON 형태로 에러를 반환
    return JSONResponse(status_code=500, content={"detail": str(exc)})