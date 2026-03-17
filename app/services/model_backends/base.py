from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EmbeddingResult:
    vector: list[float]
    inference_seconds: float


@dataclass
class ModelRuntimeStatus:
    backend: str
    repo_id: str
    device: str
    loaded: bool
    healthy: bool
    busy: bool
    message: str


class EmbeddingBackend(ABC):
    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def model_status(self) -> ModelRuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def embed_image(self, image_path: Path) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingResult:
        raise NotImplementedError
