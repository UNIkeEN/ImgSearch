from pathlib import Path

from app.services.model_backends.base import EmbeddingBackend, ModelRuntimeStatus


class CloudEmbeddingBackendStub(EmbeddingBackend):
    """Placeholder backend for future cloud embedding integration."""

    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def model_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            backend="cloud_stub",
            repo_id=self.repo_id,
            loaded=False,
            healthy=False,
            busy=False,
            message="Cloud backend stub is not implemented yet.",
        )

    def embed_image(self, image_path: Path) -> list[float]:
        raise NotImplementedError(f"Cloud embedding backend is not implemented for {image_path}.")
