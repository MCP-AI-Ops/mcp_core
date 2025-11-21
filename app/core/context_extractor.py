"""
Context extractor module.

역할:
- 외부에서 들어온 raw context(dict 형태)를 내부 표준 스키마 MCPContext로 변환한다.
- 필수 필드 검증과 기본값 보정을 한 곳에서 처리한다.
- 잘못된 입력은 ContextValidationError로 통일해서 올려보낸다.
- 프론트엔드에서 최소한의 정보만 보내도 나머지 필드를 자동으로 채운다.
"""
from pydantic import ValidationError


from datetime import datetime
from app.core.errors import ContextValidationError
from app.models.common import MCPContext


def extract_context(raw_context: dict) -> MCPContext:
    """요청 본문에서 전달된 컨텍스트 딕셔너리를 표준 MCPContext로 변환.

    - 클라이언트 간 필드 명칭 차이를 흡수 
    - current_users -> expected_users, cpu->curr_cpu, memory->curr_mem)
    - timestamp 기본값 보정 (서버 시각)
    - github_url 미지정 허용 (None)
    """
    try:
        ctx = dict(raw_context or {})

        # 필드 매핑 (하위 호환)
        if "expected_users" not in ctx and "current_users" in ctx:
            ctx["expected_users"] = ctx.get("current_users")
        if "curr_cpu" not in ctx and "cpu" in ctx:
            ctx["curr_cpu"] = ctx.get("cpu")
        if "curr_mem" not in ctx and "memory" in ctx:
            ctx["curr_mem"] = ctx.get("memory")

        # 기본값 채우기
        ctx.setdefault("timestamp", datetime.utcnow())

        return MCPContext(**ctx)
    except Exception as e:
        # 통합된 예외 타입으로 래핑
        raise ContextValidationError(f"Invalid context data: {e}")
