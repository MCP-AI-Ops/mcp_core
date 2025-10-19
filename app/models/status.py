from pydantic import BaseModel

class StatusQuery(BaseModel):
    service_id: str

class StatusResponse(BaseModel):
    service_id: str
    instance_id: str
    cpu_usage: float
    mem_usage: float
    is_healthy: bool
