from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class InstanceInfo(BaseModel):
    instance_id: str
    name: str
    image_name: str
    flavor_name: str
    network_name: str
    key_name: str
    metadata: Optional[Dict[str, str]] = None
    user_data: Optional[str] = None
    status: str
    addresses: Dict[str, Any]  # OpenStack 서버 addresses 그대로
    
    @property
    def id(self) -> str:
        """instance_id의 별칭 (호환성)"""
        return self.instance_id
    
    @property
    def flavor(self) -> str:
        """flavor_name의 별칭 (호환성)"""
        return self.flavor_name

class DeployRequest(BaseModel):
    github_url: str
    repo_id: Optional[str] = None
    image_tag: Optional[str] = "latest"
    plan_id: Optional[str] = None  # Plans에서 넘어온 plan_id
    env_config: Dict[str, Any] = {}

class DeployResponse(BaseModel):
    accepted: bool
    plan_id: Optional[str] = None
    instance_id: Optional[str] = None
    instance: Optional[InstanceInfo] = None  # 생성된 인스턴스 정보
    message: str
    deployed_at: Optional[datetime] = None
