from typing import Tuple
from app.models.common import MCPContext

# 일단 단순한 룰 먼저 생성해둠. 실제로는 어떤 케이스 있을지 좀 더 나눠봐야 할듯?
_RULES = {
    ("prod", "peak", "web"): "web_peak_v1",
    ("prod", "normal", "web"): "web_normal_v1",
    ("prod", "low", "web"): "web_low_v1",
    ("prod", "weekend", "web"): "web_weekend_v1",
    ("dev", "peak", "web"): "web_dev_peak_v1",
    ("dev", "normal", "web"): "web_dev_normal_v1",
    ("dev", "low", "web"): "web_dev_low_v1",
    ("dev", "weekend", "web"): "web_dev_weekend_v1",
}

_DEFAULT_MODEL = "default_fallback_v1"

def select_router(context: MCPContext) -> Tuple[str, str]:
    key = (context.runtime_env, context.time_slot, context.service_type)
    model_version = _RULES.get(key, _DEFAULT_MODEL)
    path = "forecast_24h"
    return path, model_version