# app/core/openstack/flavor_mapper.py

"""
OpenStack Flavor 매핑 모듈.

역할:
- recommended_flavor ("small", "medium", "large")를 OpenStack flavor 이름으로 변환
- 환경별(prod/dev), 리전별로 다른 flavor 매핑 지원 가능
- 향후 OpenStack API를 통해 실제 flavor 목록을 조회하여 검증 가능
"""

from typing import Dict, Optional
from app.models.common import RuntimeEnv


# 기본 flavor 매핑 테이블
# 추천 flavor → OpenStack flavor 이름
_DEFAULT_FLAVOR_MAP: Dict[str, str] = {
    "small": "m1.small",
    "medium": "m1.medium",
    "large": "m1.large",
}

# 환경별 flavor 매핑 (선택적)
# prod 환경에서는 더 큰 인스턴스, dev에서는 더 작은 인스턴스 사용 가능
_ENV_FLAVOR_MAPS: Dict[RuntimeEnv, Dict[str, str]] = {
    "prod": {
        "small": "m1.small",
        "medium": "m1.medium",
        "large": "m1.large",
    },
    "dev": {
        "small": "m1.tiny",  # dev 환경에서는 더 작은 인스턴스
        "medium": "m1.small",
        "large": "m1.medium",
    },
}


def get_openstack_flavor(
    recommended_flavor: str,
    runtime_env: RuntimeEnv = "prod",
    use_env_mapping: bool = False,
) -> str:
    """
    추천 flavor를 OpenStack flavor 이름으로 변환.

    Parameters
    ----------
    recommended_flavor : str
        추천된 flavor ("small", "medium", "large")
    runtime_env : RuntimeEnv
        실행 환경 ("prod", "dev")
    use_env_mapping : bool
        환경별 매핑 사용 여부 (기본값: False)

    Returns
    -------
    str
        OpenStack flavor 이름 (예: "m1.small", "m1.medium", "m1.large")

    Raises
    ------
    ValueError
        알 수 없는 recommended_flavor인 경우

    Examples
    --------
    >>> get_openstack_flavor("small")
    'm1.small'
    >>> get_openstack_flavor("medium", runtime_env="dev", use_env_mapping=True)
    'm1.small'
    """
    if use_env_mapping and runtime_env in _ENV_FLAVOR_MAPS:
        flavor_map = _ENV_FLAVOR_MAPS[runtime_env]
    else:
        flavor_map = _DEFAULT_FLAVOR_MAP

    if recommended_flavor not in flavor_map:
        raise ValueError(
            f"Unknown recommended_flavor: {recommended_flavor}. "
            f"Expected one of: {list(flavor_map.keys())}"
        )

    return flavor_map[recommended_flavor]


def get_flavor_specs(flavor_name: str) -> Dict[str, Optional[float]]:
    """
    OpenStack flavor 이름으로부터 예상 스펙 정보를 반환 (더미).

    향후 OpenStack API를 통해 실제 flavor 정보를 조회하도록 확장 가능.

    Parameters
    ----------
    flavor_name : str
        OpenStack flavor 이름

    Returns
    -------
    Dict[str, Optional[float]]
        flavor 스펙 정보 (vCPUs, RAM, Disk 등)
    """
    # 더미 스펙 테이블 (실제로는 OpenStack API로 조회)
    _FLAVOR_SPECS: Dict[str, Dict[str, Optional[float]]] = {
        "m1.tiny": {"vcpus": 1, "ram_mb": 512, "disk_gb": 1},
        "m1.small": {"vcpus": 1, "ram_mb": 2048, "disk_gb": 20},
        "m1.medium": {"vcpus": 2, "ram_mb": 4096, "disk_gb": 40},
        "m1.large": {"vcpus": 4, "ram_mb": 8192, "disk_gb": 80},
    }

    return _FLAVOR_SPECS.get(flavor_name, {"vcpus": None, "ram_mb": None, "disk_gb": None})

