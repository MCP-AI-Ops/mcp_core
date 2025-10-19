from pydantic import BaseModel

class DestroyRequest(BaseModel):
    service_id: str
    instance_id: str

class DestroyResponse(BaseModel):
    ok: bool
    message: str
