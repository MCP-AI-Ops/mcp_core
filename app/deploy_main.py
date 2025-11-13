"""
MCP 배포 요청 전용 서버 (8001 포트)
EC2에서 이 파일을 실행하여 /deploy 엔드포인트만 별도 포트로 제공
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routes import deploy

# 배포 전용 FastAPI 앱 생성
app = FastAPI(title="MCP Deploy Server", version="0.1.0")

# CORS 설정
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://localhost:5173,http://localhost:3000,https://*.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /deploy 라우터만 포함
app.include_router(deploy.router, prefix="/deploy", tags=["deploy"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "deploy"}

@app.exception_handler(Exception)
async def unhandled_ex(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})

if __name__ == "__main__":
    # 8001 포트로 실행
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False
    )

