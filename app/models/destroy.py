from pydantic import BaseModel

class DestroyRequest(BaseModel):
    github_url: str
    instance_id: str

class DestroyResponse(BaseModel):
    ok: bool
    message: str
