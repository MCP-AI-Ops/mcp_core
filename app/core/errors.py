class ContextValidationError(ValueError):
    """Context validation failed."""
    pass


class ModelValidationError(RuntimeError):
    pass


class PredictionError(RuntimeError):
    """Generic prediction failure."""
    pass


class DataSourceError(RuntimeError):
    """Errors related to data sources (CSV/MySQL)."""
    pass


class DataNotFoundError(DataSourceError):
    """Requested data or metric not found."""
    pass


