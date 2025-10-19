from fastapi import APIRouter
from app.models.deploy import DeployRequest, DeployResponse

router = APIRouter()

@router.post("", response_model=DeployResponse)
def deploy(req: DeployRequest):
    # TODO: openstack_adapter 호출하여 VM 생성(or 컨테이너 시작)
    # 지금은 더미
    return DeployResponse(
        accepted=True,
        plan_id=f"plan-{req.service_id}",
        instance_id="vm-123456",
        message="Deployment request accepted (mock)"
    )
