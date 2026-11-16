from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()
_connect_args: dict[str, int] = {"connect_timeout": 5}
if _settings.database_url.startswith("postgres"):
    # A dropped host connection should error instead of leaving an export thread waiting.
    _connect_args.update(keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
