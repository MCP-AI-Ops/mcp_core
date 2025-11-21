# app/routes/deploy.py
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
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
from app.core import projects_store

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
        env_config: Dict[str, Any] = req.env_config or {}
        service_id = env_config.get("service_id")

        def _safe_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _safe_float(value: Any, default: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        provided_context: Dict[str, Any] = (
            env_config.get("context")
            or env_config.get("extracted_context")
            or {}
        )

        context_id = env_config.get("context_id") or f"deploy-{req.github_url.replace('/', '-')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # 1. Plans 엔드포인트 호출 (내부 호출)
        mcp_core_url = os.getenv("MCP_CORE_URL", "http://localhost:8000")
        
        # Plans 요청을 위한 컨텍스트 생성 (Predict 응답 기반 값 우선 사용)
        context = MCPContext(
            context_id=context_id,
            timestamp=datetime.utcnow(),
            service_type=provided_context.get("service_type", "web"),
            runtime_env=provided_context.get("runtime_env", "prod"),
            time_slot=provided_context.get("time_slot", "normal"),
            weight=float(env_config.get("weight") or 1.0),
            expected_users=_safe_int(provided_context.get("expected_users"), 1000),
            curr_cpu=_safe_float(provided_context.get("curr_cpu"), 2.0),
            curr_mem=_safe_float(provided_context.get("curr_mem"), 4096.0),
        )

        recommendations_payload = env_config.get("recommendations", {})
        recommended_flavor_override = env_config.get("recommended_flavor")
        if not recommended_flavor_override and isinstance(recommendations_payload, dict):
            recommended_flavor_override = recommendations_payload.get("flavor")

        recommended_flavor: Optional[str] = None
        if recommended_flavor_override:
            recommended_flavor = str(recommended_flavor_override).strip().lower()
            if recommended_flavor not in {"small", "medium", "large"}:
                logger.warning(
                    "Invalid recommended_flavor '%s' from env_config. Falling back to Plans API.",
                    recommended_flavor_override,
                )
                recommended_flavor = None

        plan_id = req.plan_id or env_config.get("plan_id") or context.context_id

        if recommended_flavor is None:
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
                plan_prediction = plans_data.get("prediction", {}) or {}
                plan_id = plan_prediction.get("plan_id") or plan_prediction.get("github_url", req.github_url)
        else:
            logger.info("Using recommended_flavor from Predict response: %s", recommended_flavor)
        
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
                "service_id": service_id or "",
                "deployed_at": datetime.utcnow().isoformat(),
            }
        )

        status_label = "deployed"
        if not instance_info.status or instance_info.status.upper() not in {"ACTIVE", "RUNNING"}:
            status_label = "building"

        projects_store.upsert_project(
            name=server_name,
            repository=req.github_url,
            status=status_label,
            url=env_config.get("public_url"),
            last_deployment=datetime.utcnow(),
            service_id=service_id,
            instance_id=instance_info.instance_id,
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

