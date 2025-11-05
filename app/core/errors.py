class ContextValidationError(ValueError):
    """Context validation failed (spelling-corrected).

    We keep an alias `ContextVaidationError` for backward compatibility.
    """
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


# Backwards-compatible aliases (old names)
ContextVaidationError = ContextValidationError