# app/core/router.py

"""
Router module.

역할:
- MCPContext 정보를 기반으로 어떤 모델 버전/경로를 쓸지 결정한다.
- 현재는 간단한 룰 매핑(dict)으로 동작하지만, 향후 DB나 YAML 기반 룰 테이블로 확장 가능하다.

핵심 개념:
- model_version 문자열에 'lstm'이 포함되면 plans 라우터에서 LSTMPredictor를 선택한다.
- 그 외에는 BaselinePredictor를 사용한다.
"""

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

def select_route(context: MCPContext) -> Tuple[str, str]:
    """
    컨텍스트 기반으로 사용할 모델 버전과 예측 경로 키워드를 결정한다.

    Parameters
    ----------
    ctx : MCPContext
        요청 서비스의 실행 환경(runtime_env), 부하 구간(time_slot), 서비스 타입(service_type)
        등의 메타데이터를 포함한다.

    Returns
    -------
    (model_version, path) : (str, str)
        model_version :
            예측기에 전달할 모델 식별자. 예:
            "web_peak_lstm_v1", "web_normal_v1", ...
            이 문자열에 'lstm'이 들어있으면 LSTMPredictor를 사용하고,
            그렇지 않으면 BaselinePredictor를 사용한다.
        path :
            예측 horizon / 파이프라인 분기 키워드. 현재는 "forecast_24h"로 고정.

    Notes
    -----
    - 이 레벨에서 실제 모델을 호출하지 않는다.
    - 단지 '어떤 모델을 쓸지'를 결정해서 상위 레이어(/plans)에게 알려준다.
    """

    key = (context.runtime_env, context.time_slot, context.service_type)
    model_version = _RULES.get(key, _DEFAULT_MODEL)
    path = "forecast_24h"
    return model_version, path