# from fastapi import APIRouter
# from app.models.deploy import DeployRequest, DeployResponse

# router = APIRouter()

# @router.post("", response_model=DeployResponse)
# def deploy(req: DeployRequest):
#     # TODO: openstack_adapter 호출하여 VM 생성(or 컨테이너 시작)
#     # 지금은 더미
#     return DeployResponse(
#         accepted=True,
#         plan_id=f"plan-{req.service_id}",
#         instance_id="vm-123456",
#         message="Deployment request accepted (mock)"
#     )

from fastapi import APIRouter, HTTPException
from app.schemas.deploy import DeployRequest, DeployAccepted
from app.services.openstack import start_deploy

router = APIRouter()

@router.post("", response_model=DeployAccepted, status_code=202)
async def deploy(req: DeployRequest):
    try:
        # 오케스트레이션 시작 (in-memory 또는 DB로 상태 저장)
        return await start_deploy(req)
    except Exception as e:
        # 모델/오픈스택/설정 오류 등은 500으로 래핑
        raise HTTPException(status_code=500, detail=str(e))