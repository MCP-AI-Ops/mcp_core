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
        
        if not self.csv_path.exists():
            raise DataSourceError(f"CSV file not found: {csv_path}")
        
        # CSV 로드
        self.df = pd.read_csv(self.csv_path)
        print(f"Loaded CSV: {len(self.df)} rows")
    
    def fetch_historical_data(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 168,
        end_time: Optional[datetime] = None
    ) -> np.ndarray:
        """CSV에서 최근 N시간 데이터 조회"""
        
        if metric_name not in self.df.columns:
            raise DataNotFoundError(f"Metric '{metric_name}' not found in CSV")
        
        # 최신 데이터에서 hours만큼 가져오기
        end_idx = len(self.df) - 1
        start_idx = max(0, end_idx - hours + 1)
        
        data = self.df.iloc[start_idx:end_idx + 1][metric_name].values
        
        # 부족하면 패딩
        if len(data) < hours:
            padding = np.full(hours - len(data), data[0])
            data = np.concatenate([padding, data])
        
        return data
    
    def is_available(self) -> bool:
        return self.csv_path.exists()