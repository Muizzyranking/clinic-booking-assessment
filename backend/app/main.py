import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import connect, init_db
from app.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.logging_config import configure_logging
from app.openapi import DESCRIPTION, TAGS, install_openapi
from app.routers import bookings, slots
from app.seed import seed_if_empty

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
    init_db(settings.database_path)
    if settings.seed_on_startup:
        conn = connect(settings.database_path)
        try:
            seed_if_empty(conn, rng_seed=settings.seed_random_seed)
        finally:
            conn.close()
    yield


app = FastAPI(
    title="Clinic Booking API",
    version="0.3.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)
install_openapi(app)

app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Idempotency-Key", "Content-Type"],
    expose_headers=["Retry-After"],
    max_age=600,
)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(slots.router)
app.include_router(bookings.router)


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
