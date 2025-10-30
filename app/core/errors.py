class ContextVaidationError(ValueError):
    pass

class ModelValidationError(RuntimeError):
    pass

class PredictionError(RuntimeError):
    pass

class DataSourceError(RuntimeError):
    pass

class DataNotFoundError(DataSourceError):
    pass

class PredictionError(RuntimeError):
    pass