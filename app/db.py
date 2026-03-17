from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_schema() -> None:
    inspector = inspect(engine)
    if "image_records" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("image_records")}
    with engine.begin() as connection:
        if "embedding_elapsed_ms" not in column_names:
            connection.execute(text("ALTER TABLE image_records ADD COLUMN embedding_elapsed_ms FLOAT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
