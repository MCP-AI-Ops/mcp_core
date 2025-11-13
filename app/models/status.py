from pydantic import BaseModel

class StatusQuery(BaseModel):
    github_url: str

class StatusResponse(BaseModel):
    github_url: str
    instance_id: str
    cpu_usage: float
    mem_usage: float
    is_healthy: bool
