from abc import ABC, abstractmethod
from app.models.common import MCPContext, PredictionResult

class BasePredictor(ABC):
    @abstractmethod
    def run(self, *, service_id: str, metric_name: str, context: MCPContext, model_version: str) -> PredictionResult:
        ...