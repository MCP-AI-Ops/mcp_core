# app/routes/deploy.py
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
import httpx
import os
from datetime import datetime

from dotenv import load_dotenv

from app.models.deploy import DeployRequest, DeployResponse, InstanceInfo
from app.core.openstack.deployer import create_server
from app.core.openstack.flavor_mapper import get_openstack_flavor
from app.core.openstack.client import get_connection
from app.models.common import MCPContext

# .env 파일 로드 (OPENSTACK_* 및 MCP_CORE_URL 등)
load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=DeployResponse)
def deploy(req: DeployRequest) -> DeployResponse:
    """
    GitHub URL과 자연어를 받아서 예측 후 OpenStack에 VM을 생성하는 엔드포인트.
    
    플로우:
    1. /plans 엔드포인트를 내부적으로 호출하여 예측 및 recommended_flavor 받기
    2. recommended_flavor를 OpenStack flavor로 변환
    3. OpenStack에 VM 생성
    """
    try:
        # 1. Plans 엔드포인트 호출 (내부 호출)
        mcp_core_url = os.getenv("MCP_CORE_URL", "http://localhost:8000")
        
        # Plans 요청을 위한 기본 컨텍스트 생성
        # (실제로는 Backend API에서 받은 컨텍스트를 사용해야 함)
        context = MCPContext(
            context_id=f"deploy-{req.github_url.replace('/', '-')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.utcnow(),
            service_type="web",
            runtime_env="prod",
            time_slot="normal",
            weight=1.0,
            expected_users=1000,  # 기본값
            curr_cpu=2.0,
            curr_mem=4096.0,
        )
        
        plans_request = {
            "github_url": req.github_url,
            "metric_name": "total_events",
            "context": context.model_dump(mode='json')  # datetime을 ISO 문자열로 변환
        }
        
        # 내부 호출 (동기)
        with httpx.Client(timeout=30.0) as client:
            plans_response = client.post(
                f"{mcp_core_url}/plans",
                json=plans_request
            )
            
            if plans_response.status_code != 200:
                raise HTTPException(
                    status_code=plans_response.status_code,
                    detail=f"Plans API failed: {plans_response.text}"
                )
            
            plans_data = plans_response.json()
            recommended_flavor = plans_data.get("recommended_flavor", "small")
            plan_id = plans_data.get("prediction", {}).get("github_url", req.github_url)
        
        # 2. OpenStack flavor 매핑
        openstack_flavor = get_openstack_flavor(
            recommended_flavor,
            runtime_env=context.runtime_env
        )
        
        # 3. OpenStack 연결 및 리소스 확인
        conn = get_connection()
        
        # OpenStack 리소스 이름 (환경변수 또는 기본값)
        image_name = os.getenv("OPENSTACK_IMAGE_NAME", "cirros-0.6.3-x86_64-disk")
        network_name = os.getenv("OPENSTACK_NETWORK_NAME", "private")
        key_name = os.getenv("OPENSTACK_KEY_NAME", "default")  # 기본값 설정
        
        # 4. VM 생성
        server_name = f"mcp-{req.github_url.split('/')[-1]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        instance_info = create_server(
            name=server_name,
            image_ref=image_name,
            flavor_name=openstack_flavor,
            network_name=network_name,
            key_name=key_name or "default",
            metadata={
                "github_url": req.github_url,
                "plan_id": plan_id,
                "recommended_flavor": recommended_flavor,
                "deployed_at": datetime.utcnow().isoformat(),
            }
        )
        
        return DeployResponse(
            accepted=True,
            plan_id=plan_id,
            instance_id=instance_info.instance_id,
            instance=instance_info,
            message=f"VM created successfully: {instance_info.name} ({instance_info.status})",
            deployed_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Deployment failed")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

