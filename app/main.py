from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, SessionLocal, engine, ensure_schema, get_db
from app.dependencies import get_image_service, get_model_service
from app.gradio_ui import build_gradio_app
from app.logging_utils import get_logger
from app.models import ImageRecord, ImageStatus
from app.schemas import DeleteResponse, ImageResponse, ModelStatusResponse, SearchResponse, SearchResult
from app.services.image_service import ImageService
from app.services.model_service import ModelService


settings = get_settings()
logger = get_logger(__name__)


def to_file_url(record: ImageRecord) -> str:
    path = Path(record.stored_path)
    relative = path.relative_to(settings.upload_dir.resolve())
    return f"/uploads/{relative.as_posix()}"


def to_image_response(record: ImageRecord) -> ImageResponse:
    return ImageResponse(
        id=record.id,
        name=record.name,
        filename=record.filename,
        file_url=to_file_url(record),
        status=ImageStatus(record.status),
        embedding_elapsed_ms=record.embedding_elapsed_ms,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def process_image_embedding(image_id: int):
    db = SessionLocal()
    try:
        image_service = get_image_service()
        image_service.process_embedding(image_id=image_id, db=db)
    except Exception:
        logger.exception("Background image embedding task crashed: image_id=%s", image_id)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    model_service = get_model_service()
    try:
        model_service.load()
    except Exception:
        # Keep the app running so the failure is visible through /api/model/status.
        logger.exception("Model preload failed during startup")
    else:
        db = SessionLocal()
        try:
            image_service = get_image_service()
            image_service.retry_unfinished_embeddings(db=db)
            logger.info("Startup retry for unfinished image embeddings completed")
        except Exception:
            logger.exception("Startup retry for unfinished image embeddings failed")
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description="Local lost-and-found image search API powered by Qwen3-VL embeddings.",
    lifespan=lifespan,
)

app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir.resolve())), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/images", response_model=list[ImageResponse], tags=["images"])
def list_images(
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service),
):
    return [to_image_response(record) for record in image_service.list_images(db)]


@app.post("/api/images", response_model=ImageResponse, status_code=201, tags=["images"])
async def add_image(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service),
):
    record = image_service.save_upload(
        name=name,
        filename=file.filename or "uploaded-image",
        content_type=file.content_type,
        file_obj=file.file,
        db=db,
    )
    background_tasks.add_task(process_image_embedding, record.id)
    return to_image_response(record)


@app.delete("/api/images/{image_id}", response_model=DeleteResponse, tags=["images"])
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service),
):
    deleted = image_service.delete_image(image_id=image_id, db=db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found.")
    return DeleteResponse(success=True, message="Image deleted.")


@app.post("/api/images/search", response_model=SearchResponse, tags=["search"])
async def search_images(
    query: str = Form(...),
    top_k: int = Form(default=settings.search_top_k),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service),
):
    try:
        search_payload = image_service.search_by_text(query_text=query, top_k=top_k, db=db)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text search failed: query=%s", query)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SearchResponse(
        status="success",
        query_status=ImageStatus.READY,
        elapsed_ms=search_payload["elapsed_ms"],
        embedding_ms=search_payload["embedding_ms"],
        retrieval_ms=search_payload["retrieval_ms"],
        results=[
            SearchResult(
                id=item["id"],
                name=item["name"],
                filename=item["filename"],
                file_url=to_file_url(db.get(ImageRecord, item["id"])),
                score=item["score"],
                status=ImageStatus(item["status"]),
            )
            for item in search_payload["results"]
        ],
    )


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return JSONResponse(
        {
            "name": settings.app_name,
            "short_name": "ImgSearch",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#1f2937",
            "icons": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/model/status", response_model=ModelStatusResponse, tags=["model"])
def model_status(model_service: ModelService = Depends(get_model_service)):
    status = model_service.status()
    return ModelStatusResponse(
        backend=status.backend,
        repo_id=status.repo_id,
        device=status.device,
        loaded=status.loaded,
        healthy=status.healthy,
        busy=status.busy,
        message=status.message,
    )


gradio_app = build_gradio_app()
app = gr.mount_gradio_app(app, gradio_app, path=settings.gradio_path)
