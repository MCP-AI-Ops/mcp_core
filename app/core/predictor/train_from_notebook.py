"""
demoMCPproject.ipynb 내용을 기반으로 정리한 모델 학습 스크립트.

개선 포인트
  * 학습 구간으로만 스케일러를 학습시켜 데이터 누수를 차단.
  * 결측치는 과거 값으로 채우고, 남은 값은 0으로 보정.
  * 모든 산출물을 models/ 디렉터리에 저장.
  * CLI 인자를 통해 경로와 하이퍼파라미터를 조정.
"""

from __future__ import annotations

import argparse
import os
import pickle
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import RobustScaler
from tensorflow.keras import callbacks, layers, regularizers


DEFAULT_CSV_PATH = Path("data/lstm_ready_cluster_data.csv")
MODELS_DIR = Path("models")
CHECKPOINT_PATH = MODELS_DIR / "best_mcp_lstm_checkpoint.h5"
MODEL_PATH = MODELS_DIR / "best_mcp_lstm_model.h5"
METADATA_PATH = MODELS_DIR / "mcp_model_metadata.pkl"


def set_random_seeds(seed: int = 42) -> None:
    """난수 시드를 고정해 재현 가능성을 확보한다."""
    np.random.seed(seed)
    tf.random.set_seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


class CompleteMCPPredictor:
    """데이터 전처리와 LSTM 학습·평가를 담당하는 클래스."""

    def __init__(
        self,
        *,
        sequence_length: int = 24,
        target_col: str = "total_events",
        test_size: float = 0.2,
        val_size: float = 0.1,
        use_log_transform: bool = True,
        handle_outliers: bool = True,
    ) -> None:
        self.seq_len = sequence_length
        self.target_col = target_col
        self.test_size = test_size
        self.val_size = val_size
        self.use_log_transform = use_log_transform
        self.handle_outliers = handle_outliers

        self.feature_scaler = RobustScaler()
        self.target_scaler = RobustScaler()

        self.model: tf.keras.Model | None = None
        self.feature_names: list[str] | None = None

        self.df: pd.DataFrame | None = None
        self.X_train = self.X_val = self.X_test = None
        self.y_train = self.y_val = self.y_test = None

    # ------------------------------------------------------------------
    # 데이터 로드 및 전처리
    # ------------------------------------------------------------------
    def load_and_prepare_data(self, csv_path: Path) -> pd.DataFrame:
        """CSV를 로드하고 타깃·특징·결측치를 정리한다."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없음: {csv_path}")

        self.df = pd.read_csv(csv_path)
        if "hour_offset" in self.df.columns:
            self.df = self.df.sort_values("hour_offset").reset_index(drop=True)

        self._preprocess_target()
        self._select_features()

        if self.handle_outliers:
            self._handle_outliers()

        self._handle_missing_values()
        return self.df

    def _preprocess_target(self) -> None:
        assert self.df is not None
        if self.target_col not in self.df.columns:
            raise ValueError(f"{self.target_col} 컬럼이 데이터에 없음")

        target = self.df[self.target_col].astype(float)
        neg_count = (target < 0).sum()
        if neg_count > 0:
            print(f"[경고] 음수 타깃 {neg_count}개 발견, 0으로 클리핑")
            target = target.clip(lower=0)

        if self.use_log_transform:
            print("[정보] 타깃에 log1p 변환 적용")
            target = np.log1p(target)

        self.df[self.target_col] = target

    def _select_features(self) -> None:
        assert self.df is not None
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        exclude = {self.target_col, "hour_offset"}
        self.feature_names = [
            col for col in numeric_cols if col not in exclude and "Unnamed" not in col
        ]
        if not self.feature_names:
            raise RuntimeError("학습에 사용할 숫자형 특징이 없음")
        print(f"[정보] 선택된 특징 수: {len(self.feature_names)}")

    def _handle_outliers(self) -> None:
        assert self.df is not None and self.feature_names is not None
        for col in self.feature_names:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 3 * iqr
            upper = q3 + 3 * iqr
            self.df[col] = self.df[col].clip(lower=lower, upper=upper)

    def _handle_missing_values(self) -> None:
        assert self.df is not None and self.feature_names is not None
        cols = self.feature_names + [self.target_col]
        if self.df[cols].isna().sum().sum() > 0:
            print("[경고] 결측치를 과거 값으로 채운 뒤 0으로 보정")
            self.df[cols] = self.df[cols].fillna(method="ffill").fillna(0.0)

    # ------------------------------------------------------------------
    # 시퀀스 생성 및 스케일링
    # ------------------------------------------------------------------
    def create_sequences(self) -> None:
        """시퀀스를 생성하고 train/val/test로 나눈다."""
        assert self.df is not None and self.feature_names is not None

        total_rows = len(self.df)
        n_samples = total_rows - self.seq_len
        if n_samples <= 0:
            raise ValueError("시퀀스를 생성하기에 데이터가 부족함")

        test_start = int(n_samples * (1 - self.test_size))
        val_start = int(test_start * (1 - self.val_size))

        feature_end = min(val_start + self.seq_len, total_rows)
        features = self.df[self.feature_names].values.astype(np.float32)
        target = self.df[self.target_col].values.astype(np.float32).reshape(-1, 1)

        self.feature_scaler.fit(features[:feature_end])
        features_scaled = self.feature_scaler.transform(features)

        self.target_scaler.fit(target[:feature_end])
        target_scaled = self.target_scaler.transform(target).flatten()

        X_all, y_all = self._build_windows(features_scaled, target_scaled)

        self.X_train = X_all[:val_start]
        self.X_val = X_all[val_start:test_start]
        self.X_test = X_all[test_start:]

        self.y_train = y_all[:val_start]
        self.y_val = y_all[val_start:test_start]
        self.y_test = y_all[test_start:]

        print(
            "[정보] 시퀀스 분할 "
            f"train={len(self.X_train)}, val={len(self.X_val)}, test={len(self.X_test)}"
        )

    def _build_windows(
        self, features: np.ndarray, target: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for idx in range(len(features) - self.seq_len):
            X.append(features[idx : idx + self.seq_len])
            y.append(target[idx + self.seq_len])
        return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)

    # ------------------------------------------------------------------
    # 모델 구성 및 학습
    # ------------------------------------------------------------------
    def build_model(
        self,
        *,
        lstm_units: Tuple[int, int] = (64, 32),
        dense_units: Tuple[int, int] = (16, 8),
        dropout_rate: float = 0.3,
        l2_reg: float = 1e-4,
        learning_rate: float = 1e-3,
    ) -> None:
        assert self.feature_names is not None
        n_features = len(self.feature_names)

        self.model = tf.keras.Sequential(
            [
                layers.Input(shape=(self.seq_len, n_features)),
                layers.LSTM(
                    lstm_units[0],
                    return_sequences=True,
                    dropout=dropout_rate,
                    recurrent_dropout=dropout_rate / 2,
                    kernel_regularizer=regularizers.l2(l2_reg),
                ),
                layers.BatchNormalization(),
                layers.LSTM(
                    lstm_units[1],
                    return_sequences=False,
                    dropout=dropout_rate,
                    recurrent_dropout=dropout_rate / 2,
                    kernel_regularizer=regularizers.l2(l2_reg),
                ),
                layers.BatchNormalization(),
                layers.Dense(
                    dense_units[0],
                    activation="relu",
                    kernel_regularizer=regularizers.l2(l2_reg),
                ),
                layers.Dropout(dropout_rate),
                layers.BatchNormalization(),
                layers.Dense(
                    dense_units[1],
                    activation="relu",
                    kernel_regularizer=regularizers.l2(l2_reg),
                ),
                layers.Dropout(dropout_rate / 2),
                layers.Dense(1),
            ]
        )

        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        self.model.compile(optimizer=optimizer, loss="huber", metrics=["mae"])
        print("[정보] 모델 컴파일 완료")

    def train(
        self,
        *,
        epochs: int = 100,
        batch_size: int = 32,
        patience: int = 20,
        verbose: int = 1,
    ) -> tf.keras.callbacks.History:
        assert self.model is not None

        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        cbks = [
            callbacks.EarlyStopping(
                monitor="val_loss",
                patience=patience,
                restore_best_weights=True,
                verbose=verbose,
            ),
            callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                patience=max(1, patience // 2),
                factor=0.5,
                min_lr=1e-7,
                verbose=verbose,
            ),
            callbacks.ModelCheckpoint(
                filepath=str(CHECKPOINT_PATH),
                monitor="val_loss",
                save_best_only=True,
                verbose=0,
            ),
        ]

        history = self.model.fit(
            self.X_train,
            self.y_train,
            validation_data=(self.X_val, self.y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=cbks,
            verbose=verbose,
        )
        print("[정보] 학습 완료")
        return history

    # ------------------------------------------------------------------
    # 평가 및 산출물 저장
    # ------------------------------------------------------------------
    def evaluate(self) -> Dict[str, Dict[str, float]]:
        assert self.model is not None

        results: Dict[str, Dict[str, float]] = {}
        for label, X, y_true in (
            ("train", self.X_train, self.y_train),
            ("val", self.X_val, self.y_val),
            ("test", self.X_test, self.y_test),
        ):
            if len(X) == 0:
                continue
            preds_scaled = self.model.predict(X, verbose=0).flatten()

            y_pred = self.target_scaler.inverse_transform(
                preds_scaled.reshape(-1, 1)
            ).flatten()
            y_true_orig = self.target_scaler.inverse_transform(
                y_true.reshape(-1, 1)
            ).flatten()

            if self.use_log_transform:
                y_pred = np.expm1(y_pred)
                y_true_orig = np.expm1(y_true_orig)

            y_pred = np.maximum(y_pred, 0)

            mae = mean_absolute_error(y_true_orig, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true_orig, y_pred))
            r2 = r2_score(y_true_orig, y_pred)
            epsilon = 1e-10
            mape = np.mean(
                np.abs((y_true_orig - y_pred) / (y_true_orig + epsilon))
            ) * 100

            results[label] = {
                "mae": float(mae),
                "rmse": float(rmse),
                "r2": float(r2),
                "mape": float(mape),
            }
            print(
                f"[정보] {label.upper():>5} 지표 - "
                f"MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.4f}, MAPE={mape:.1f}%"
            )
        return results

    def save_artifacts(self) -> None:
        assert self.model is not None and self.feature_names is not None
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        self.model.save(MODEL_PATH, include_optimizer=False)
        print(f"[정보] 모델 저장 완료: {MODEL_PATH}")

        metadata = {
            "scaler": self.feature_scaler,
            "target_scaler": self.target_scaler,
            "sequence_length": self.seq_len,
            "target_col": self.target_col,
            "feature_names": self.feature_names,
            "n_features": len(self.feature_names),
            "use_log_transform": self.use_log_transform,
        }
        with open(METADATA_PATH, "wb") as fh:
            pickle.dump(metadata, fh)
        print(f"[정보] 메타데이터 저장 완료: {METADATA_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP LSTM 모델 학습 스크립트")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--sequence-length", type=int, default=24)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--val-size", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_random_seeds(args.seed)

    trainer = CompleteMCPPredictor(
        sequence_length=args.sequence_length,
        test_size=args.test_size,
        val_size=args.val_size,
    )
    trainer.load_and_prepare_data(args.csv_path)
    trainer.create_sequences()
    trainer.build_model(learning_rate=args.learning_rate)
    trainer.train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience,
    )
    results = trainer.evaluate()
    trainer.save_artifacts()

    print("=" * 80)
    print("[요약] 학습 완료")
    for split, metrics in results.items():
        print(
            f"  {split.upper():>5} → R²={metrics['r2']:.4f}, "
            f"MAE={metrics['mae']:.2f}, MAPE={metrics['mape']:.1f}%"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()

