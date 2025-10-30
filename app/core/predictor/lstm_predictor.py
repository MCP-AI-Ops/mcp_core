"""
LSTM Predictor (Production Ready)
더미 제거, 실패 시 예외 발생 (Baseline이 처리)
"""

import os
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime, timedelta

from app.models.common import MCPContext, PredictionResult, PredictionPoint
from .base import BasePredictor
from .data_sources import get_data_source
from app.core.errors import PredictionError


MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MODEL_PATH = MODEL_DIR / "best_mcp_lstm_model.h5"
METADATA_PATH = MODEL_DIR / "mcp_model_metadata.pkl"


class LSTMPredictor(BasePredictor):
    """LSTM 기반 시계열 예측기"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.metadata = None
        
        self._load_models()
        self.data_source = get_data_source()
        print(f"✅ LSTM Predictor initialized")
    
    def _load_models(self):
        """모델 및 메타데이터 로드"""
        try:
            import tensorflow as tf
            
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
            
            self.model = tf.keras.models.load_model(str(MODEL_PATH))
            print(f"✅ Loaded model: {MODEL_PATH.name}")
            
            if METADATA_PATH.exists():
                with open(METADATA_PATH, "rb") as f:
                    self.metadata = pickle.load(f)
                
                if isinstance(self.metadata, dict):
                    self.scaler = self.metadata.get('scaler')
                else:
                    self.scaler = self.metadata
                
                print(f"✅ Loaded metadata with scaler")
            
        except Exception as e:
            print(f"❌ Model load failed: {e}")
            raise PredictionError(f"Failed to initialize LSTM model: {e}")
    
    def run(
        self,
        *,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str
    ) -> PredictionResult:
        """LSTM 예측 실행"""
        
        # 1. 모델 체크
        if self.model is None:
            raise PredictionError("LSTM model not loaded")
        
        # 2. 데이터 조회
        historical_data = self.data_source.fetch_historical_data(
            service_id=service_id,
            metric_name=metric_name,
            hours=168
        )
        print(f"📊 Fetched {len(historical_data)} datapoints")
        
        # 3. 전처리
        X = self._preprocess(historical_data)
        
        # 4. 예측
        y_pred_scaled = self.model.predict(X, verbose=0)
        
        # 5. 역변환
        if self.scaler is not None:
            y_pred = self.scaler.inverse_transform(
                y_pred_scaled.reshape(-1, 1)
            ).flatten()
        else:
            y_pred = y_pred_scaled.flatten()
        
        # 6. 후처리
        y_pred = np.clip(y_pred, 0, None)
        
        if metric_name == "total_events":
            y_pred = np.round(y_pred).astype(int)
        
        print(f"✅ Prediction: {y_pred.min():.2f} ~ {y_pred.max():.2f}")
        
        # 7. 결과 생성
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        predictions = [
            PredictionPoint(
                time=now + timedelta(hours=k),
                value=float(y_pred[k-1])
            )
            for k in range(1, min(25, len(y_pred) + 1))
        ]
        
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=predictions
        )
    
    def _preprocess(self, data: np.ndarray) -> np.ndarray:
        """데이터 전처리"""
        
        if self.scaler is not None:
            scaled = self.scaler.transform(data.reshape(-1, 1)).flatten()
        else:
            mean, std = data.mean(), data.std()
            scaled = (data - mean) / std if std > 0 else data - mean
        
        return scaled.reshape(1, 168, 1)