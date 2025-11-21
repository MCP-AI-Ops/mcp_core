import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import DataSource
from app.core.errors import DataNotFoundError, DataSourceError


class CSVDataSource(DataSource):
    """CSV 파일에서 시계열 데이터를 읽어오는 데이터 소스."""

    def __init__(self, csv_path: str = "data/lstm_ready_cluster_data.csv"):
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            print(f"[경고] CSV 파일을 찾을 수 없음: {csv_path}")
            self.df = None
            return

        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"[정보] CSV 로드 완료: {len(self.df)}행")
        except Exception as exc:
            print(f"[경고] CSV 읽기 실패: {exc}")
            self.df = None

    def fetch_historical_data(
        self,
        github_url: str,
        metric_name: str,
        hours: int = 168,
        end_time: Optional[datetime] = None,
    ) -> np.ndarray:
        """최근 N시간 데이터를 반환한다."""
        if self.df is None:
            raise DataSourceError("CSV 데이터가 로드되지 않음")

        df = self.df

        # 서비스별 데이터 분리 지원: github_url 컬럼 존재 시 필터링
        if "github_url" in df.columns:
            filtered = df[df["github_url"] == github_url]
            if not filtered.empty:
                df = filtered

        if metric_name not in df.columns:
            raise DataNotFoundError(f"{metric_name} 컬럼이 CSV에 존재하지 않음")

        end_idx = len(df) - 1
        start_idx = max(0, end_idx - hours + 1)
        data = np.asarray(df.iloc[start_idx : end_idx + 1][metric_name].values)

        if len(data) < hours:
            pad_len = hours - len(data)
            pad_val = float(data[0]) if len(data) > 0 else 0.0
            padding = np.full(pad_len, pad_val, dtype=float)
            data = np.concatenate([padding, data])

        return data

    def is_available(self) -> bool:
        return self.csv_path.exists()
