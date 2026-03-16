from functools import lru_cache

from app.services.image_service import ImageService
from app.services.model_service import ModelService, create_model_service


@lru_cache
def get_model_service() -> ModelService:
    return create_model_service()


@lru_cache
def get_image_service() -> ImageService:
    return ImageService(get_model_service())
