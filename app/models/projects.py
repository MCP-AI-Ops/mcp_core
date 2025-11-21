from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ProjectStatus = Literal["building", "deployed", "error", "stopped"]


class ProjectBase(BaseModel):
    name: str
    repository: str
    status: ProjectStatus = "building"
    url: Optional[str] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None
    lastDeployment: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    repository: Optional[str] = None
    status: Optional[ProjectStatus] = None
    url: Optional[str] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None
    lastDeployment: Optional[datetime] = None


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ProjectsResponse(BaseModel):
    projects: list[Project]

