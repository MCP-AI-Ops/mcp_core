# app/core/openstack_client.py
import os
from openstack import connection

def get_openstack_connection() -> connection.Connection:
    """
    DevStack openrc 로드해서 세팅된 OS_* 환경변수로 OpenStack 연결.
    """
    return connection.Connection(
        auth_url=os.environ["OS_AUTH_URL"],
        username=os.environ["OS_USERNAME"],
        password=os.environ["OS_PASSWORD"],
        project_name=os.environ["OS_PROJECT_NAME"],
        user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME", "Default"),
        project_domain_name=os.environ.get("OS_PROJECT_DOMAIN_NAME", "Default"),
        region_name=os.environ.get("OS_REGION_NAME", "RegionOne"),
        compute_api_version="2",
        identity_interface="public",
    )

