"""
LSTM Predictor 모듈
FastAPI 환경에서 LSTM 기반 24시간 예측을 수행한다.
"""

from __future__ import annotations

import os
import pickle
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import tensorflow as tf

from app.models.common import MCPContext, PredictionResult, PredictionPoint
from app.core.predictor.base import BasePredictor
from app.core.errors import PredictionError


class LSTMPredictor(BasePredictor):
    """LSTM 모델을 사용해 24시간 예측을 수행한다."""

    def __init__(
        self,
        model_path: str = "models/best_mcp_lstm_model.h5",
        metadata_path: str = "models/mcp_model_metadata.pkl",
        csv_path: str = "data/lstm_ready_cluster_data.csv",
    ):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.csv_path = csv_path

        self.model = None
        self.metadata = None
        self.feature_scaler = None
        self.target_scaler = None
        self.feature_names = None
        self.sequence_length = None
        self.use_log_transform = None

        self.df = None

        self._load_model()
        self._load_metadata()
        self._load_csv_data()

        print("[정보] LSTM Predictor 초기화 완료")

    # ------------------------------------------------------------------
    # 로딩 유틸리티
    # ------------------------------------------------------------------
    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            raise PredictionError(f"모델 파일이 존재하지 않음: {self.model_path}")

        try:
            self.model = tf.keras.models.load_model(self.model_path)
            print(f"[정보] 모델 로딩 완료: {self.model_path}")
        except Exception as exc:
            raise PredictionError(f"모델 로딩 실패: {exc}")

    def _load_metadata(self) -> None:
        if not os.path.exists(self.metadata_path):
            raise PredictionError(f"메타데이터 파일이 존재하지 않음: {self.metadata_path}")

        try:
            with open(self.metadata_path, "rb") as fh:
                self.metadata = pickle.load(fh)

            self.feature_scaler = self.metadata["scaler"]
            self.target_scaler = self.metadata["target_scaler"]
            self.feature_names = self.metadata["feature_names"]
            self.sequence_length = self.metadata["sequence_length"]
            self.use_log_transform = self.metadata.get("use_log_transform", False)

            print("[정보] 메타데이터 로딩 완료")
        except Exception as exc:
            raise PredictionError(f"메타데이터 로딩 실패: {exc}")

    def _load_csv_data(self) -> None:
        if not os.path.exists(self.csv_path):
            print(f"[경고] CSV 파일을 찾을 수 없음: {self.csv_path}")
            self.df = None
            return

        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"[정보] CSV 로드 완료: {len(self.df)}행")
        except Exception as exc:
            print(f"[경고] CSV 로드 실패: {exc}")
            self.df = None

    # ------------------------------------------------------------------
    # Predictor 인터페이스 구현
    # ------------------------------------------------------------------
    def run(
        self,
        *,
        service_id: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
    ) -> PredictionResult:
        if self.df is None:
            raise PredictionError("CSV 데이터가 로드되지 않음")

        recent_df = self.df.tail(self.sequence_length)
        if len(recent_df) < self.sequence_length:
            raise PredictionError(
                f"데이터 부족: {len(recent_df)} < {self.sequence_length}"
            )

        try:
            recent_data = recent_df[self.feature_names].values
        except KeyError as exc:
            raise PredictionError(f"특징 컬럼 누락: {exc}")

        try:
            features_scaled = self.feature_scaler.transform(recent_data)
            X = features_scaled.reshape(1, self.sequence_length, -1)
        except Exception as exc:
            raise PredictionError(f"특징 스케일링 실패: {exc}")

        predictions = self._generate_predictions(X)

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        prediction_points = [
            PredictionPoint(
                time=now + timedelta(hours=i + 1),
                value=float(value),
            )
            for i, value in enumerate(predictions)
        ]

        return PredictionResult(
            service_id=service_id,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=prediction_points,
        )

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _generate_predictions(self, X: np.ndarray) -> list[float]:
        try:
            results = []
            current_sequence = X.copy()

            for _ in range(24):
                pred_scaled = self.model.predict(current_sequence, verbose=0)[0, 0]
                pred = self.target_scaler.inverse_transform([[pred_scaled]])[0, 0]

                if self.use_log_transform:
                    pred = np.expm1(pred)

                pred = max(pred, 0)
                results.append(pred)

                new_features = current_sequence[0, -1, :].copy()
                new_row = np.concatenate([[pred_scaled], new_features[1:]])
                current_sequence = np.append(
                    current_sequence[:, 1:, :],
                    new_row.reshape(1, 1, -1),
                    axis=1,
                )

            return results
        except Exception as exc:
            raise PredictionError(f"예측 생성 실패: {exc}")


# ----------------------------------------------------------------------
# 테스트 실행용 진입점
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("LSTM Predictor 테스트 실행")
    print("=" * 60)

    try:
        predictor = LSTMPredictor()
        print("\n테스트 예측 수행 중...")
        result = predictor.run(
            service_id="test",
            metric_name="total_events",
            ctx=None,
            model_version="v1",
        )

        print("\n[정보] 테스트 예측 완료")
        print(f"  - 예측 데이터 수: {len(result.predictions)}")
        print(f"  - 첫 예측 시각: {result.predictions[0].time}")
        print(f"  - 첫 예측 값: {result.predictions[0].value:.2f}")
        print(f"  - 마지막 예측 값: {result.predictions[-1].value:.2f}")

        print("\n상위 5개 예측 결과:")
        for i, pred in enumerate(result.predictions[:5], 1):
            print(f"  {i}시간 뒤 예측: {pred.value:.2f}")

    except Exception as exc:
        print(f"\n[오류] 테스트 실행 중 예외: {exc}")
        raise

