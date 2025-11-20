# tests/test_flavor_mapper.py

"""
flavor_mapper 모듈 단위 테스트.
"""

import pytest

from app.core.openstack.flavor_mapper import (
    get_openstack_flavor,
    get_flavor_specs,
)


def test_get_openstack_flavor_default_mapping():
    """기본 flavor 매핑 테스트."""
    assert get_openstack_flavor("small") == "m1.small"
    assert get_openstack_flavor("medium") == "m1.medium"
    assert get_openstack_flavor("large") == "m1.large"


def test_get_openstack_flavor_with_env_mapping_prod():
    """prod 환경 flavor 매핑 테스트."""
    assert get_openstack_flavor("small", runtime_env="prod", use_env_mapping=True) == "m1.small"
    assert get_openstack_flavor("medium", runtime_env="prod", use_env_mapping=True) == "m1.medium"
    assert get_openstack_flavor("large", runtime_env="prod", use_env_mapping=True) == "m1.large"


def test_get_openstack_flavor_with_env_mapping_dev():
    """dev 환경 flavor 매핑 테스트 (더 작은 인스턴스 사용)."""
    assert get_openstack_flavor("small", runtime_env="dev", use_env_mapping=True) == "m1.tiny"
    assert get_openstack_flavor("medium", runtime_env="dev", use_env_mapping=True) == "m1.small"
    assert get_openstack_flavor("large", runtime_env="dev", use_env_mapping=True) == "m1.medium"


def test_get_openstack_flavor_invalid_flavor():
    """알 수 없는 flavor는 ValueError 발생."""
    with pytest.raises(ValueError, match="Unknown recommended_flavor"):
        get_openstack_flavor("xlarge")


def test_get_openstack_flavor_env_mapping_disabled():
    """use_env_mapping=False인 경우 기본 매핑 사용."""
    # dev 환경이지만 use_env_mapping=False이므로 기본 매핑 사용
    assert get_openstack_flavor("small", runtime_env="dev", use_env_mapping=False) == "m1.small"


def test_get_flavor_specs():
    """flavor 스펙 조회 테스트."""
    specs = get_flavor_specs("m1.small")
    
    assert specs["vcpus"] == 1
    assert specs["ram_mb"] == 2048
    assert specs["disk_gb"] == 20


def test_get_flavor_specs_unknown_flavor():
    """알 수 없는 flavor는 None 반환."""
    specs = get_flavor_specs("unknown.flavor")
    
    assert specs["vcpus"] is None
    assert specs["ram_mb"] is None
    assert specs["disk_gb"] is None


def test_get_flavor_specs_all_flavors():
    """모든 정의된 flavor의 스펙이 올바른지 확인."""
    flavors = ["m1.tiny", "m1.small", "m1.medium", "m1.large"]
    
    for flavor in flavors:
        specs = get_flavor_specs(flavor)
        assert specs["vcpus"] is not None
        assert specs["ram_mb"] is not None
        assert specs["disk_gb"] is not None
        assert specs["vcpus"] > 0
        assert specs["ram_mb"] > 0
        assert specs["disk_gb"] > 0

