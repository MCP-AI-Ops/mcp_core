import os

from .csv_source import CSVDataSource
from .mysql_source import MySQLDataSource
from app.core.errors import DataSourceError


_data_source_instance = None


def _create_data_source():
    backend = os.getenv("DATA_SOURCE_BACKEND", "csv").strip().lower()

    if backend == "mysql":
        return MySQLDataSource()
    if backend == "csv":
        csv_path = os.getenv("CSV_DATA_PATH", "data/lstm_ready_cluster_data.csv")
        return CSVDataSource(csv_path=csv_path)

    raise DataSourceError(f"Unknown data source backend: {backend}")


def get_data_source():
    """글로벌 데이터 소스 인스턴스 반환"""
    global _data_source_instance

    if _data_source_instance is None:
        try:
            _data_source_instance = _create_data_source()
        except Exception as exc:
            raise DataSourceError(f"failed to initialize data source: {exc}") from exc

    return _data_source_instance
