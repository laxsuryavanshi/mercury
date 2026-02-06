from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .logging import LoggingMiddleware, configure_logging, get_logger
from .settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(
        log_level=settings.logging.log_level,
        json_logging=settings.logging.log_json_format,
        service_name=settings.app_name,
        service_version=settings.app_version,
        environment=settings.environment,
    )

    logger.info(
        "Starting application",
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )

    yield

    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
    allow_credentials=settings.cors.allow_credentials,
    expose_headers=settings.cors.expose_headers,
    max_age=settings.cors.max_age,
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=settings.trusted_host.allowed_hosts
)

Instrumentator().instrument(app).expose(app)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for liveness probes.
    """
    return {"status": "ok"}
