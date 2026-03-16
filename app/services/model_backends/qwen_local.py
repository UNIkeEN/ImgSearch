import importlib.util
import inspect
import threading
from pathlib import Path

from huggingface_hub import snapshot_download

from app.config import Settings
from app.services.model_backends.base import EmbeddingBackend, ModelRuntimeStatus


class QwenLocalEmbeddingBackend(EmbeddingBackend):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._instance = None
        self._lock = threading.Lock()
        self._busy = False
        self._last_error: str | None = None

    def _load_module(self, module_path: Path):
        spec = importlib.util.spec_from_file_location("qwen3_vl_embedding_remote", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _ensure_loaded(self):
        if self._instance is not None:
            return self._instance

        with self._lock:
            if self._instance is not None:
                return self._instance

            repo_path = snapshot_download(
                repo_id=self.settings.model_repo_id,
                cache_dir=str(self.settings.model_cache_dir),
            )
            module = self._load_module(Path(repo_path) / "scripts" / "qwen3_vl_embedding.py")
            embedder_cls = getattr(module, "Qwen3VLEmbedder", None)
            if embedder_cls is None:
                raise RuntimeError("Qwen3VLEmbedder was not found in downloaded model repository.")

            self._instance = self._build_embedder(embedder_cls, repo_path)
            self._last_error = None
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
            self._ensure_loaded()
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            raise
        finally:
            self._busy = False

    def _normalize_vector(self, vector) -> list[float]:
        if hasattr(vector, "tolist"):
            return [float(value) for value in vector.tolist()]
        return [float(value) for value in vector]

    def _invoke_text_embedding(self, instance, text: str):
        candidate_calls = [
            lambda: instance.embed_text(text),
            lambda: instance.get_text_embeddings([text], batch_size=self.settings.model_batch_size),
            lambda: instance.get_embeddings([text], batch_size=self.settings.model_batch_size),
            lambda: instance.get_embeddings(
                [text],
                batch_size=self.settings.model_batch_size,
                input_type="text",
            ),
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
            vectors = instance.get_embeddings(
                [str(image_path)],
                max_length=2048,
                batch_size=self.settings.model_batch_size,
            )
            if not vectors:
                raise RuntimeError("Embedding backend returned no vectors.")

            return self._normalize_vector(vectors[0])
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
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
            raise
        finally:
            self._busy = False
