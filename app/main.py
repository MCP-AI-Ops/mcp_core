from fastapi import FastAPI
form fastapi.responses import JSONResponse

from app.routes import plans, deploy, status, destroy


app = FastAPI(title="MCP Orchestrator", version="0.1.0")

@app.get("/health")
def health():
    return {"status = ok": True}

app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(deploy.router, prefix="/deploy", tags=["deploy"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(destroy.router, prefix="/destroy", tags=["destroy"])

@app.exception_handler(Exception)
async def unhandled_ex(e: Exception, _):
    return JSONResponse(status_code=500, content={"detail": str(e)})