# app/models/projects.py
# 프로젝트 관련 모델 정의

from pydantic import BaseModel, HttpUrl
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional, Literal
from app.models.model_user import Base

# SQLAlchemy 모델
class ProjectDB(Base):
    """프로젝트 DB 모델"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    repository = Column(String, nullable=False)  # GitHub URL
    status = Column(String, default="building")  # "deployed" | "building" | "error" | "stopped"
    url = Column(String, nullable=True)
    service_id = Column(String, nullable=True)
    instance_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic 모델 (API 요청/응답)
class ProjectCreate(BaseModel):
    """프로젝트 생성 요청 모델"""
    name: str
    repository: HttpUrl

class ProjectUpdate(BaseModel):
    """프로젝트 업데이트 요청 모델"""
    name: Optional[str] = None
    repository: Optional[HttpUrl] = None
    status: Optional[Literal["deployed", "building", "error", "stopped"]] = None
    url: Optional[str] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None

class Project(BaseModel):
    """프로젝트 정보 응답 모델"""
    id: int
    name: str
    repository: str
    status: str  # "deployed" | "building" | "error" | "stopped"
    lastDeployment: Optional[str] = None
    url: Optional[str] = None
    service_id: Optional[str] = None
    instance_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProjectsResponse(BaseModel):
    """프로젝트 목록 응답 모델"""
    projects: list[Project]

