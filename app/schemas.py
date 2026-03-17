from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ImageStatus


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    filename: str
    file_url: str
    status: ImageStatus
    embedding_elapsed_ms: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DeleteResponse(BaseModel):
    success: bool
    message: str


class SearchResult(BaseModel):
    id: int
    name: str
    filename: str
    file_url: str
    score: float
    status: ImageStatus


class SearchResponse(BaseModel):
    status: str
    query_status: ImageStatus = Field(default=ImageStatus.READY)
    elapsed_ms: float
    embedding_ms: float
    retrieval_ms: float
    results: list[SearchResult]


class ModelStatusResponse(BaseModel):
    backend: str
    repo_id: str
    device: str
    loaded: bool
    healthy: bool
    busy: bool
    message: str
