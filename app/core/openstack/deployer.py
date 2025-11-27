# app/core/openstack/deployer.py

import logging
from typing import Optional, Dict, Any

from app.core.openstack.client import get_connection
from app.core.errors import DeploymentError
from app.models.deploy import InstanceInfo


def create_server(
    *,
    name: str,
    image_ref: str,  # 이름 또는 ID
    flavor_name: str,
    network_name: str,
    key_name: str,
    metadata: Optional[Dict[str, str]] = None,
    user_data: Optional[str] = None,
    wait_until_active: bool = False,
) -> InstanceInfo:
    """
    DevStack에 VM 한 대를 생성하고, 부팅 완료될 때까지 기다린 뒤
    InstanceInfo 모델로 반환한다.
    """
    conn = get_connection()

    try:
        # 1) 먼저 compute 쪽에서 이미지 찾아보기 (이름 / ID 둘 다 지원)
        img = conn.compute.find_image(image_ref)  # type: ignore
        if img is not None:
            image_id = img.id
        else:
            # 못 찾으면 그냥 "이미 ID 라고 가정" 하고 그대로 사용
            image_id = image_ref
    except Exception as e:
        logging.exception("Failed to resolve image via compute API, using raw ref: %s", e)
        image_id = image_ref

    # 2) flavor / network 도 compute / network 프록시로만 처리
    flv = conn.compute.find_flavor(flavor_name, ignore_missing=False)  # type: ignore
    net = conn.network.find_network(network_name, ignore_missing=False)  # type: ignore

    try:
        # OpenStack API는 user_data가 None 인 것을 허용하지 않고 string 타입만 허용하는 경우가 있다.
        # 따라서 user_data가 None 이면 아예 인자를 보내지 않는다.
        create_kwargs: Dict[str, Any] = {
            "name": name,
            "image_id": image_id,
            "flavor_id": flv.id,
            "networks": [{"uuid": net.id}],
            "key_name": key_name,
            "metadata": metadata or {},
        }
        if user_data is not None:
            create_kwargs["user_data"] = user_data

        server = conn.compute.create_server(  # type: ignore
            **create_kwargs
        )
        if wait_until_active:
            # VM 부팅 완료까지 블로킹
            server = conn.compute.wait_for_server(server)  # type: ignore
        else:
            # 최소한의 최신 정보를 위해 한 번만 조회
            server = conn.compute.get_server(server.id)  # type: ignore
    except Exception as e:
        logging.exception("Failed to create server")
        raise DeploymentError(f"Failed to create server: {e}")

    # InstanceInfo 빌드 (필드명은 프로젝트 정의에 맞게 조정)
    return InstanceInfo(
        instance_id=server.id,
        name=server.name,
        image_name=getattr(server.image, "id", image_id),
        flavor_name=flv.name,
        network_name=net.name,
        key_name=key_name,
        metadata=server.metadata or {},
        user_data=user_data,
        status=server.status,
        addresses=server.addresses or {},
    )
