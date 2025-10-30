import os
from .csv_source import CSVDataSource


_data_source_instance = None


def get_data_source():
    """글로벌 데이터 소스 인스턴스 반환"""
    global _data_source_instance
    
    if _data_source_instance is None:
        csv_path = os.getenv("CSV_DATA_PATH", "data/lstm_ready_cluster_data.csv")
        _data_source_instance = CSVDataSource(csv_path=csv_path)
    
    return _data_source_instance