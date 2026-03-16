import importlib.util
import inspect
import threading
from pathlib import Path

from huggingface_hub import snapshot_download

try:
    from huggingface_hub.errors import LocalEntryNotFoundError
except ImportError:  # pragma: no cover - compatibility for older huggingface_hub
    class LocalEntryNotFoundError(Exception):
        pass

from app.config import Settings
from app.logging_utils import get_logger
from app.services.model_backends.base import EmbeddingBackend, ModelRuntimeStatus


class QwenLocalEmbeddingBackend(EmbeddingBackend):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._instance = None
        self._lock = threading.Lock()
        self._busy = False
        self._last_error: str | None = None
        self._logger = get_logger(__name__)

    def _load_module(self, module_path: Path):
        spec = importlib.util.spec_from_file_location("qwen3_vl_embedding_remote", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _resolve_repo_path(self) -> Path:
        if self.settings.model_local_path is not None:
            repo_path = self.settings.model_local_path
            if not repo_path.exists():
                raise RuntimeError(f"MODEL_LOCAL_PATH does not exist: {repo_path}")
            self._logger.info("Loading Qwen model from MODEL_LOCAL_PATH=%s", repo_path)
            return repo_path

        try:
            repo_path = snapshot_download(
                repo_id=self.settings.model_repo_id,
                cache_dir=str(self.settings.model_cache_dir),
                local_files_only=True,
            )
        except LocalEntryNotFoundError as exc:
            raise RuntimeError(
                "Model was not found in local Hugging Face cache. "
                "Set MODEL_LOCAL_PATH to your downloaded model directory, "
                "or download the model into the local cache first."
            ) from exc
        self._logger.info("Loading Qwen model from local cache: repo_id=%s path=%s", self.settings.model_repo_id, repo_path)
        return Path(repo_path)

    def _ensure_loaded(self):
        if self._instance is not None:
            return self._instance

        with self._lock:
            if self._instance is not None:
                return self._instance

            repo_path = self._resolve_repo_path()
            module = self._load_module(repo_path / "scripts" / "qwen3_vl_embedding.py")
            embedder_cls = getattr(module, "Qwen3VLEmbedder", None)
            if embedder_cls is None:
                raise RuntimeError("Qwen3VLEmbedder was not found in downloaded model repository.")

            self._instance = self._build_embedder(embedder_cls, str(repo_path))
            self._last_error = None
            self._logger.info("Qwen embedder loaded successfully: repo=%s device=%s", repo_path, self.settings.device)
            return self._instance

    def _build_embedder(self, embedder_cls, repo_path: str):
        kwargs = {"model_name_or_path": repo_path}
        try:
            signature = inspect.signature(embedder_cls)
            parameters = signature.parameters
            if "device" in parameters:
                kwargs["device"] = self.settings.device
            if "torch_dtype" in parameters:
                kwargs["torch_dtype"] = self.settings.torch_dtype
        except (TypeError, ValueError):
            pass

        try:
            instance = embedder_cls(**kwargs)
        except TypeError:
            instance = embedder_cls(model_name_or_path=repo_path)

        self._move_instance_to_device(instance)
        return instance

    def _move_instance_to_device(self, instance) -> None:
        targets = [instance]
        model_attr = getattr(instance, "model", None)
        if model_attr is not None:
            targets.append(model_attr)

        for target in targets:
            to_method = getattr(target, "to", None)
            if callable(to_method):
                try:
                    to_method(self.settings.device)
                except TypeError:
                    continue

    def load(self) -> None:
        self._busy = True
        try:
            self._logger.info("Preloading Qwen embedder")
            self._ensure_loaded()
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self._logger.exception("Failed to preload Qwen embedder")
            raise
        finally:
            self._busy = False

    def _normalize_vector(self, vector) -> list[float]:
        if hasattr(vector, "tolist"):
            return [float(value) for value in vector.tolist()]
        return [float(value) for value in vector]

    def _invoke_text_embedding(self, instance, text: str):
        candidate_calls = [
            lambda: instance.process([{"text": text}]),
            lambda: instance.embed_text(text),
            lambda: instance.get_text_embeddings([text], batch_size=self.settings.model_batch_size),
        ]
        last_error = None
        for candidate in candidate_calls:
            try:
                result = candidate()
                if result:
                    return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        if last_error is not None:
            raise RuntimeError(f"Text embedding failed: {last_error}") from last_error
        raise RuntimeError("Text embedding backend returned no vectors.")

    def model_status(self) -> ModelRuntimeStatus:
        loaded = self._instance is not None
        healthy = self._last_error is None
        message = self._last_error or ("Model is ready." if loaded else "Model is not loaded yet.")
        return ModelRuntimeStatus(
            backend=self.settings.model_source,
            repo_id=self.settings.model_repo_id,
            loaded=loaded,
            healthy=healthy,
            busy=self._busy,
            message=message,
        )

    def embed_image(self, image_path: Path) -> list[float]:
        self._busy = True
        try:
            instance = self._ensure_loaded()
            candidate_calls = [
                lambda: instance.process([{"image": str(image_path)}]),
                lambda: instance.embed_image(str(image_path)),
            ]
            vectors = None
            last_error = None
            for candidate in candidate_calls:
                try:
                    vectors = candidate()
                    if vectors:
                        break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            if not vectors:
                if last_error is not None:
                    raise RuntimeError(f"Image embedding failed: {last_error}") from last_error
                raise RuntimeError("Embedding backend returned no vectors.")

            return self._normalize_vector(vectors[0])
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self._logger.exception("Image embedding failed: image_path=%s", image_path)
            raise
        finally:
            self._busy = False

    def embed_text(self, text: str) -> list[float]:
        self._busy = True
        try:
            instance = self._ensure_loaded()
            vectors = self._invoke_text_embedding(instance, text)
            return self._normalize_vector(vectors[0])
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            self._logger.exception("Text embedding failed: query=%s", text)
            raise
        finally:
            self._busy = False
