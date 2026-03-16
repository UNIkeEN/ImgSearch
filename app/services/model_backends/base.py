from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelRuntimeStatus:
    backend: str
    repo_id: str
    loaded: bool
    healthy: bool
    busy: bool
    message: str


class EmbeddingBackend(ABC):
    @abstractmethod
    def model_status(self) -> ModelRuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def embed_image(self, image_path: Path) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError
