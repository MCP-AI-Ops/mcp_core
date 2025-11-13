# app/routes/destroy.py

from fastapi import APIRouter, HTTPException
from openstack.exceptions import ResourceNotFound

from app.models.destroy import DestroyRequest, DestroyResponse
from app.core.openstack_client import get_openstack_connection

router = APIRouter()


@router.post("", response_model=DestroyResponse)
def destroy(req: DestroyRequest) -> DestroyResponse:
    conn = get_openstack_connection()

    # instance_id 또는 name으로 서버 찾기
    server = conn.compute.find_server(req.instance_id, ignore_missing=True)

    if server is None:
        # 이미 없거나 잘못된 ID
        raise HTTPException(
            status_code=404,
            detail=f"Server not found: {req.instance_id}",
        )

    try:
        # 실제 삭제 호출
        conn.compute.delete_server(server, ignore_missing=False)
    except ResourceNotFound:
        # 삭제 중에 사라진 케이스 (거의 없지만 방어용)
        raise HTTPException(
            status_code=404,
            detail=f"Server not found while deleting: {req.instance_id}",
        )
    except Exception as e:
        # 그 외 OpenStack 에러
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete server {req.instance_id}: {e}",
        )

    return DestroyResponse(
        ok=True,
        message=f"Deleted {server.id} ({server.name}) for {req.service_id}",
    )

