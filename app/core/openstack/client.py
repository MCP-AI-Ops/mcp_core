# app/core/openstack/client.py
from functools import lru_cache
import os

from openstack import connection


class OpenStackConfigError(RuntimeError):
    """OS_* 설정이 잘못된 경우 발생하는 에러."""


@lru_cache
def get_connection() -> connection.Connection:
    """
    DevStack/OpenStack 연결 객체를 하나만 생성해서 재사용한다.
    
    우선 OS_CLOUD(clouds.yaml) 를 쓰고, 없으면 OS_AUTH_URL 등 환경변수 기반으로 붙는다.
    """
    cloud = os.getenv("OS_CLOUD")
    if cloud:
        return connection.Connection(cloud=cloud)

    required = ["OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD", "OS_PROJECT_NAME"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise OpenStackConfigError(f"Missing OpenStack env vars: {', '.join(missing)}")

    return connection.Connection(
        auth_url=os.environ["OS_AUTH_URL"],
        username=os.environ["OS_USERNAME"],
        password=os.environ["OS_PASSWORD"],
        project_name=os.environ["OS_PROJECT_NAME"],
        user_domain_name=os.getenv("OS_USER_DOMAIN_NAME", "Default"),
        project_domain_name=os.getenv("OS_PROJECT_DOMAIN_NAME", "Default"),
        region_name=os.getenv("OS_REGION_NAME", "RegionOne"),
        compute_api_version="2",
        identity_interface="public",
    )
