from fastapi import APIRouter
from app.models.destroy import DestroyRequest, DestroyResponse

router = APIRouter()

@router.post("", response_model=DestroyResponse)
def destroy(req: DestroyRequest):
    # TODO: openstack_adapter 통해 자원 삭제
    # 지금은 더미
    return DestroyResponse(ok=True, message=f"Destroyed {req.instance_id} for {req.service_id} (mock)")
