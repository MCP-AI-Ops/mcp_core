"""
이상탐지 + 디스코드 알림 테스트

목적:
- /plans API를 호출해서 이상탐지 트리거
- Discord 웹훅으로 알림 전송 확인

방법:
- 실제 데이터보다 훨씬 높은 예측값을 강제로 만들어서 Z-score >= 3.0 달성
"""
import requests
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# MCP Core URL
MCP_CORE_URL = "http://localhost:8000"

# 디스코드 웹훅 확인
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
if not DISCORD_WEBHOOK:
    print("경고: DISCORD_WEBHOOK_URL이 설정되지 않았습니다!")
    print("   .env 파일에 DISCORD_WEBHOOK_URL을 추가하세요.")
else:
    print(f"Discord 웹훅 설정됨: {DISCORD_WEBHOOK[:50]}...")


def test_normal_prediction():
    """정상 예측 테스트 (이상탐지 발동 안 됨)"""
    print("\n" + "="*60)
    print("테스트 1: 정상 예측 (이상탐지 발동 안 됨)")
    print("="*60)
    
    payload = {
        "github_url": "test-service-normal",
        "metric_name": "total_events",
        "context": {
            "service_type": "api",
            "expected_users": 100,
            "time_slot": "normal",
            "curr_cpu": 2,
            "curr_mem": 4096
        }
    }
    
    response = requests.post(f"{MCP_CORE_URL}/plans", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"예측 성공")
        print(f"   - 모델: {result['prediction']['model_version']}")
        print(f"   - 예측 개수: {len(result['prediction']['predictions'])}")
        print(f"   - 권장 인스턴스: {result['recommended_flavor']}")
        print(f"   - 예상 비용: ${result['expected_cost_per_day']:.2f}/일")
    else:
        print(f"❌ 예측 실패: {response.status_code}")
        print(response.text)


def test_anomaly_trigger():
    """이상탐지 트리거 테스트"""
    print("\n" + "="*60)
    print("테스트 2: 이상탐지 트리거 (높은 사용자 수)")
    print("="*60)
    
    # 매우 높은 사용자 수로 강제 스파이크 유도
    # current_users를 극단적으로 높게 설정
    payload = {
        "github_url": "test-anomaly-spike",
        "metric_name": "total_events",
        "context": {
            "service_type": "web",
            "expected_users": 100000,  # 매우 높은 사용자 수
            "time_slot": "peak",
            "curr_cpu": 16,
            "curr_mem": 32768
        }
    }
    
    print(f"📊 테스트 컨텍스트:")
    print(f"   - 사용자: {payload['context']['current_users']:,}명")
    print(f"   - 시간대: {payload['context']['time_slot']}")
    print(f"   - CPU: {payload['context']['cpu']} vCPU")
    print(f"   - Memory: {payload['context']['memory']} MB")
    
    response = requests.post(f"{MCP_CORE_URL}/plans", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n예측 완료")
        print(f"   - 모델: {result['prediction']['model_version']}")
        print(f"   - 예측 개수: {len(result['prediction']['predictions'])}")
        
        # 예측값 확인
        predictions = result['prediction']['predictions']
        max_pred = max(p['value'] for p in predictions)
        avg_pred = sum(p['value'] for p in predictions) / len(predictions)
        
        print(f"\n예측 통계:")
        print(f"   - 최대값: {max_pred:.2f}")
        print(f"   - 평균값: {avg_pred:.2f}")
        print(f"   - 권장 인스턴스: {result['recommended_flavor']}")
        print(f"   - 예상 비용: ${result['expected_cost_per_day']:.2f}/일")
        
        # 이상탐지 여부 확인 (응답에 포함되지 않지만 서버 로그에서 확인 가능)
        print(f"\n이상탐지 결과:")
        print(f"   서버 로그를 확인하세요!")
        print(f"   Discord 알림이 전송되었는지 확인하세요!")
        
    else:
        print(f"❌ 예측 실패: {response.status_code}")
        print(response.text)


def test_github_repo_analysis():
    """실제 GitHub 저장소로 테스트"""
    print("\n" + "="*60)
    print("테스트 3: 실제 GitHub 저장소 분석 (대형 프로젝트)")
    print("="*60)
    
    # 매우 인기 있는 저장소 (이상탐지 가능성 높음)
    repos_to_test = [
        "https://github.com/facebook/react",  # 228k stars
        "https://github.com/tensorflow/tensorflow",  # 186k stars
        "https://github.com/torvalds/linux",  # 180k stars
    ]
    
    print("테스트 대상 저장소:")
    for repo in repos_to_test:
        print(f"   - {repo}")
    
    print("\n사용 방법:")
    print("   1. MCP Core 서버 실행: python -m uvicorn app.main:app --reload")
    print("   2. Claude Desktop에서 다음 명령:")
    print(f"      'https://github.com/facebook/react를 완전 분석해줘'")
    print("   3. Discord에서 알림 확인")


if __name__ == "__main__":
    print("이상탐지 + 디스코드 알림 테스트")
    print("="*60)
    
    # 서버 연결 확인
    try:
        response = requests.get(f"{MCP_CORE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"MCP Core 서버 연결 성공: {MCP_CORE_URL}")
        else:
            print(f"MCP Core 서버 응답 이상: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ MCP Core 서버 연결 실패!")
        print(f"   서버를 먼저 실행하세요: python -m uvicorn app.main:app --reload")
        exit(1)
    
    # 테스트 실행
    test_normal_prediction()
    test_anomaly_trigger()
    test_github_repo_analysis()
    
    print("\n" + "="*60)
    print("모든 테스트 완료!")
    print("="*60)
    print("\n다음 단계:")
    print("   1. 서버 로그에서 'anomaly_detected' 메시지 확인")
    print("   2. Discord 채널에서 알림 메시지 확인")
    print("   3. 데이터베이스에서 anomaly_detections 테이블 확인 (선택)")
