from pathlib import Path

from app.services.model_backends.base import EmbeddingBackend, EmbeddingResult, ModelRuntimeStatus


class CloudEmbeddingBackendStub(EmbeddingBackend):
    """Placeholder backend for future cloud embedding integration."""

    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def load(self) -> None:
        return None

    def model_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            backend="cloud_stub",
            repo_id=self.repo_id,
            configured_device="n/a",
            actual_device="n/a",
            loaded=False,
            healthy=False,
            busy=False,
            message="Cloud backend stub is not implemented yet.",
        )

    def embed_image(self, image_path: Path) -> EmbeddingResult:
        raise NotImplementedError(f"Cloud embedding backend is not implemented for {image_path}.")

    def embed_text(self, text: str) -> EmbeddingResult:
        raise NotImplementedError(f"Cloud embedding backend is not implemented for text query: {text}")
