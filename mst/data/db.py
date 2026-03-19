from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DB_PATH = Path("mst.db")

_engine = create_engine(f"sqlite:///{DEFAULT_DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def init_db(path: Path | None = None) -> None:
    """
    初始化 SQLite 数据库。
    """

    global _engine, SessionLocal
    if path is not None:
        _engine = create_engine(f"sqlite:///{path}", echo=False, future=True)
        SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session
        )
    Base.metadata.create_all(_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    简单的会话上下文管理器。
    """

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

