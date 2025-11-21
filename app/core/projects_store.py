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
        record = {
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
        record.update({k: v for k, v in fields.items() if v is not None})
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
    with _lock:
        existing = None
        if service_id:
            existing = next((p for p in _projects.values() if p.get("service_id") == service_id), None)
        if existing is None:
            existing = next((p for p in _projects.values() if p["repository"] == repository), None)

        if existing:
            existing.update(
                {
                    "name": name or existing["name"],
                    "status": status or existing["status"],
                    "url": url or existing.get("url"),
                    "lastDeployment": last_deployment or existing.get("lastDeployment"),
                    "service_id": service_id or existing.get("service_id"),
                    "instance_id": instance_id or existing.get("instance_id"),
                    "updated_at": _now(),
                }
            )
            return _clone(existing)

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

