"""
MCP Core Client - MCP Core /plans 엔드포인트 호출 클라이언트
"""
import requests
from typing import Dict, Any


class MCPCoreClient:
    """MCP Core API 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Args:
            base_url: MCP Core 서버 URL
        """
        self.base_url = base_url.rstrip("/")
    
    def health_check(self) -> Dict[str, Any]:
        """MCP Core 헬스 체크"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def request_plans(self, plans_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Core /plans 엔드포인트 호출
        
        Args:
            plans_request: {
                "github_url": str,
                "metric_name": str,
                "context": dict
            }
        
        Returns:
            PlansResponse JSON
        
        Raises:
            ConnectionError: MCP Core 연결 실패
            ValueError: 요청 검증 실패
        """
        try:
            response = requests.post(
                f"{self.base_url}/plans",
                json=plans_request,
                timeout=30
            )
            
            if response.status_code == 400:
                raise ValueError(f"잘못된 요청: {response.json().get('detail', 'Unknown error')}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"MCP Core 서버에 연결할 수 없습니다: {self.base_url}")
        
        except requests.exceptions.Timeout:
            raise ConnectionError("MCP Core 응답 시간 초과 (30초)")
        
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"MCP Core API 오류: {e}")
