"""
원본 demoMCPproject.ipynb 기반 학습 스크립트
- CompleteMCPPredictor 클래스 그대로 사용
- 로컬 환경 경로로 수정
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, regularizers, callbacks
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, RobustScaler
import matplotlib
matplotlib.use('Agg')  # GUI 없는 환경용
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🚀 MCP LSTM 모델 학습 (원본 노트북 기반)")
print("=" * 80)

# GPU 최적화 설정
print("\n📋 환경 정보:")
print(f"  TensorFlow 버전: {tf.__version__}")
print(f"  GPU 사용 가능: {tf.config.list_physical_devices('GPU')}")

# 재현 가능성을 위한 시드 설정
def set_random_seeds(seed=42):
    np.random.seed(seed)
    tf.random.set_seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

set_random_seeds(42)

# ===================================================================
# CompleteMCPPredictor 클래스 (원본 노트북과 동일)
# ===================================================================

class CompleteMCPPredictor:
    """
    Google Cluster 데이터의 극값과 long-tail 분포 특성을 고려한 설계
    """

    def __init__(self,
                 sequence_length=24,
                 target_col='total_events',
                 test_size=0.2,
                 val_size=0.1,
                 use_log_transform=True,
                 handle_outliers=True):

        self.seq_len = sequence_length
        self.target_col = target_col
        self.test_size = test_size
        self.val_size = val_size
        self.use_log_transform = use_log_transform
        self.handle_outliers = handle_outliers

        # 스케일러들 (RobustScaler - 극값에 강건)
        self.feature_scaler = RobustScaler()
        self.target_scaler = RobustScaler()

        # 모델과 데이터
        self.model = None
        self.history = None
        self.feature_names = None

        # 데이터 저장
        self.X_train = self.X_val = self.X_test = None
        self.y_train = self.y_val = self.y_test = None
        self.df = None

    def load_and_prepare_data(self, csv_path='data/lstm_ready_cluster_data.csv'):
        """데이터 로드 및 전처리"""
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        
        self.df = pd.read_csv(csv_path)
        print(f"\n📂 데이터 로드 완료: {self.df.shape}")

        # 기본 정리
        if 'hour_offset' in self.df.columns:
            self.df = self.df.sort_values('hour_offset').reset_index(drop=True)

        # 타겟 변수 전처리
        self._preprocess_target()

        # 특성 선택
        self._select_features()

        # 이상치 처리
        if self.handle_outliers:
            self._handle_outliers()

        # 결측값 처리
        self._handle_missing_values()

        print(f"✓ 전처리 완료: {self.df.shape}")
        print(f"✓ 타겟 통계 - 평균: {self.df[self.target_col].mean():.2f}, "
              f"분산: {self.df[self.target_col].var():.2f}")

        return self.df

    def _preprocess_target(self):
        """타겟 변수 전처리"""
        if self.target_col not in self.df.columns:
            raise ValueError(f"타겟 컬럼 '{self.target_col}'을 찾을 수 없습니다")

        target = self.df[self.target_col].copy()

        # 음수 값 처리
        if (target < 0).any():
            print(f"⚠️  음수 값 발견: {(target < 0).sum()}개")
            target = target.clip(lower=0)

        # 로그 변환 (극단값 처리)
        if self.use_log_transform:
            print(f"✓ 로그 변환 적용 (극단값 처리)")
            target = np.log1p(target)

        self.df[self.target_col] = target

    def _select_features(self):
        """피처 선택"""
        # 제외할 컬럼
        exclude_cols = [self.target_col, 'hour_offset']
        
        # 숫자형 컬럼만 선택
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        self.feature_names = [
            col for col in numeric_cols 
            if col not in exclude_cols and 'Unnamed' not in col
        ]
        
        print(f"✓ 선택된 피처: {len(self.feature_names)}개")

    def _handle_outliers(self):
        """이상치 처리 (IQR 방식)"""
        for col in self.feature_names:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            self.df[col] = self.df[col].clip(lower=lower_bound, upper=upper_bound)

    def _handle_missing_values(self):
        """결측값 처리"""
        if self.df[self.feature_names + [self.target_col]].isnull().sum().sum() > 0:
            print("⚠️  결측값 처리 중...")
            self.df[self.feature_names + [self.target_col]] = \
                self.df[self.feature_names + [self.target_col]].fillna(method='ffill').fillna(method='bfill')

    def create_sequences(self):
        """시퀀스 데이터 생성"""
        print(f"\n🔄 시퀀스 생성 중... (length={self.seq_len})")
        
        # 피처 스케일링
        features = self.df[self.feature_names].values
        features_scaled = self.feature_scaler.fit_transform(features)
        
        # 타겟 스케일링
        target = self.df[self.target_col].values
        target_scaled = self.target_scaler.fit_transform(target.reshape(-1, 1)).flatten()
        
        # 시퀀스 생성
        X, y = [], []
        for i in range(len(self.df) - self.seq_len):
            X.append(features_scaled[i:i+self.seq_len])
            y.append(target_scaled[i+self.seq_len])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"✓ X shape: {X.shape}")
        print(f"✓ y shape: {y.shape}")
        
        # Train/Val/Test 분할
        n_samples = len(X)
        test_idx = int(n_samples * (1 - self.test_size))
        val_idx = int(test_idx * (1 - self.val_size))
        
        self.X_train = X[:val_idx]
        self.X_val = X[val_idx:test_idx]
        self.X_test = X[test_idx:]
        
        self.y_train = y[:val_idx]
        self.y_val = y[val_idx:test_idx]
        self.y_test = y[test_idx:]
        
        print(f"✓ Train: {len(self.X_train)} samples")
        print(f"✓ Val:   {len(self.X_val)} samples")
        print(f"✓ Test:  {len(self.X_test)} samples")

    def build_model(self,
                    lstm_units=[64, 32],
                    dense_units=[16, 8],
                    dropout_rate=0.3,
                    l2_reg=1e-4,
                    learning_rate=0.001):
        """LSTM 모델 구축"""
        print(f"\n🏗️  모델 구축 중...")
        print(f"  LSTM: {lstm_units}")
        print(f"  Dense: {dense_units}")
        print(f"  Dropout: {dropout_rate}")
        
        n_features = len(self.feature_names)
        
        self.model = tf.keras.Sequential([
            layers.Input(shape=(self.seq_len, n_features)),
            
            # LSTM 레이어
            layers.LSTM(lstm_units[0], return_sequences=True, 
                       dropout=dropout_rate, recurrent_dropout=dropout_rate/2,
                       kernel_regularizer=regularizers.l2(l2_reg)),
            layers.BatchNormalization(),
            
            layers.LSTM(lstm_units[1], return_sequences=False,
                       dropout=dropout_rate, recurrent_dropout=dropout_rate/2,
                       kernel_regularizer=regularizers.l2(l2_reg)),
            layers.BatchNormalization(),
            
            # Dense 레이어
            layers.Dense(dense_units[0], activation='relu',
                        kernel_regularizer=regularizers.l2(l2_reg)),
            layers.Dropout(dropout_rate),
            layers.BatchNormalization(),
            
            layers.Dense(dense_units[1], activation='relu',
                        kernel_regularizer=regularizers.l2(l2_reg)),
            layers.Dropout(dropout_rate/2),
            
            # 출력
            layers.Dense(1)
        ])
        
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
            loss='huber',
            metrics=['mae']
        )
        
        print("✓ 모델 구축 완료")

    def train_model(self, epochs=100, batch_size=32, patience=20, verbose=1):
        """모델 훈련"""
        print(f"\n🚀 학습 시작 (epochs={epochs}, batch_size={batch_size})")
        
        callbacks_list = [
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=patience,
                restore_best_weights=True,
                verbose=verbose
            ),
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                patience=patience//2,
                factor=0.5,
                min_lr=1e-7,
                verbose=verbose
            ),
            callbacks.ModelCheckpoint(
                'best_mcp_lstm_model.h5',
                monitor='val_loss',
                save_best_only=True,
                verbose=0
            )
        ]
        
        self.history = self.model.fit(
            self.X_train, self.y_train,
            validation_data=(self.X_val, self.y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks_list,
            verbose=verbose
        )
        
        print("\n✓ 학습 완료!")
        return self.history

    def evaluate_model(self):
        """모델 평가"""
        print(f"\n📊 모델 평가 중...")
        
        results = {}
        
        for name, X, y_true in [
            ('train', self.X_train, self.y_train),
            ('val', self.X_val, self.y_val),
            ('test', self.X_test, self.y_test)
        ]:
            # 예측
            y_pred_scaled = self.model.predict(X, verbose=0).flatten()
            
            # 역변환
            y_pred = self.target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
            y_true_orig = self.target_scaler.inverse_transform(y_true.reshape(-1, 1)).flatten()
            
            # 로그 변환 되돌리기
            if self.use_log_transform:
                y_pred = np.expm1(y_pred)
                y_true_orig = np.expm1(y_true_orig)
            
            # 음수 클리핑
            y_pred = np.maximum(y_pred, 0)
            
            # 평가 지표
            mae = mean_absolute_error(y_true_orig, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true_orig, y_pred))
            r2 = r2_score(y_true_orig, y_pred)
            
            # MAPE
            epsilon = 1e-10
            mape = np.mean(np.abs((y_true_orig - y_pred) / (y_true_orig + epsilon))) * 100
            
            results[name] = {
                'mae': mae,
                'rmse': rmse,
                'r2': r2,
                'mape': mape,
                'y_true': y_true_orig,
                'y_pred': y_pred
            }
            
            print(f"\n  {name.upper():>5}: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.4f}, MAPE={mape:.1f}%")
        
        return results

    def save_model_and_scaler(self):
        """모델 및 메타데이터 저장"""
        print(f"\n💾 모델 저장 중...")
        
        # 모델 저장
        os.makedirs('models', exist_ok=True)
        model_path = 'models/best_mcp_lstm_model.h5'
        self.model.save(model_path)
        print(f"  ✓ 모델: {model_path}")
        
        # 메타데이터 저장
        metadata = {
            'scaler': self.feature_scaler,
            'target_scaler': self.target_scaler,
            'sequence_length': self.seq_len,
            'target_col': self.target_col,
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names),
            'use_log_transform': self.use_log_transform
        }
        
        metadata_path = 'models/mcp_model_metadata.pkl'
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        print(f"  ✓ 메타데이터: {metadata_path}")

# ===================================================================
# 메인 실행
# ===================================================================

def main():
    """메인 실행 함수"""
    try:
        # 1. Predictor 초기화
        print("\n⚙️  Predictor 초기화")
        predictor = CompleteMCPPredictor(
            sequence_length=24,
            target_col='total_events',
            test_size=0.2,
            val_size=0.1,
            use_log_transform=True,
            handle_outliers=True
        )

        # 2. 데이터 로드 및 전처리
        print("\n📂 데이터 로드 및 전처리")
        predictor.load_and_prepare_data(csv_path='data/lstm_ready_cluster_data.csv')

        # 3. 시퀀스 생성
        print("\n🔄 시퀀스 데이터 생성")
        predictor.create_sequences()

        # 4. 모델 구축
        print("\n🏗️  LSTM 모델 구축")
        predictor.build_model(
            lstm_units=[64, 32],
            dense_units=[16, 8],
            dropout_rate=0.3,
            l2_reg=1e-4,
            learning_rate=0.001
        )

        # 5. 모델 훈련
        print("\n🚀 모델 훈련 시작")
        history = predictor.train_model(
            epochs=100,
            batch_size=32,
            patience=20,
            verbose=1
        )

        # 6. 모델 평가
        print("\n📊 모델 평가")
        results = predictor.evaluate_model()

        # 7. 모델 저장
        print("\n💾 모델 저장")
        predictor.save_model_and_scaler()

        # 8. 최종 결과 요약
        print("\n" + "=" * 80)
        print("✅ 훈련 완료! 결과 요약:")
        print("=" * 80)

        for dataset, metrics in results.items():
            print(f"{dataset.upper():>12}: R²={metrics['r2']:.4f}, "
                  f"MAE={metrics['mae']:.2f}, MAPE={metrics['mape']:.1f}%")

        # R² 평가
        test_r2 = results.get('test', {}).get('r2', -999)
        if test_r2 > 0.7:
            print("\n🎉 우수한 성능! (R² > 0.7)")
        elif test_r2 > 0.5:
            print("\n✅ 양호한 성능 (R² > 0.5)")
        elif test_r2 > 0:
            print("\n⚠️  R² 양수 달성, 추가 튜닝 권장")
        else:
            print("\n❌ R² 음수. 모델 재검토 필요")

        print("\n📁 생성된 파일:")
        print("  - models/best_mcp_lstm_model.h5: 훈련된 모델")
        print("  - models/mcp_model_metadata.pkl: 메타데이터")

        return predictor, results

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

# 실행
if __name__ == "__main__":
    predictor, results = main()

    if predictor is not None:
        print("\n" + "=" * 80)
        print("🎉 성공적으로 완료되었습니다!")
        print("=" * 80)
        print("\n다음 단계: 이제 학습된 모델을 FastAPI에서 사용할 수 있습니다.")
    else:
        print("\n실행 중 문제가 발생했습니다. 로그를 확인하세요.")
