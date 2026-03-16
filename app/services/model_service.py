from pathlib import Path

from app.config import get_settings
from app.services.model_backends.base import EmbeddingBackend, ModelRuntimeStatus
from app.services.model_backends.cloud_stub import CloudEmbeddingBackendStub
from app.services.model_backends.qwen_local import QwenLocalEmbeddingBackend


class ModelService:
    def __init__(self, backend: EmbeddingBackend):
        self.backend = backend

    def embed_image(self, image_path: Path) -> list[float]:
        return self.backend.embed_image(image_path)

    def status(self) -> ModelRuntimeStatus:
        return self.backend.model_status()


def create_model_service() -> ModelService:
    settings = get_settings()
    if settings.model_source == "local_huggingface_qwen":
        return ModelService(QwenLocalEmbeddingBackend(settings))
    if settings.model_source == "cloud_stub":
        return ModelService(CloudEmbeddingBackendStub(settings.model_repo_id))
    raise ValueError(f"Unsupported MODEL_SOURCE: {settings.model_source}")
