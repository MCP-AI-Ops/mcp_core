import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print('PYTHONPATH 설정 완료, 스모크 테스트 시작')

# Check model artifacts
model_path = 'models/best_mcp_lstm_model.h5'
meta_path = 'models/mcp_model_metadata.pkl'
print('모델 파일 존재 여부:', os.path.exists(model_path))
print('메타데이터 존재 여부:', os.path.exists(meta_path))

# Data source
try:
    from app.core.predictor.data_sources.factory import get_data_source
    ds = get_data_source()
    if getattr(ds, 'df', None) is None:
        print('데이터 소스에 CSV가 로드되지 않음')
    else:
        print('CSV 로드 행 수:', len(ds.df))
        vals = ds.fetch_historical_data(github_url='test', metric_name='total_events', hours=24)
        print('조회 데이터 형태:', getattr(vals, 'shape', None))
        print('샘플 값:', vals[:3])
except Exception as e:
    print('데이터 소스 오류:', e)

# Baseline predictor
try:
    from app.core.predictor.baseline_predictor import BaselinePredictor
    from app.models.common import MCPContext
    bp = BaselinePredictor()
    ctx = MCPContext(
        github_url='smoke-1',
        timestamp=datetime.utcnow(),
        service_type='web',
        runtime_env='prod',
        time_slot='normal',
        weight=1.0
    )
    pr = bp.run(github_url='svc-smoke', metric_name='total_events', ctx=ctx, model_version='baseline_v1')
    print('Baseline 예측 개수:', len(pr.predictions))
    print('첫 예측 값:', pr.predictions[0].value)
except Exception as e:
    print('Baseline 오류:', e)

print('스모크 테스트 종료')
