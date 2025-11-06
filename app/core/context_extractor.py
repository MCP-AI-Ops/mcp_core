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
    """
    요청 바디에 포함된 'context' dict를 MCPContext(Pydantic 모델)로 파싱한다.

    이 함수는 다음을 보장한다:
    - 필수 필드(runtime_env, time_slot, service_type 등)가 존재하지 않거나 타입이 맞지 않을 경우
      ContextValidationError를 발생시킨다.
    - weight 등 일부 필드는 Pydantic 내부 기본값에 의해 보정된다.
      (예: 제공되지 않은 경우에도 기본 가중치가 설정됨)

    Parameters
    ----------
    raw_ctx : dict
        클라이언트가 /plans 요청 시 전송한 context JSON 조각.

    Returns
    -------
    MCPContext
        검증된 Context 오브젝트. 이후 router, predictor, policy 단계에서 신뢰 가능한 형태로 사용된다.

    Raises
    ------
    ContextValidationError
        context 형식이 잘못되었거나 필수 값이 누락된 경우.
    """

    try:
        context = MCPContext(**raw_ctx)
        return context
    except Exception as e:
        raise ContextVaidationError(f"Invalid context data: {e}")
    return context