# /app/core/context_extractor.py

"""
Context extractor module.

역할:
- 외부에서 들어온 raw context(dict 형태)를 내부 표준 스키마 MCPContext로 변환한다.
- 필수 필드 검증과 기본값 보정을 한 곳에서 처리한다.
- 잘못된 입력은 ContextValidationError로 통일해서 올려보낸다.
"""

from app.core.errors import ContextVaidationError
from app.models.common import MCPContext


def extract_context(raw_context: dict) -> MCPContext:
    """요청 본문에서 전달된 컨텍스트 딕셔너리를 Pydantic 모델로 변환."""
    try:
        return MCPContext(**raw_context)
    except Exception as e:
        raise ContextVaidationError(f"Invalid context data: {e}")
