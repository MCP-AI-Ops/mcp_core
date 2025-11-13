# OpenStack 연동 및 테스트 가이드

## 1. OpenStack Flavor 매핑

### 개요
`recommended_flavor` ("small", "medium", "large")를 OpenStack flavor 이름으로 변환하는 모듈을 추가했습니다.

### 파일 위치
- `app/core/openstack/flavor_mapper.py`: Flavor 매핑 로직
- `app/core/openstack/__init__.py`: 모듈 초기화

### 사용 방법

#### 기본 매핑
```python
from app.core.openstack.flavor_mapper import get_openstack_flavor

# 기본 매핑 사용
flavor = get_openstack_flavor("small")  # "m1.small"
flavor = get_openstack_flavor("medium")  # "m1.medium"
flavor = get_openstack_flavor("large")   # "m1.large"
```

#### 환경별 매핑
```python
# dev 환경에서는 더 작은 인스턴스 사용
flavor = get_openstack_flavor(
    recommended_flavor="medium",
    runtime_env="dev",
    use_env_mapping=True
)  # "m1.small" (dev 환경에서는 medium → small)
```

### 매핑 테이블

#### 기본 매핑
- `small` → `m1.small`
- `medium` → `m1.medium`
- `large` → `m1.large`

#### Prod 환경 매핑
- `small` → `m1.small`
- `medium` → `m1.medium`
- `large` → `m1.large`

#### Dev 환경 매핑
- `small` → `m1.tiny`
- `medium` → `m1.small`
- `large` → `m1.medium`

### deploy.py 연동

`app/routes/deploy.py`에서 `recommended_flavor`를 OpenStack flavor로 변환:

```python
# env_config에 recommended_flavor가 포함된 경우
recommended_flavor = req.env_config.get("recommended_flavor")
runtime_env = req.env_config.get("runtime_env", "prod")

if recommended_flavor:
    openstack_flavor = get_openstack_flavor(
        recommended_flavor=recommended_flavor,
        runtime_env=runtime_env,
        use_env_mapping=False,  # 필요시 True로 변경
    )
```

### 향후 확장
- OpenStack API를 통해 실제 flavor 목록 조회
- 리전별 flavor 매핑 지원
- 동적 flavor 스펙 조회 (`get_flavor_specs` 함수 활용)

## 2. 단위 테스트

### 추가된 테스트 파일
1. `tests/test_context_extractor.py`: Context 추출 및 검증 테스트
2. `tests/test_router.py`: 라우팅 로직 테스트
3. `tests/test_baseline_predictor.py`: Baseline 예측기 테스트
4. `tests/test_flavor_mapper.py`: Flavor 매핑 테스트

### 테스트 실행

```bash
# 모든 테스트 실행
poetry run pytest tests/ -v

# 특정 테스트 파일 실행
poetry run pytest tests/test_context_extractor.py -v

# 특정 테스트 함수 실행
poetry run pytest tests/test_router.py::test_select_route_prod_peak_web -v
```

### 테스트 커버리지

#### context_extractor 테스트
- ✅ 유효한 context 변환
- ✅ 기본값 적용
- ✅ 잘못된 service_type 검증
- ✅ 필수 필드 누락 검증
- ✅ 잘못된 time_slot 검증
- ✅ 음수 weight 검증
- ✅ 선택적 필드 포함

#### router 테스트
- ✅ 모든 정의된 조합 (prod/dev × peak/normal/low/weekend × web)
- ✅ 기본값 폴백 (매핑되지 않은 조합)
- ✅ path 반환값 확인

#### baseline_predictor 테스트
- ✅ 데이터 소스가 있는 경우 예측
- ✅ 데이터 소스가 없는 경우 폴백
- ✅ 다양한 context로 예측
- ✅ 예측 결과 시간 순서 확인

#### flavor_mapper 테스트
- ✅ 기본 매핑
- ✅ 환경별 매핑 (prod/dev)
- ✅ 잘못된 flavor 에러 처리
- ✅ Flavor 스펙 조회

### 테스트 실행 결과
```
tests/test_flavor_mapper.py::test_get_openstack_flavor_default_mapping PASSED
tests/test_context_extractor.py::test_extract_context_valid PASSED
tests/test_router.py::test_select_route_all_combinations PASSED
...
============================== 22 passed in 0.32s ===============================
```

## 3. 다음 단계

### OpenStack 실제 연동
1. `app/core/openstack/vm_manager.py` 생성
   - OpenStack SDK를 사용한 VM 생성
   - Flavor 매핑 결과를 실제 VM 생성에 사용

2. `deploy.py` 수정
   - `vm_manager.create_vm()` 호출
   - 실제 인스턴스 ID 반환

3. 환경 변수 설정
   - OpenStack 인증 정보 (OS_AUTH_URL, OS_USERNAME, OS_PASSWORD 등)

### 테스트 확장
- OpenStack Mock을 사용한 통합 테스트
- 실제 OpenStack 환경과의 통합 테스트 (선택적)

