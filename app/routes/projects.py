from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.core import projects_store
from app.models.projects import Project, ProjectCreate, ProjectUpdate, ProjectsResponse

router = APIRouter()


def _to_project(record: dict) -> Project:
    return Project(
        id=record["id"],
        name=record["name"],
        repository=record["repository"],
        status=record["status"],
        url=record.get("url"),
        lastDeployment=record.get("lastDeployment"),
        service_id=record.get("service_id"),
        instance_id=record.get("instance_id"),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


@router.get("", response_model=ProjectsResponse)
def list_projects() -> ProjectsResponse:
    records = projects_store.list_projects()
    return ProjectsResponse(projects=[_to_project(r) for r in records])


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate) -> Project:
    record = projects_store.create_project(
        name=payload.name,
        repository=payload.repository,
        status=payload.status,
        url=payload.url,
        last_deployment=payload.lastDeployment,
        service_id=payload.service_id,
        instance_id=payload.instance_id,
    )
    return _to_project(record)


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: int) -> Project:
    record = projects_store.get_project(project_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _to_project(record)


@router.put("/{project_id}", response_model=Project)
def update_project(project_id: int, payload: ProjectUpdate) -> Project:
    record = projects_store.update_project(
        project_id,
        name=payload.name,
        repository=payload.repository,
        status=payload.status,
        url=payload.url,
        lastDeployment=payload.lastDeployment,
        service_id=payload.service_id,
        instance_id=payload.instance_id,
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _to_project(record)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_project(project_id: int) -> Response:
    deleted = projects_store.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)