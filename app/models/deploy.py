from pydantic import BaseModel
from typing import Optional, Dict, Any

class DeployRequest(BaseModel):
    github_url: str
    repo_id: Optional[str] = None
    image_tag: Optional[str] = "latest"
    env_config: Dict[str, Any] = {}

class DeployResponse(BaseModel):
    accepted: bool
    plan_id: Optional[str] = None
    instance_id: Optional[str] = None
    message: str
