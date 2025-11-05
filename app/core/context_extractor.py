from app.core.errors import ContextVaidationError
from app.models.common import MCPContext


def extract_context(raw_context: dict) -> MCPContext:
    """요청 본문에서 전달된 컨텍스트 딕셔너리를 Pydantic 모델로 변환."""
    try:
        return MCPContext(**raw_context)
    except Exception as e:
        raise ContextVaidationError(f"Invalid context data: {e}")
