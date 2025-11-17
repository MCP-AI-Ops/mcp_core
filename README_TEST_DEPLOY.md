# 전체 배포 플로우 테스트 가이드

GitHub URL과 자연어 입력부터 OpenStack VM 생성까지 전체 플로우를 테스트하는 스크립트입니다.

## 사전 준비사항

### 1. 환경변수 설정

`.env` 파일에 다음 환경변수를 설정하세요:

```bash
# Claude API (필수)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Backend API & MCP Core URL (기본값 사용 가능)
BACKEND_API_URL=http://localhost:8001
MCP_CORE_URL=http://localhost:8000

# GitHub Token (선택, Rate Limit 완화용)
GITHUB_TOKEN=ghp_...

# OpenStack 설정 (VM 배포 시 필요)
OS_AUTH_URL=http://localhost:5000/v3
OS_USERNAME=admin
OS_PASSWORD=devstack
OS_PROJECT_NAME=admin
OS_REGION_NAME=RegionOne

# OpenStack 리소스 이름 (선택, 기본값 사용 가능)
OPENSTACK_IMAGE_NAME=cirros-0.6.3-x86_64-disk
OPENSTACK_NETWORK_NAME=private
OPENSTACK_KEY_NAME=default
```

### 2. 서비스 실행

**Terminal 1: MCP Core 실행**
```bash
cd /home/stack/mcp_core
python3 -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2: Backend API 실행**
```bash
cd /home/stack/mcp_core
cd backend_api
python3 -m uvicorn main:app --reload --port 8001
```

## 테스트 실행

### 기본 테스트

```bash
cd /home/stack/mcp_core
python3 test_full_deploy_flow.py
```

기본 파라미터:
- GitHub URL: `https://github.com/fastapi/fastapi`
- 자연어 입력: `"피크타임에 5000명 정도 사용할 것 같아요"`

### 커스텀 파라미터로 테스트

```bash
python3 test_full_deploy_flow.py <github_url> <자연어 입력>
```

예시:
```bash
python3 test_full_deploy_flow.py https://github.com/django/django "평소에 1000명 정도 사용할 것 같아요"
```

## 테스트 플로우

스크립트는 다음 단계를 순차적으로 실행합니다:

1. **서비스 상태 확인**
   - Backend API (포트 8001) 헬스 체크
   - MCP Core (포트 8000) 헬스 체크

2. **Backend API 예측 요청**
   - GitHub URL로 저장소 메타데이터 수집
   - Claude API로 자연어를 구조화된 데이터로 변환
   - MCP Core `/plans` 호출하여 예측 수행
   - 추천 Flavor 및 예상 비용 반환

3. **OpenStack VM 배포**
   - MCP Core `/deploy` 엔드포인트 호출
   - `/plans`를 내부적으로 호출하여 예측 및 Flavor 추천 받기
   - OpenStack에 VM 생성
   - VM이 ACTIVE 상태가 될 때까지 대기

4. **VM 상태 확인**
   - 생성된 VM의 상태 조회
   - Instance ID, 이름, 상태, Flavor 등 정보 출력

## 예상 출력

```
============================================================
전체 배포 플로우 테스트
============================================================

[Step 1] 서비스 상태 확인
------------------------------------------------------------
✓ Backend API 연결 성공 (http://localhost:8001)
✓ MCP Core 연결 성공 (http://localhost:8000)

[Step 2] Backend API 예측 요청
------------------------------------------------------------
ℹ GitHub URL: https://github.com/fastapi/fastapi
ℹ 자연어 입력: 피크타임에 5000명 정도 사용할 것 같아요
✓ Backend API 예측 성공
ℹ   - Service Type: web
ℹ   - Expected Users: 5000
ℹ   - Time Slot: peak
ℹ   - CPU: 4.0
ℹ   - Memory: 8192.0
ℹ   - Recommended Flavor: medium
ℹ   - Expected Cost: $2.8/day

[Step 3] OpenStack VM 배포
------------------------------------------------------------
ℹ GitHub URL: https://github.com/fastapi/fastapi
ℹ   예측된 Flavor: medium
ℹ   예상 비용: $2.8/day
ℹ VM 생성 중... (이 작업은 몇 분이 걸릴 수 있습니다)
✓ VM 생성 성공!
ℹ   - Instance ID: abc123-def456-...
ℹ   - Instance Name: mcp-fastapi-20250113123456
ℹ   - Status: ACTIVE
ℹ   - Flavor: m1.medium
ℹ   - Image: cirros-0.6.3-x86_64-disk
ℹ   - Network: private
ℹ   - Plan ID: fastapi/fastapi
ℹ   - Message: VM created successfully: mcp-fastapi-20250113123456 (ACTIVE)

[Step 4] VM 상태 확인
------------------------------------------------------------
ℹ Instance ID: abc123-def456-...
✓ VM 상태 조회 성공
ℹ   - Status: ACTIVE

============================================================
✓ 전체 플로우 테스트 완료!
============================================================

생성된 VM 정보:
  Instance ID: abc123-def456-...
  상태 확인: http://localhost:8000/status/abc123-def456-...
  삭제: http://localhost:8000/destroy/abc123-def456-...
```

## 트러블슈팅

### 1. 서비스 연결 실패

**증상:** `Backend API 연결 실패` 또는 `MCP Core 연결 실패`

**해결:**
- 서비스가 실행 중인지 확인: `curl http://localhost:8000/health`
- 포트가 올바른지 확인
- 방화벽 설정 확인

### 2. Claude API 오류

**증상:** `Claude API key not set` 또는 `Claude API HTTP error`

**해결:**
- `.env` 파일에 `ANTHROPIC_API_KEY` 설정 확인
- Anthropic Console에서 API 키 발급 확인
- API 키 권한 확인

### 3. OpenStack 연결 실패

**증상:** `Missing OpenStack env vars` 또는 `Failed to create server`

**해결:**
- OpenStack 환경변수 설정 확인 (`OS_AUTH_URL`, `OS_USERNAME`, `OS_PASSWORD` 등)
- OpenStack 서비스가 실행 중인지 확인
- 이미지/네트워크/Flavor 이름 확인:
  ```bash
  openstack image list
  openstack network list
  openstack flavor list
  ```

### 4. VM 생성 타임아웃

**증상:** `VM 생성 타임아웃 (5분 초과)`

**해결:**
- OpenStack 리소스 상태 확인
- Nova 서비스 상태 확인
- 네트워크 설정 확인

## 참고사항

- VM 생성은 몇 분이 걸릴 수 있습니다 (기본 타임아웃: 5분)
- 테스트 후 생성된 VM은 수동으로 삭제해야 합니다:
  ```bash
  curl -X POST http://localhost:8000/destroy/<instance_id>
  ```
- OpenStack 리소스 이름은 환경에 따라 다를 수 있습니다. `.env` 파일에서 설정하세요.

