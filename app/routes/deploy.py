# app/routes/deploy.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.openstack_client import get_openstack_connection

router = APIRouter()


# 이미 있을 수도 있지만, 예시로 작성
class DeployRequest(BaseModel):
    service_id: str
    repo_id: str
    image_tag: str = "latest"
    env_config: dict = {}

class DeployResponse(BaseModel):
    accepted: bool
    plan_id: str
    instance_id: str
    message: str


@router.post("/deploy", response_model=DeployResponse)
def deploy(req: DeployRequest) -> DeployResponse:
    """
    진짜로 DevStack에 VM 하나 생성하는 엔드포인트.
    """
    try:
        conn = get_openstack_connection()

        # TODO: 네 devstack 상황에 맞게 이름 조정
        IMAGE_NAME = "cirros-0.6.3-x86_64-disk"   # openstack image list 로 확인
        FLAVOR_NAME = "m1.small"      # openstack flavor list
        NETWORK_NAME = "private"      # openstack network list

        image = conn.compute.find_image(IMAGE_NAME, ignore_missing=False)
        flavor = conn.compute.find_flavor(FLAVOR_NAME, ignore_missing=False)
        network = conn.network.find_network(NETWORK_NAME, ignore_missing=False)

        server_name = req.service_id

        server = conn.compute.create_server(
            name=server_name,
            image_id=image.id,
            flavor_id=flavor.id,
            networks=[{"uuid": network.id}],
            # 필요하면 여기서 user_data로 repo_id, env_config 등 넘겨서
            # cloud-init 스크립트로 앱 배포까지 할 수 있음.
        )

        # VM이 ACTIVE 될 때까지 기다림
        server = conn.compute.wait_for_server(server)

        return DeployResponse(
            accepted=True,
            plan_id=f"plan-{req.service_id}",
            instance_id=server.id,
            message=f"VM created: {server.name} ({server.status})",
        )

    except Exception as e:
        # 로그 찍고 500 던지기
        raise HTTPException(status_code=500, detail=f"Deployment failed: {e}")

