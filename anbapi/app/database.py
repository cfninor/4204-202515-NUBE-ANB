from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from anbapi.app.config import config

engine = create_engine(
    config.DATABASE_URL,
    future=True,
    poolclass=NullPool,
    connect_args={
        "connect_timeout": 5,
        "application_name": "api-anb",
    },
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
