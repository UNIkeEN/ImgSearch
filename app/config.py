import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Lost and Found Image Search", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")
    upload_dir: Path = Field(default=Path("./data/uploads"), alias="UPLOAD_DIR")
    model_cache_dir: Path = Field(default=Path("./models"), alias="MODEL_CACHE_DIR")
    model_local_path: Path | None = Field(default=None, alias="MODEL_LOCAL_PATH")

    model_source: str = Field(default="local_huggingface_qwen", alias="MODEL_SOURCE")
    model_repo_id: str = Field(default="Qwen/Qwen3-VL-Embedding-2B", alias="MODEL_REPO_ID")
    device: str = Field(default="cpu", alias="DEVICE")
    torch_dtype: str = Field(default="auto", alias="TORCH_DTYPE")
    trust_remote_code: bool = Field(default=True, alias="TRUST_REMOTE_CODE")
    model_batch_size: int = Field(default=4, alias="MODEL_BATCH_SIZE")

    search_top_k: int = Field(default=5, alias="SEARCH_TOP_K")
    gradio_path: str = Field(default="/gradio", alias="GRADIO_PATH")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.device.strip().lower() == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
    if settings.model_local_path is not None:
        settings.model_local_path = settings.model_local_path.expanduser().resolve()
    Path("./data").mkdir(parents=True, exist_ok=True)
    return settings
