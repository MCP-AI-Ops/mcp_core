# /app/core/context_extractor.py

"""
Context extractor module.

역할:
- 외부에서 들어온 raw context(dict 형태)를 내부 표준 스키마 MCPContext로 변환한다.
- 필수 필드 검증과 기본값 보정을 한 곳에서 처리한다.
- 잘못된 입력은 ContextValidationError로 통일해서 올려보낸다.
- 프론트엔드에서 최소한의 정보만 보내도 나머지 필드를 자동으로 채운다.
"""

from datetime import datetime
from app.core.errors import ContextVaidationError
from app.models.common import MCPContext


def extract_context(raw_context: dict) -> MCPContext:
    """
    요청 본문에서 전달된 컨텍스트 딕셔너리를 Pydantic 모델로 변환.
    프론트엔드에서 최소한의 정보(github_url, expected_users)만 보내도
    나머지 필드를 자동으로 채운다.
    """
    try:
        # 프론트엔드에서 github_url을 보내면 context_id로 사용
        # context_id가 없으면 github_url을 context_id로 사용
        if "github_url" in raw_context and "context_id" not in raw_context:
            raw_context["context_id"] = raw_context["github_url"]
        
        # 필수 필드 기본값 설정
        if "timestamp" not in raw_context:
            raw_context["timestamp"] = datetime.utcnow()
        
        if "service_type" not in raw_context:
            raw_context["service_type"] = "web"
        
        if "runtime_env" not in raw_context:
            raw_context["runtime_env"] = "prod"
        
        if "time_slot" not in raw_context:
            raw_context["time_slot"] = "normal"
        
        if "weight" not in raw_context:
            raw_context["weight"] = 1.0
        
        return MCPContext(**raw_context)
    except Exception as e:
        raise ContextVaidationError(f"Invalid context data: {e}")
