# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn app:app --reload --log-level critical

# Lint (check only)
uv run ruff check .

# Lint with auto-fix
uv run ruff check . --fix

# Format
uv run ruff format .

# Build wheel + sdist
uv build

# Docker build
docker build -t mercury:latest .
```

No test framework is currently configured.

## Configuration

Settings are loaded from `.env` via `pydantic-settings`. Nested settings use `__` as a delimiter (e.g. `LOGGING__LOG_LEVEL=debug` maps to `settings.logging.log_level`). The settings object is frozen after load. Key env vars:

- `APP_NAME`, `ENVIRONMENT` (`development`/`staging`/`production`), `DEBUG`
- `LOGGING__LOG_LEVEL`, `LOGGING__LOG_JSON_FORMAT` — controls structlog output format (JSON in production, colorized in development)
- `UVICORN_LOG_LEVEL` — set to `critical` by default to suppress uvicorn's own logs (they are routed through structlog instead)

## Architecture

### Application factory (`app/app.py`)

The `app` FastAPI instance is created with a **lifespan** that calls `configure_logging()` on startup. Middleware stack (outer to inner): `LoggingMiddleware` → `TrustedHostMiddleware` → `CORSMiddleware`. Prometheus metrics are instrumented via `prometheus-fastapi-instrumentator`. Swagger/ReDoc/OpenAPI are only exposed when `DEBUG=true`.

### Logging subsystem (`app/logging/`)

A custom structured logging layer built on `structlog`:

- **`utils.py`**: Configures structlog with a shared processor chain. Uses a `ContextVar[dict]` (`request_context`) to propagate per-request data (correlation ID, method, path, client IP) across the call stack. Emits JSON in production, colorized console output otherwise. Uvicorn's loggers are routed through the same structlog pipeline.
- **`middleware.py` (`LoggingMiddleware`)**: Raw ASGI middleware (not `BaseHTTPMiddleware`) that generates/propagates `X-Correlation-ID` headers, binds request context, wraps `send` to capture response status codes, and logs `http_request_incoming` with duration on completion. Always clears context in a `finally` block. Supports an `exclude_paths` set to suppress logging for specific paths (e.g. health checks).

### Key patterns

- All new loggers should be obtained via `get_logger(name)` from `app.logging`.
- Per-request context (correlation ID, etc.) is available anywhere via `get_request_context()` from `app.logging`.
- The settings singleton is imported as `from app.settings import settings`.
