# app/routes/deploy.py

from datetime import datetime
import logging
import os

from fastapi import APIRouter, HTTPException, status

from app.models.deploy import DeployRequest, DeployResponse, InstanceInfo
from app.core.openstack.flavor_mapper import get_openstack_flavor
from app.core.openstack.deployer import create_server
from app.core.errors import DeploymentError

router = APIRouter()


@router.post("", response_model=DeployResponse)
def deploy(req: DeployRequest):
    """
    배포 요청 처리.

    1) Plans에서 넘어온 recommended_flavor 해석
    2) OpenStack flavor로 매핑
    3) OpenStack에 VM 생성
    4) 생성된 인스턴스 정보와 함께 DeployResponse 반환
    """

    # 1) env_config 해석
    env = req.env_config or {}
    recommended_flavor = env.get("recommended_flavor")
    runtime_env = env.get("runtime_env", "prod")
    use_env_mapping = env.get("use_env_mapping", False)

    # 2) recommended_flavor -> OpenStack flavor
    if recommended_flavor:
        try:
            openstack_flavor = get_openstack_flavor(
                recommended_flavor=recommended_flavor,
                runtime_env=runtime_env,
                use_env_mapping=use_env_mapping,
            )
        except ValueError:
            # 알 수 없는 flavor면 m1.small 로 폴백
            logging.warning("Unknown recommended_flavor=%s, fallback to m1.small",
                            recommended_flavor)
            openstack_flavor = "m1.small"
    else:
        openstack_flavor = "m1.small"

    # 3) DevStack에 VM 생성
    image_ref = req.image_tag or os.getenv("OS_IMAGE_ID")
    if not image_ref:
        logging.warning("No image specified, using default cirros image")
        image_ref = "cirros-0.6.3-x86_64-disk"
    
    try:
        instance: InstanceInfo = create_server(
            name=f"{req.service_id}-{runtime_env}",
            image_ref=image_ref,
            flavor_name=openstack_flavor or "m1.small",
            network_name=env.get("network_name", "private"),
            key_name=env.get("key_name", "demo-key"),
            metadata={
                "service_id": req.service_id,
                "repo_id": req.repo_id or "",
                "runtime_env": runtime_env,
            },
        )
    except DeploymentError as e:
        logging.exception("Deployment failed: %s", e)
        # 계약상 accepted=False 로 돌려줄지, 5xx 를 낼지는 선택인데
        # 일단 500 으로 올려보는 쪽으로.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {e}",
        )

    # 4) 성공 응답
    return DeployResponse(
        accepted=True,
        plan_id=req.plan_id or f"plan-{req.service_id}",
        instance_id=instance.instance_id,
        instance=instance,
        message=(
            f"Deployment request accepted. "
            f"instance={instance.name}, flavor={instance.flavor_name}"
        ),
        deployed_at=datetime.utcnow(),
    )
