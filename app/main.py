import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.cache import get_redis, close_redis
from app.core.logging_config import configure_logging
from app.services.kafka_producer import close_producer
from app.api import router as api_router

settings = get_settings()

configure_logging(
    log_format=settings.LOG_FORMAT,
    level="DEBUG" if settings.DEBUG else settings.LOG_LEVEL,
)
logger = logging.getLogger("meddiagnose")

# Use Redis for rate limiting when not in debug or when explicitly requested (scales across instances)
_limiter_storage = (
    f"redis://{settings.REDIS_URL.split('://', 1)[-1]}"
    if (settings.USE_REDIS_FOR_LIMITER or not settings.DEBUG)
    else "memory://"
)
limiter = Limiter(key_func=get_remote_address, storage_uri=_limiter_storage)

REQUEST_COUNT = 0
REQUEST_LATENCY_SUM = 0.0
ERROR_COUNT = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DATABASE_URL.startswith("sqlite") and not settings.DEBUG:
        logger.warning(
            "SQLite is not suitable for production. Set DATABASE_URL to PostgreSQL."
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        r = await get_redis()
        await r.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Caching disabled.")

    # Eager-load knowledge graph so first diagnosis request is fast
    try:
        from app.services.disease_knowledge_graph import warm_cache
        await asyncio.to_thread(warm_cache)
        logger.info("Knowledge graph cache warmed")
    except Exception as e:
        logger.debug("Knowledge graph warm failed (optional): %s", e)

    logger.info(f"MedDiagnose API started (v{settings.APP_VERSION}, debug={settings.DEBUG})")

    # Start periodic background tasks
    bg_tasks = []

    # BigQuery sync (every 15 minutes)
    if settings.BQ_EXPORT_ENABLED:
        async def _bq_sync_loop():
            from app.tasks.bq_sync import sync_pending_feedback
            while True:
                await asyncio.sleep(900)
                await sync_pending_feedback()

        bg_tasks.append(asyncio.create_task(_bq_sync_loop()))
        logger.info("BigQuery periodic sync started (every 15 min)")

    # Feedback weights refresh (every hour)
    async def _weights_loop():
        from app.services.feedback_weights import refresh_weights
        while True:
            await asyncio.sleep(3600)
            try:
                await refresh_weights()
            except Exception as e:
                logger.debug("Feedback weights refresh failed: %s", e)

    bg_tasks.append(asyncio.create_task(_weights_loop()))
    logger.info("Feedback weights refresh started (every 1 hour)")

    yield

    for t in bg_tasks:
        t.cancel()
    await close_producer()
    await close_redis()
    await engine.dispose()
    logger.info("MedDiagnose API shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered medical diagnosis platform with GPU inference",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    global REQUEST_COUNT, REQUEST_LATENCY_SUM, ERROR_COUNT

    start = time.time()
    response: Response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT += 1
    REQUEST_LATENCY_SUM += duration
    if response.status_code >= 500:
        ERROR_COUNT += 1

    if request.url.path.startswith("/api/"):
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "client": request.client.host if request.client else "unknown",
            },
        )

    response.headers["X-Request-Duration-Ms"] = str(round(duration * 1000, 2))
    return response


upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(api_router)


@app.get("/health")
async def health_check():
    db_ok = True
    redis_ok = True
    try:
        async with engine.begin() as conn:
            await conn.execute(Base.metadata.tables["users"].select().limit(1)) if "users" in Base.metadata.tables else None
    except Exception:
        db_ok = False

    try:
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_ok = False

    status = "healthy" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    avg_latency = (REQUEST_LATENCY_SUM / REQUEST_COUNT * 1000) if REQUEST_COUNT > 0 else 0

    lines = [
        "# HELP meddiagnose_requests_total Total number of HTTP requests",
        "# TYPE meddiagnose_requests_total counter",
        f"meddiagnose_requests_total {REQUEST_COUNT}",
        "",
        "# HELP meddiagnose_errors_total Total number of 5xx errors",
        "# TYPE meddiagnose_errors_total counter",
        f"meddiagnose_errors_total {ERROR_COUNT}",
        "",
        "# HELP meddiagnose_request_duration_ms_avg Average request duration in ms",
        "# TYPE meddiagnose_request_duration_ms_avg gauge",
        f"meddiagnose_request_duration_ms_avg {avg_latency:.2f}",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain; version=0.0.4")
