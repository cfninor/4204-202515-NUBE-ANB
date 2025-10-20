import logging
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from config import config
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from logging_config import configure_logging
from prometheus_fastapi_instrumentator import Instrumentator
from services import auth, video, public_video, public_ranking

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("API iniciada ✅")
    try:
        yield
    finally:
        logger.info("API apagada 🛑")


app = FastAPI(lifespan=lifespan, title=config.__class__.__name__, version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
app.include_router(auth.router)
app.include_router(video.router)
app.include_router(public_video.router)
app.include_router(public_ranking.router)


@app.exception_handler(HTTPException)
async def http_exception_handler_logging(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return await http_exception_handler(request, exc)


@app.get("/health")
async def health():
    return {"ok": True}


Instrumentator().instrument(app).expose(app, endpoint="/metrics")
