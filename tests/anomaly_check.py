import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print('이상 탐지 테스트 시작')

from app.core.predictor.baseline_predictor import BaselinePredictor
from app.core.policy import postprocess_predictions
from app.models.common import MCPContext

bp = BaselinePredictor()
ctx = MCPContext(
    context_id='anomaly-1',
    timestamp=datetime.utcnow(),
    service_type='web',
    runtime_env='prod',
    time_slot='peak',
    weight=1.0
)
pr = bp.run(service_id='svc-anom', metric_name='total_events', ctx=ctx, model_version='baseline_v1')
print('Baseline 결과 수:', len(pr.predictions))

res = postprocess_predictions(pr, ctx)
print('후처리 결과 수:', len(res.predictions))
print('이상 탐지 테스트 종료')
