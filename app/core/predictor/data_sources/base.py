from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import numpy as np
from app.core.errors import DataSourceError, DataNotFoundError


class DataSource(ABC):
    """시계열 데이터 조회 인터페이스"""
    
    @abstractmethod
    def fetch_historical_data(
        self,
        service_id: str,
        metric_name: str,
        hours: int = 168,
        end_time: Optional[datetime] = None
    ) -> np.ndarray:
        """최근 N시간 데이터 조회 (168개 값 반환)"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부"""
        pass