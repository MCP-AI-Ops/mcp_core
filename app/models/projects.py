from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    repository: str
    status: str = "building"
    url: Optional[str] = None
    lastDeployment: Optional[datetime] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Payload for creating a new project."""


class ProjectUpdate(BaseModel):
    """Payload for updating an existing project (partial update via PUT)."""

    name: Optional[str] = None
    repository: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
    lastDeployment: Optional[datetime] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ProjectsResponse(BaseModel):
    projects: List[Project]

