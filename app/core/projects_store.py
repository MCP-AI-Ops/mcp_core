from __future__ import annotations

from datetime import datetime
from itertools import count
from threading import Lock
from typing import Any, Dict, List, Optional

ProjectStatus = str

_lock = Lock()
_id_counter = count(1)
_projects: Dict[int, Dict[str, Any]] = {}


def _now() -> datetime:
  return datetime.utcnow()


def _clone(record: Dict[str, Any]) -> Dict[str, Any]:
  return {**record}


def list_projects() -> List[Dict[str, Any]]:
  with _lock:
    return [_clone(p) for p in _projects.values()]


def get_project(project_id: int) -> Optional[Dict[str, Any]]:
  with _lock:
    record = _projects.get(project_id)
    return _clone(record) if record else None


def create_project(
  *,
  name: str,
  repository: str,
  status: ProjectStatus = "building",
  url: Optional[str] = None,
  last_deployment: Optional[datetime] = None,
  service_id: Optional[str] = None,
  instance_id: Optional[str] = None,
) -> Dict[str, Any]:
  with _lock:
    record_id = next(_id_counter)
    now = _now()
    record: Dict[str, Any] = {
      "id": record_id,
      "name": name,
      "repository": repository,
      "status": status,
      "url": url,
      "lastDeployment": last_deployment,
      "service_id": service_id,
      "instance_id": instance_id,
      "created_at": now,
      "updated_at": now,
    }
    _projects[record_id] = record
    return _clone(record)


def update_project(project_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
  with _lock:
    if project_id not in _projects:
      return None
    record = _projects[project_id]
    # None 값은 무시하고 실제 값만 업데이트
    for key, value in fields.items():
      if value is not None:
        record[key] = value
    record["updated_at"] = _now()
    return _clone(record)


def delete_project(project_id: int) -> bool:
  with _lock:
    return _projects.pop(project_id, None) is not None


def upsert_project(
  *,
  name: Optional[str],
  repository: str,
  status: Optional[ProjectStatus] = None,
  url: Optional[str] = None,
  last_deployment: Optional[datetime] = None,
  service_id: Optional[str] = None,
  instance_id: Optional[str] = None,
) -> Dict[str, Any]:
  """
  service_id 또는 repository 기준으로 기존 프로젝트가 있으면 업데이트,
  없으면 새로 생성한다.
  """
  with _lock:
    existing: Optional[Dict[str, Any]] = None

    if service_id:
      existing = next(
        (p for p in _projects.values() if p.get("service_id") == service_id),
        None,
      )
    if existing is None:
      existing = next(
        (p for p in _projects.values() if p["repository"] == repository),
        None,
      )

    if existing:
      if name:
        existing["name"] = name
      if status:
        existing["status"] = status
      if url is not None:
        existing["url"] = url
      if last_deployment is not None:
        existing["lastDeployment"] = last_deployment
      if service_id is not None:
        existing["service_id"] = service_id
      if instance_id is not None:
        existing["instance_id"] = instance_id
      existing["updated_at"] = _now()
      return _clone(existing)

    # 기존 레코드가 없으면 새로 생성
    return _clone(
      create_project(
        name=name or repository.split("/")[-1],
        repository=repository,
        status=status or "building",
        url=url,
        last_deployment=last_deployment,
        service_id=service_id,
        instance_id=instance_id,
      )
    )


