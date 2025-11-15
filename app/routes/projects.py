# app/routes/projects.py
# 프로젝트 관련 API

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.projects import (
    Project, ProjectsResponse, ProjectCreate, ProjectUpdate, ProjectDB
)
from app.models.model_user import User
from app.core.security import get_current_user
from app.core.db import get_db
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_response(project_db: ProjectDB) -> Project:
    """ProjectDB를 Project 응답 모델로 변환"""
    last_deployment = project_db.created_at.strftime("%Y-%m-%d %H:%M:%S") if project_db.created_at else None
    
    return Project(
        id=project_db.id,
        name=project_db.name,
        repository=project_db.repository,
        status=project_db.status,
        lastDeployment=last_deployment,
        url=project_db.url,
        service_id=project_db.service_id,
        instance_id=project_db.instance_id
    )


@router.get("", response_model=ProjectsResponse)
def get_projects(
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """유저별 프로젝트 목록 조회"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    projects_db = db.query(ProjectDB).filter(ProjectDB.user_id == user.id).all()
    projects = [_project_to_response(p) for p in projects_db]
    
    return ProjectsResponse(projects=projects)


@router.post("", response_model=Project, status_code=201)
def create_project(
    project_data: ProjectCreate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로젝트 생성"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 중복 체크 (같은 repository가 이미 있는지)
    existing = db.query(ProjectDB).filter(
        ProjectDB.user_id == user.id,
        ProjectDB.repository == str(project_data.repository)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Project with this repository already exists")
    
    new_project = ProjectDB(
        user_id=user.id,
        name=project_data.name,
        repository=str(project_data.repository),
        status="building"
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return _project_to_response(new_project)


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로젝트 상세 조회"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    project = db.query(ProjectDB).filter(
        ProjectDB.id == project_id,
        ProjectDB.user_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return _project_to_response(project)


@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로젝트 업데이트"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    project = db.query(ProjectDB).filter(
        ProjectDB.id == project_id,
        ProjectDB.user_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 업데이트할 필드만 적용
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.repository is not None:
        project.repository = str(project_data.repository)
    if project_data.status is not None:
        project.status = project_data.status
    if project_data.url is not None:
        project.url = project_data.url
    if project_data.service_id is not None:
        project.service_id = project_data.service_id
    if project_data.instance_id is not None:
        project.instance_id = project_data.instance_id
    
    project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(project)
    
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로젝트 삭제"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    project = db.query(ProjectDB).filter(
        ProjectDB.id == project_id,
        ProjectDB.user_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return None

