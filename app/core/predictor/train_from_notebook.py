"""
개선 포인트
  * 학습 구간으로만 스케일러를 학습시켜 데이터 누수를 차단.
  * 결측치는 과거 값으로 채우고, 남은 값은 0으로 보정.
  * 모든 산출물을 models/ 디렉터리에 저장.
  * CLI 인자를 통해 경로와 하이퍼파라미터를 조정.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
from pathlib import Path
from typing import Dict, Any, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import RobustScaler
from tensorflow.keras import callbacks, layers, regularizers  # type: ignore

plt.switch_backend("Agg")


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
    """데이터 전처리와 LSTM 학습, 평가를 담당하는 클래스."""

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

        self.model: tf.keras.Model | None = None  # type: ignore
        self.feature_names: list[str] | None = None

        self.df: pd.DataFrame | None = None
        self.X_train = self.X_val = self.X_test = None
        self.y_train = self.y_val = self.y_test = None

    # ------------------------------------------------------------------
    # 데이터 로드 및 전처리
    # ------------------------------------------------------------------
    def load_and_prepare_data(self, csv_path: Path) -> pd.DataFrame:
        """CSV를 로드하고 타깃, 특징, 결측치를 정리한다."""
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

        original_target = self.df[self.target_col].astype(float)
        neg_count = (original_target < 0).sum()
        if neg_count > 0:
            print(f"[경고] 음수 타깃 {neg_count}개 발견, 0으로 클리핑")
            original_target = original_target.clip(lower=0)
        
        target = original_target.copy()
        
        # log 변환 먼저 (노트북 방식)
        if self.use_log_transform:
            original_mean = target.mean()
            target = np.log1p(target)
            self.df[f"{self.target_col}_log"] = target
            self.target_col = f"{self.target_col}_log"  # 타겟 컬럼명 변경
            print(f"[정보] 로그 변환 적용: {original_mean:.1f} -> {target.mean():.3f}")
        
        # 타겟 이상치 처리 - 95/5 percentile로 극값 클리핑 (log 변환 후)
        if self.handle_outliers:
            upper_bound = target.quantile(0.95)
            lower_bound = target.quantile(0.05)
            outliers_high = (target > upper_bound).sum()
            outliers_low = (target < lower_bound).sum()
            if outliers_high > 0 or outliers_low > 0:
                target = target.clip(lower=lower_bound, upper=upper_bound)
                self.df[self.target_col] = target
                print(f"[정보] 극값 제한: 상위 {outliers_high}개, 하위 {outliers_low}개 조정")
        
        # 원본도 유지하지 않았다면 저장
        if not self.use_log_transform:
            self.df[self.target_col] = target

    def _select_features(self) -> None:
        assert self.df is not None
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        # 원본 타겟과 로그 변환된 타겟 모두 제외 (노트북 방식)
        exclude = {self.target_col, "hour_offset", "total_events", "total_events_log"}
        self.feature_names = [
            col for col in numeric_cols if col not in exclude and "Unnamed" not in col
        ]
        if not self.feature_names:
            raise RuntimeError("학습에 사용할 숫자형 특징이 없음")
        print(f"[정보] 선택된 특징 수: {len(self.feature_names)}")

    def _handle_outliers(self) -> None:
        assert self.df is not None and self.feature_names is not None
        total_clipped = 0
        for col in self.feature_names:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr  # 표준 IQR 방식
            upper = q3 + 1.5 * iqr
            before = ((self.df[col] < lower) | (self.df[col] > upper)).sum()
            self.df[col] = self.df[col].clip(lower=lower, upper=upper)
            total_clipped += before
        if total_clipped > 0:
            print(f"[정보] 특성 이상치 조정: {total_clipped}개 값")

    def _handle_missing_values(self) -> None:
        assert self.df is not None and self.feature_names is not None
        cols = self.feature_names + [self.target_col]
        if self.df[cols].isna().sum().sum() > 0:
            print("[경고] 결측치 처리 중")
            for col in cols:
                if self.df[col].isna().sum() > 0:
                    if 'LAG' in col:
                        # LAG 특징: forward fill (과거 값 사용)
                        self.df[col] = self.df[col].ffill()
                    elif 'MA' in col:
                        # MA 특징: backward fill 후 forward fill
                        self.df[col] = self.df[col].bfill().ffill()
                    else:
                        # 기타: 선형 보간
                        self.df[col] = self.df[col].interpolate(method='linear', limit_direction='both')
                    # 여전히 남은 결측치는 0으로
                    self.df[col] = self.df[col].fillna(0.0)

    # ------------------------------------------------------------------
    # 시퀀스 생성 및 스케일링 (노트북 방식: 분할 후 스케일링)
    # ------------------------------------------------------------------
    def create_sequences(self) -> None:
        """시간 기반 분할 후 train 기준으로 스케일링하여 시퀀스 생성"""
        assert self.df is not None and self.feature_names is not None

        print("[정보] 시간 기반 데이터 분할 시작")
        
        # 시간 기반 분할 (노트북 방식)
        n = len(self.df)
        train_end = int(n * (1 - self.test_size - self.val_size))
        val_end = int(n * (1 - self.test_size))

        df_train = self.df.iloc[:train_end].copy()
        df_val = self.df.iloc[train_end:val_end].copy()
        df_test = self.df.iloc[val_end:].copy()

        print(f"[정보] 데이터 분할: Train({len(df_train)}), Val({len(df_val)}), Test({len(df_test)})")

        # 훈련 데이터로 스케일러 학습
        train_features = df_train[self.feature_names].values.astype(np.float32)
        train_target = df_train[self.target_col].values.astype(np.float32).reshape(-1, 1)

        self.feature_scaler.fit(train_features)
        self.target_scaler.fit(train_target)

        # 각 분할에 대해 시퀀스 생성
        self.X_train, self.y_train = self._build_sequences(df_train)
        self.X_val, self.y_val = self._build_sequences(df_val)
        self.X_test, self.y_test = self._build_sequences(df_test)

        print(
            "[정보] 시퀀스 생성 완료: "
            f"Train X{self.X_train.shape}, Val X{self.X_val.shape}, Test X{self.X_test.shape}"
        )

        # 시퀀스가 충분한지 확인
        if self.X_train.shape[0] < 100:
            print(f"[경고] 훈련 시퀀스가 {self.X_train.shape[0]}개로 부족합니다. 최소 100개 권장")

    def _build_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """단일 데이터프레임에서 시퀀스 생성"""
        features = df[self.feature_names].values.astype(np.float32)
        target = df[self.target_col].values.astype(np.float32).reshape(-1, 1)

        # 스케일링 적용
        features_scaled = self.feature_scaler.transform(features)
        target_scaled = self.target_scaler.transform(target).flatten()

        # 윈도우 생성
        X, y = [], []
        for idx in range(len(features_scaled) - self.seq_len):
            X.append(features_scaled[idx : idx + self.seq_len])
            y.append(target_scaled[idx + self.seq_len])
        
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

        self.model = tf.keras.Sequential(  # type: ignore
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

        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)  # type: ignore
        self.model.compile(optimizer=optimizer, loss="huber", metrics=["mae", "mse"])  # type: ignore
        print("[정보] 모델 컴파일 완료")

    def train(
        self,
        *,
        epochs: int = 100,
        batch_size: int = 32,
        patience: int = 20,
        verbose: int = 1,
    ) -> tf.keras.callbacks.History:  # type: ignore
        assert self.model is not None

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 동적 배치 크기 계산 (데이터 크기에 비례)
        train_size = len(self.X_train)
        dynamic_batch = min(32, max(8, train_size // 10))
        if batch_size == 32 and train_size > 100:  # 기본값일 때만 동적 조정
            batch_size = dynamic_batch
            print(f"[정보] 배치 크기 동적 조정: {batch_size}")

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

    def save_history(self, history: tf.keras.callbacks.History) -> None:  # type: ignore
        """학습 이력을 JSON과 PNG 그래프로 저장한다."""
        history_dict = history.history or {}
        epochs = list(range(1, len(history_dict.get("loss", [])) + 1))

        history_payload = {
            "epoch": epochs,
            "train_loss": history_dict.get("loss", []),
            "val_loss": history_dict.get("val_loss", []),
            "train_mae": history_dict.get("mae", []),
            "val_mae": history_dict.get("val_mae", []),
            "train_mse": history_dict.get("mse", []),
            "val_mse": history_dict.get("val_mse", []),
        }

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODELS_DIR / "training_history.json", "w", encoding="utf-8") as fh:
            json.dump(history_payload, fh, ensure_ascii=False, indent=2)
        print("[정보] 학습 이력을 training_history.json에 저장")

        if history_payload["train_loss"]:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(history_payload["epoch"], history_payload["train_loss"], label="train_loss")
            if history_payload["val_loss"]:
                ax.plot(history_payload["epoch"], history_payload["val_loss"], label="val_loss")
            ax.set_xlabel("epoch")
            ax.set_ylabel("loss")
            ax.set_title("Training Loss Curve")
            ax.legend()
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            fig.tight_layout()
            fig.savefig(MODELS_DIR / "training_loss.png", dpi=150)
            plt.close(fig)
            print("[정보] 학습 곡선을 training_loss.png로 저장")

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
            if X is None or y_true is None or len(X) == 0:
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
    history = trainer.train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience,
    )
    trainer.save_history(history)
    results = trainer.evaluate()
    trainer.save_artifacts()

    print("[요약] 학습 완료")
    for split, metrics in results.items():
        print(
            f"  {split.upper():>5} → R²={metrics['r2']:.4f}, "
            f"MAE={metrics['mae']:.2f}, MAPE={metrics['mape']:.1f}%"
        )


if __name__ == "__main__":
    main()