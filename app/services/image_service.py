from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_utils import get_logger
from app.models import ImageRecord, ImageStatus
from app.utils import build_storage_path, cosine_similarity, load_json_vector, save_json_vector


class ImageService:
    def __init__(self, model_service):
        self.settings = get_settings()
        self.model_service = model_service
        self._logger = get_logger(__name__)

    def save_upload(self, name: str, filename: str, content_type: str | None, file_obj: BinaryIO, db: Session) -> ImageRecord:
        safe_filename = Path(filename).name or "uploaded-image"
        storage_path = build_storage_path(self.settings.upload_dir, safe_filename)
        with storage_path.open("wb") as output:
            output.write(file_obj.read())

        record = ImageRecord(
            name=name,
            filename=safe_filename,
            stored_path=str(storage_path.resolve()),
            mime_type=content_type,
            status=ImageStatus.PENDING.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def mark_processing(self, image_id: int, db: Session) -> ImageRecord:
        record = db.get(ImageRecord, image_id)
        if record is None:
            raise ValueError(f"Image {image_id} does not exist.")
        record.status = ImageStatus.PROCESSING.value
        record.error_message = None
        db.commit()
        db.refresh(record)
        return record

    def process_embedding(self, image_id: int, db: Session) -> ImageRecord:
        record = db.get(ImageRecord, image_id)
        if record is None:
            raise ValueError(f"Image {image_id} does not exist.")

        record.status = ImageStatus.PROCESSING.value
        record.error_message = None
        db.commit()

        try:
            self._logger.info("Processing image embedding: id=%s path=%s", record.id, record.stored_path)
            vector = self.model_service.embed_image(Path(record.stored_path))
            record.embedding_json = save_json_vector(vector)
            record.status = ImageStatus.READY.value
            record.error_message = None
            self._logger.info("Image embedding ready: id=%s", record.id)
        except Exception as exc:  # noqa: BLE001
            record.status = ImageStatus.FAILED.value
            record.error_message = str(exc)
            self._logger.exception("Image embedding failed: id=%s path=%s", record.id, record.stored_path)

        db.commit()
        db.refresh(record)
        return record

    def retry_unfinished_embeddings(self, db: Session) -> list[ImageRecord]:
        stmt = (
            select(ImageRecord)
            .where(ImageRecord.status.in_([ImageStatus.PENDING.value, ImageStatus.FAILED.value]))
            .order_by(ImageRecord.id.asc())
        )
        records = list(db.scalars(stmt).all())
        self._logger.info("Retrying unfinished embeddings: count=%s", len(records))
        processed: list[ImageRecord] = []
        for record in records:
            path = Path(record.stored_path)
            if not path.exists():
                record.status = ImageStatus.FAILED.value
                record.error_message = f"Image file not found: {record.stored_path}"
                db.commit()
                db.refresh(record)
                self._logger.warning("Skipping missing image file during retry: id=%s path=%s", record.id, record.stored_path)
                processed.append(record)
                continue
            processed.append(self.process_embedding(image_id=record.id, db=db))
        return processed

    def list_images(self, db: Session) -> list[ImageRecord]:
        stmt = select(ImageRecord).where(ImageRecord.status != ImageStatus.DELETED.value).order_by(ImageRecord.id.desc())
        return list(db.scalars(stmt).all())

    def delete_image(self, image_id: int, db: Session) -> bool:
        record = db.get(ImageRecord, image_id)
        if record is None or record.status == ImageStatus.DELETED.value:
            return False

        record.status = ImageStatus.DELETED.value
        record.embedding_json = None
        db.commit()

        path = Path(record.stored_path)
        if path.exists():
            path.unlink(missing_ok=True)
            parent = path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        return True

    def search_by_image(self, query_path: Path, top_k: int, db: Session) -> list[dict]:
        query_vector = self.model_service.embed_image(query_path)
        return self._search_by_vector(query_vector=query_vector, top_k=top_k, db=db)

    def search_by_text(self, query_text: str, top_k: int, db: Session) -> list[dict]:
        query_vector = self.model_service.embed_text(query_text)
        return self._search_by_vector(query_vector=query_vector, top_k=top_k, db=db)

    def _search_by_vector(self, query_vector: list[float], top_k: int, db: Session) -> list[dict]:
        stmt = select(ImageRecord).where(ImageRecord.status == ImageStatus.READY.value)
        candidates = list(db.scalars(stmt).all())

        scored = []
        for item in candidates:
            vector = load_json_vector(item.embedding_json)
            if vector is None:
                continue
            scored.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "filename": item.filename,
                    "stored_path": item.stored_path,
                    "score": cosine_similarity(query_vector, vector),
                    "status": item.status,
                }
            )

        scored.sort(key=lambda row: row["score"], reverse=True)
        return scored[:top_k]
