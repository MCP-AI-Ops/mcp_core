#!/usr/bin/env python3
"""
전체 배포 플로우 테스트 스크립트

GitHub URL + 자연어 입력부터 OpenStack VM 생성까지 전체 플로우를 테스트합니다.

사용법:
    python test_full_deploy_flow.py

환경변수:
    BACKEND_API_URL: Backend API URL (기본: http://localhost:8001)
    MCP_CORE_URL: MCP Core URL (기본: http://localhost:8000)
    ANTHROPIC_API_KEY: Claude API 키 (필수)
    GITHUB_TOKEN: GitHub API 토큰 (선택)
"""

import os
import sys
import json
import time
import httpx
from typing import Dict, Any
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 기본 설정
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
MCP_CORE_URL = os.getenv("MCP_CORE_URL", "http://localhost:8000")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 색상 출력
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num: int, description: str):
    """단계 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {step_num}]{Colors.END} {description}")
    print("-" * 60)


def print_success(message: str):
    """성공 메시지 출력"""
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def print_error(message: str):
    """에러 메시지 출력"""
    print(f"{Colors.RED}✗{Colors.END} {message}")


def print_info(message: str):
    """정보 메시지 출력"""
    print(f"{Colors.YELLOW}ℹ{Colors.END} {message}")


def check_services():
    """서비스 상태 확인"""
    print_step(1, "서비스 상태 확인")
    
    services = {
        "Backend API": BACKEND_API_URL,
        "MCP Core": MCP_CORE_URL,
    }
    
    all_ok = True
    for name, url in services.items():
        try:
            response = httpx.get(f"{url}/health", timeout=5.0)
            if response.status_code == 200:
                print_success(f"{name} 연결 성공 ({url})")
            else:
                print_error(f"{name} 응답 오류: {response.status_code}")
                all_ok = False
        except Exception as e:
            print_error(f"{name} 연결 실패: {e}")
            all_ok = False
    
    if not ANTHROPIC_API_KEY:
        print_error("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print_info("Claude API를 사용할 수 없지만 테스트는 계속 진행됩니다.")
    
    return all_ok


def test_backend_api_predict(github_url: str, user_input: str) -> Dict[str, Any]:
    """Backend API로 예측 요청"""
    print_step(2, f"Backend API 예측 요청")
    print_info(f"GitHub URL: {github_url}")
    print_info(f"자연어 입력: {user_input}")
    
    request_data = {
        "github_url": github_url,
        "user_input": user_input,
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{BACKEND_API_URL}/api/predict",
                json=request_data
            )
            
            if response.status_code != 200:
                print_error(f"Backend API 오류: {response.status_code}")
                print_error(f"응답: {response.text}")
                raise Exception(f"Backend API failed: {response.status_code}")
            
            result = response.json()
            print_success("Backend API 예측 성공")
            
            # 결과 출력
            if "extracted_context" in result:
                ctx = result["extracted_context"]
                print_info(f"  - Service Type: {ctx.get('service_type')}")
                print_info(f"  - Expected Users: {ctx.get('expected_users')}")
                print_info(f"  - Time Slot: {ctx.get('time_slot')}")
                print_info(f"  - CPU: {ctx.get('curr_cpu')}")
                print_info(f"  - Memory: {ctx.get('curr_mem')}")
            
            if "recommendations" in result:
                rec = result["recommendations"]
                print_info(f"  - Recommended Flavor: {rec.get('flavor')}")
                print_info(f"  - Expected Cost: ${rec.get('cost_per_day')}/day")
            
            return result
            
    except Exception as e:
        print_error(f"Backend API 호출 실패: {e}")
        raise


def test_deploy(github_url: str, predict_result: Dict[str, Any] = None) -> Dict[str, Any]:
    """MCP Core Deploy 엔드포인트로 VM 생성"""
    print_step(3, f"OpenStack VM 배포")
    print_info(f"GitHub URL: {github_url}")
    
    request_data = {
        "github_url": github_url,
        "repo_id": github_url.split("/")[-1],
        "image_tag": "latest",
        "env_config": {}
    }
    
    # 예측 결과가 있으면 plan_id 추가
    if predict_result and "recommendations" in predict_result:
        rec = predict_result["recommendations"]
        print_info(f"  예측된 Flavor: {rec.get('flavor')}")
        print_info(f"  예상 비용: ${rec.get('cost_per_day')}/day")
    
    try:
        print_info("VM 생성 중... (이 작업은 몇 분이 걸릴 수 있습니다)")
        
        with httpx.Client(timeout=300.0) as client:  # 5분 타임아웃
            response = client.post(
                f"{MCP_CORE_URL}/deploy",
                json=request_data
            )
            
            if response.status_code != 200:
                print_error(f"Deploy API 오류: {response.status_code}")
                print_error(f"응답: {response.text}")
                raise Exception(f"Deploy API failed: {response.status_code}")
            
            result = response.json()
            print_success("VM 생성 성공!")
            
            # 결과 출력
            if "instance" in result:
                instance = result["instance"]
                print_info(f"  - Instance ID: {instance.get('instance_id')}")
                print_info(f"  - Instance Name: {instance.get('name')}")
                print_info(f"  - Status: {instance.get('status')}")
                print_info(f"  - Flavor: {instance.get('flavor_name')}")
                print_info(f"  - Image: {instance.get('image_name')}")
                print_info(f"  - Network: {instance.get('network_name')}")
                
                if "addresses" in instance:
                    print_info(f"  - Addresses: {json.dumps(instance['addresses'], indent=2)}")
            
            print_info(f"  - Plan ID: {result.get('plan_id')}")
            print_info(f"  - Message: {result.get('message')}")
            
            return result
            
    except httpx.TimeoutException:
        print_error("VM 생성 타임아웃 (5분 초과)")
        raise
    except Exception as e:
        print_error(f"VM 배포 실패: {e}")
        raise


def verify_vm_status(instance_id: str, github_url: str):
    """VM 상태 확인

    주의: 현재 MCP Core의 /status 엔드포인트는
    - 메소드: POST
    - URL: /status
    - Body: {"github_url": "..."}
    형태를 기대하므로, 테스트 코드도 이에 맞춰 호출한다.
    """
    print_step(4, "VM 상태 확인")
    print_info(f"Instance ID: {instance_id}")
    print_info(f"GitHub URL: {github_url}")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MCP_CORE_URL}/status",
                json={"github_url": github_url},
            )

            if response.status_code == 200:
                result = response.json()
                print_success("VM 상태 조회 성공")
                print_info(f"  - GitHub URL: {result.get('github_url')}")
                print_info(f"  - Instance ID(더미): {result.get('instance_id')}")
                print_info(f"  - CPU Usage: {result.get('cpu_usage')}")
                print_info(f"  - Mem Usage: {result.get('mem_usage')}")
                print_info(f"  - Healthy: {result.get('is_healthy')}")
                return result
            else:
                print_error(f"상태 조회 실패: {response.status_code}")
                return None

    except Exception as e:
        print_error(f"VM 상태 확인 실패: {e}")
        return None


def main():
    """메인 테스트 함수"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}전체 배포 플로우 테스트{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    
    # 테스트 파라미터
    github_url = "https://github.com/fastapi/fastapi"
    user_input = "피크타임에 1명 정도 사용할 것 같아요"
    
    # 사용자 입력 받기 (선택적)
    if len(sys.argv) > 1:
        github_url = sys.argv[1]
    if len(sys.argv) > 2:
        user_input = " ".join(sys.argv[2:])
    
    print(f"\n{Colors.BOLD}테스트 파라미터:{Colors.END}")
    print(f"  GitHub URL: {github_url}")
    print(f"  자연어 입력: {user_input}")
    
    try:
        # 1. 서비스 상태 확인
        if not check_services():
            print_error("일부 서비스가 연결되지 않았습니다. 계속 진행할까요? (y/n)")
            if input().lower() != 'y':
                sys.exit(1)
        
        # 2. Backend API로 예측 요청
        predict_result = test_backend_api_predict(github_url, user_input)
        
        # 3. Deploy로 VM 생성 (예측 결과 전달)
        deploy_result = test_deploy(github_url, predict_result)
        
        instance_id = deploy_result.get("instance_id")
        if instance_id:
            # 4. VM 상태 확인
            time.sleep(2)  # 잠시 대기
            verify_vm_status(instance_id, github_url)
        
        # 최종 결과 출력
        print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}✓ 전체 플로우 테스트 완료!{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.END}")
        
        print(f"\n{Colors.BOLD}생성된 VM 정보:{Colors.END}")
        if instance_id:
            print(f"  Instance ID: {instance_id}")
            print(f"  상태 확인: {MCP_CORE_URL}/status/{instance_id}")
            print(f"  삭제: {MCP_CORE_URL}/destroy/{instance_id}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}테스트가 사용자에 의해 중단되었습니다.{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}{'='*60}{Colors.END}")
        print(f"{Colors.RED}✗ 테스트 실패: {e}{Colors.END}")
        print(f"{Colors.RED}{'='*60}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

