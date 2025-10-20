import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

def _setup_path() -> None:
    app_dir = Path(__file__).resolve().parents[1]  
    p = str(app_dir)
    if p not in sys.path:
        sys.path.insert(0, p)

_setup_path()

from database import Base, get_db # noqa: E402
from services.auth import router as auth_router # noqa: E402
from services.video import router as video_router # noqa: E402
from services.public import router as public_router # noqa: E402
from services.public_video import router as public_video_router # noqa: E402
from services.public_ranking import router as public_ranking_router # noqa: E402

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

engine = create_engine(
    TEST_DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


@pytest.fixture(scope="session", autouse=True)
def create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def app(db_session):
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(video_router)
    app.include_router(public_router)
    app.include_router(public_video_router)
    app.include_router(public_ranking_router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture()
def client(app):
    c = TestClient(app)
    try:
        yield c
    finally:
        c.close()
