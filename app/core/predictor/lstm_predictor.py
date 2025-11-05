"""
LSTM Predictor - FastAPI 통합 버전
"""

import os
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
from typing import Optional

from app.models.common import MCPContext, PredictionResult, PredictionPoint
from app.core.predictor.base import BasePredictor
from app.core.errors import PredictionError


class LSTMPredictor(BasePredictor):
    """실제 LSTM 모델 사용"""

    def __init__(self, 
                 model_path: str = "models/best_mcp_lstm_model.h5",
                 metadata_path: str = "models/mcp_model_metadata.pkl",
                 csv_path: str = "data/lstm_ready_cluster_data.csv"):
        
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.csv_path = csv_path
        
        # 모델 & 메타데이터
        self.model = None
        self.metadata = None
        self.feature_scaler = None
        self.target_scaler = None
        self.feature_names = None
        self.sequence_length = None
        self.use_log_transform = None
        
        # CSV 데이터
        self.df = None
        
        # 초기화
        self._load_model()
        self._load_metadata()
        self._load_csv_data()
        
        print(f"✓ LSTMPredictor 초기화 완료")

    def _load_model(self):
        """모델 로드"""
        if not os.path.exists(self.model_path):
            raise PredictionError(f"모델 파일 없음: {self.model_path}")
        
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            print(f"✓ 모델 로드: {self.model_path}")
        except Exception as e:
            raise PredictionError(f"모델 로드 실패: {e}")

    def _load_metadata(self):
        """메타데이터 로드"""
        if not os.path.exists(self.metadata_path):
            raise PredictionError(f"메타데이터 파일 없음: {self.metadata_path}")
        
        try:
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            self.feature_scaler = self.metadata['scaler']
            self.target_scaler = self.metadata['target_scaler']
            self.feature_names = self.metadata['feature_names']
            self.sequence_length = self.metadata['sequence_length']
            self.use_log_transform = self.metadata.get('use_log_transform', False)
            
            print(f"✓ 메타데이터 로드 완료")
        except Exception as e:
            raise PredictionError(f"메타데이터 로드 실패: {e}")

    def _load_csv_data(self):
        """CSV 데이터 로드"""
        if not os.path.exists(self.csv_path):
            print(f"⚠️  CSV 없음: {self.csv_path}")
            self.df = None
            return
        
        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"✓ CSV 로드: {len(self.df)}행")
        except Exception as e:
            print(f"⚠️  CSV 로드 실패: {e}")
            self.df = None

    def run(self, 
            *, 
            service_id: str, 
            metric_name: str, 
            ctx: MCPContext, 
            model_version: str) -> PredictionResult:
        """24시간 예측"""
        
        # 1. 데이터 확인
        if self.df is None:
            raise PredictionError("CSV 데이터 없음")
        
        # 2. 최근 데이터 가져오기
        recent_df = self.df.tail(self.sequence_length)
        
        if len(recent_df) < self.sequence_length:
            raise PredictionError(f"데이터 부족: {len(recent_df)} < {self.sequence_length}")
        
        try:
            recent_data = recent_df[self.feature_names].values
        except KeyError as e:
            raise PredictionError(f"피처 누락: {e}")
        
        # 3. 전처리
        try:
            features_scaled = self.feature_scaler.transform(recent_data)
            X = features_scaled.reshape(1, self.sequence_length, -1)
        except Exception as e:
            raise PredictionError(f"전처리 실패: {e}")
        
        # 4. 24시간 예측
        try:
            predictions = []
            current_sequence = X.copy()
            
            for _ in range(24):
                # 예측
                pred_scaled = self.model.predict(current_sequence, verbose=0)[0, 0]
                
                # 역변환
                pred = self.target_scaler.inverse_transform([[pred_scaled]])[0, 0]
                
                # 로그 변환 되돌리기
                if self.use_log_transform:
                    pred = np.expm1(pred)
                
                # 음수 클리핑
                pred = max(pred, 0)
                
                predictions.append(pred)
                
                # 다음 시퀀스 업데이트
                new_features = current_sequence[0, -1, :].copy()
                new_row = np.concatenate([[pred_scaled], new_features[1:]])
                current_sequence = np.append(
                    current_sequence[:, 1:, :], 
                    new_row.reshape(1, 1, -1), 
                    axis=1
                )
            
        except Exception as e:
            raise PredictionError(f"예측 실패: {e}")
        
        # 5. 결과 생성
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        prediction_points = []
        
        for i, value in enumerate(predictions, 1):
            prediction_points.append(
                PredictionPoint(
                    time=now + timedelta(hours=i),
                    value=float(value)
                )
            )
        
        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=prediction_points
        )


# =============================================================================
# 테스트 코드
# =============================================================================

if __name__ == "__main__":
    """테스트 실행"""
    print("=" * 60)
    print("LSTM Predictor 테스트")
    print("=" * 60)
    
    try:
        # 1. 예측기 초기화
        predictor = LSTMPredictor()
        
        # 2. 예측 실행
        print("\n예측 실행 중...")
        result = predictor.run(
            service_id="test",
            metric_name="total_events",
            ctx=None,
            model_version="v1"
        )
        
        # 3. 결과 출력
        print("\n✅ 예측 완료!")
        print(f"  - 예측 개수: {len(result.predictions)}개")
        print(f"  - 첫 시간: {result.predictions[0].time}")
        print(f"  - 첫 값: {result.predictions[0].value:.2f}")
        print(f"  - 마지막 값: {result.predictions[-1].value:.2f}")
        
        print("\n처음 5개 예측값:")
        for i, pred in enumerate(result.predictions[:5], 1):
            print(f"  {i}시간 후: {pred.value:.2f}")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        raise
