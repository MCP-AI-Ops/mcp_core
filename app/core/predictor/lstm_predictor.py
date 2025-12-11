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
    """LSTM 모델을 사용해 24시간 예측을 수행"""

    def __init__(
        self,
        model_path: str | None = None,
        metadata_path: str | None = None,
        csv_path: str | None = None,
    ):
        # 경로 우선순위: 명시 인자 > 환경변수 > 기본값
        self.model_path = model_path or os.getenv("LSTM_MODEL_PATH", "models/best_mcp_lstm_model.h5")
        self.metadata_path = metadata_path or os.getenv("LSTM_METADATA_PATH", "models/mcp_model_metadata.pkl")
        self.csv_path = csv_path or os.getenv("LSTM_CSV_PATH", "data/lstm_ready_cluster_data.csv")

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
            raise PredictionError(
                f"LSTM 모델 파일을 찾을 수 없습니다: {self.model_path}\n"
                "다음 방법 중 하나를 시도하세요:\n"
                "  1. 모델 다운로드: python scripts/download_models.py\n"
                "  2. 환경변수 설정: LSTM_MODEL_PATH=<경로>\n"
                f"  3. GitHub Release에서 수동 다운로드: https://github.com/MCP-AI-Ops/mcp_core/releases/tag/v1.0.0-models"
            )

        try:
            self.model = tf.keras.models.load_model(self.model_path)  # type: ignore
            print(f"[정보] 모델 로딩 완료: {self.model_path}")
        except Exception as exc:
            raise PredictionError(f"모델 로딩 실패: {exc}")

    def _load_metadata(self) -> None:
        if not os.path.exists(self.metadata_path):
            raise PredictionError(
                f"LSTM 메타데이터 파일을 찾을 수 없습니다: {self.metadata_path}\n"
                "다음 방법 중 하나를 시도하세요:\n"
                "  1. 모델 다운로드: python scripts/download_models.py\n"
                "  2. 환경변수 설정: LSTM_METADATA_PATH=<경로>\n"
                f"  3. GitHub Release에서 수동 다운로드: https://github.com/MCP-AI-Ops/mcp_core/releases/tag/v1.0.0-models"
            )

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
        github_url: str,
        metric_name: str,
        ctx: MCPContext,
        model_version: str,
    ) -> PredictionResult:
        if self.df is None:
            raise PredictionError("CSV 데이터가 로드되지 않음")
        
        if self.sequence_length is None:
            raise PredictionError("sequence_length가 로드되지 않음")

        recent_df = self.df.tail(self.sequence_length)
        if len(recent_df) < self.sequence_length:
            raise PredictionError(
                f"데이터 부족: {len(recent_df)} < {self.sequence_length}"
            )

        try:
            recent_data = recent_df[self.feature_names].values
        except KeyError as exc:
            raise PredictionError(f"특징 컬럼 누락: {exc}")
        
        if self.feature_scaler is None:
            raise PredictionError("feature_scaler가 로드되지 않음")

        try:
            features_scaled = self.feature_scaler.transform(recent_data)
            X = features_scaled.reshape(1, self.sequence_length, -1)
        except Exception as exc:
            raise PredictionError(f"특징 스케일링 실패: {exc}")

        raw_predictions = self._generate_predictions(X)
        
        # 컨텍스트 기반 스케일링: 입력 컨텍스트를 반영하여 예측값 조정
        scale_factor = self._compute_context_scale(ctx, metric_name)
        predictions = [pred * scale_factor for pred in raw_predictions]
        
        print(f"[디버그] 컨텍스트 스케일 팩터: {scale_factor:.2f} (users={ctx.expected_users}, slot={ctx.time_slot})")

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        prediction_points = [
            PredictionPoint(
                time=now + timedelta(hours=i + 1),
                value=float(value),
            )
            for i, value in enumerate(predictions)
        ]

        return PredictionResult(
            github_url=github_url,
            metric_name=metric_name,
            model_version=model_version,
            generated_at=datetime.utcnow(),
            predictions=prediction_points,
        )

    # 내부 헬퍼
    def _compute_context_scale(self, ctx: MCPContext, metric_name: str) -> float:
        """
        입력 컨텍스트를 기반으로 예측값 스케일 팩터를 계산한다.
        모델이 평균적인 상황을 기준으로 학습되었다고 가정하고,
        실제 사용자 수와 시간대를 반영한다.
        """
        expected_users = ctx.expected_users or 1000
        
        # 기본 스케일 (1000명 기준)
        baseline_users = 1000.0
        user_scale = expected_users / baseline_users
        
        # 시간대별 배수
        time_multiplier = {
            "peak": 1.5,
            "normal": 1.0,
            "low": 0.6,
        }.get(ctx.time_slot, 1.0)
        
        # 서비스 타입별 배수
        service_multiplier = {
            "web": 1.0,
            "api": 1.2,  # API는 더 높은 트래픽
            "db": 0.8,   # DB는 상대적으로 낮음
        }.get(ctx.service_type, 1.0)
        
        # 메트릭별 조정
        if metric_name in ("avg_cpu", "avg_memory"):
            # CPU/메모리는 사용자 수에 로그 스케일로 증가
            user_scale = 1.0 + np.log1p(expected_users / baseline_users) * 0.5
        
        final_scale = user_scale * time_multiplier * service_multiplier
        
        # 안전장치: 너무 극단적인 값 방지
        final_scale = np.clip(final_scale, 0.1, 10.0)
        
        return float(final_scale)

    def _generate_predictions(self, X: np.ndarray) -> list[float]:
        if self.model is None:
            raise PredictionError("모델이 로드되지 않음")
        if self.target_scaler is None:
            raise PredictionError("target_scaler가 로드되지 않음")
        
        try:
            results = []
            current_sequence = X.copy()

            for _ in range(24):
                pred_scaled = self.model.predict(current_sequence, verbose=0)[0, 0]  # type: ignore
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


# 테스트 실행용 진입점
if __name__ == "__main__":
    print("=" * 60)
    print("LSTM Predictor 테스트 실행")
    print("=" * 60)

    try:
        predictor = LSTMPredictor()
        print("\n테스트 예측 수행 중...")
        
        test_ctx = MCPContext(
            context_id="test-ctx",
            timestamp=datetime.utcnow(),
            service_type="web",
            runtime_env="prod",
            time_slot="normal",
            weight=1.0,
            expected_users=1000,
        )
        
        result = predictor.run(
            github_url="test",
            metric_name="total_events",
            ctx=test_ctx,
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

