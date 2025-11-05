import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

from .base import DataSource
from app.core.errors import DataNotFoundError, DataSourceError


class CSVDataSource(DataSource):
    """CSV 파일에서 시계열 데이터 조회"""
    
    def __init__(self, csv_path: str = "data/lstm_ready_cluster_data.csv"):
        self.csv_path = Path(csv_path)
        
        # 존재하지 않을 수 있으므로 예외 대신 None으로 처리 (앱 시작 시 치명적 실패 방지)
        if not self.csv_path.exists():
            print(f"⚠️ CSV file not found: {csv_path}")
            self.df = None
            return
        
        # CSV 로드
        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"Loaded CSV: {len(self.df)} rows")
        except Exception as e:
            print(f"⚠️ Failed to read CSV ({self.csv_path}): {e}")
            self.df = None
    
    def fetch_historical_data(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 168,
        end_time: Optional[datetime] = None
    ) -> np.ndarray:
        """CSV에서 최근 N시간 데이터 조회"""
        
        if self.df is None:
            raise DataSourceError("CSV not loaded")

        if metric_name not in self.df.columns:
            raise DataNotFoundError(f"Metric '{metric_name}' not found in CSV")

        # 최신 데이터에서 hours만큼 가져오기
        end_idx = len(self.df) - 1
        start_idx = max(0, end_idx - hours + 1)

        data = self.df.iloc[start_idx:end_idx + 1][metric_name].values

        # 부족하면 패딩 (데이터가 아예 없을 경우 안전하게 0으로 패딩)
        if len(data) < hours:
            pad_len = hours - len(data)
            pad_val = float(data[0]) if len(data) > 0 else 0.0
            padding = np.full(pad_len, pad_val)
            data = np.concatenate([padding, data])

        return data
    
    def is_available(self) -> bool:
        return self.csv_path.exists()