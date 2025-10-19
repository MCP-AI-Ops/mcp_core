from app.core.errors import ContextVaidationError
from app.models.common import MCPContext
def extract_context(raw_context: dict) -> MCPContext:
    try:
        context = MCPContext(**raw_ctx)
        return context
    except Exception as e:
        raise ContextVaidationError(f"Invalid context data: {e}")
    return context