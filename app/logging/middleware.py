import time

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .utils import (
    bind_request_context,
    clear_request_context,
    get_logger,
    set_correlation_id,
)

logger = get_logger(__name__)


def _get_client_ip(scope: Scope, headers: Headers) -> str:
    """Extract client IP from headers or scope."""
    if forwarded_for := headers.get("x-forwarded-for"):
        # X-Forwarded-For may contain multiple IPs, the first is the original client
        return forwarded_for.split(",", 1)[0].strip()

    if real_ip := headers.get("x-real-ip"):
        return real_ip.strip()

    if client := scope.get("client"):
        return client[0]

    return "unknown"


class LoggingMiddleware:
    def __init__(self, app: ASGIApp, *, exclude_paths: set[str] | None = None) -> None:
        self.app = app
        self.exclude_paths = exclude_paths or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        headers = Headers(scope=scope)

        correlation_id = headers.get("x-correlation-id")
        correlation_id = set_correlation_id(correlation_id)

        client_ip = _get_client_ip(scope, headers)

        bind_request_context(
            correlation_id=correlation_id, method=method, path=path, client_ip=client_ip
        )

        should_log = path not in self.exclude_paths
        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-correlation-id", correlation_id.encode()))
                message["headers"] = response_headers

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            if should_log:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.exception(
                    "http_request_incoming",
                    status_code=500,
                    duration_ms=round(duration_ms, 2),
                    error_type=type(exc).__name__,
                )
            raise
        else:
            if should_log:
                duration_ms = (time.perf_counter() - start_time) * 1000
                query_string_bytes = scope.get("query_string", b"")
                query_string = (
                    query_string_bytes.decode() if query_string_bytes else None
                )

                logger.info(
                    "http_request_incoming",
                    status_code=status_code,
                    duration_ms=round(duration_ms, 2),
                    query_string=query_string,
                )
        finally:
            clear_request_context()
