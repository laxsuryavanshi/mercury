import logging
import sys
from collections.abc import Sequence
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor

request_context: ContextVar[dict[str, Any]] = ContextVar("request_context")


def _get_context() -> dict[str, Any]:
    try:
        return request_context.get()
    except LookupError:
        return {}


def get_correlation_id() -> str:
    ctx = _get_context()
    return ctx.get("correlation_id", str(uuid4()))


def set_correlation_id(correlation_id: str | None = None) -> str:
    cid = correlation_id or str(uuid4())
    ctx = _get_context().copy()
    ctx["correlation_id"] = cid
    request_context.set(ctx)
    return cid


def clear_request_context() -> None:
    request_context.set({})


def bind_request_context(**kwargs: Any) -> None:
    ctx = _get_context().copy()
    ctx.update(kwargs)
    request_context.set(ctx)


def _add_request_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    ctx = _get_context()
    if ctx:
        event_dict.update(ctx)
    return event_dict


def _add_service_context(
    service_name: str, service_version: str, environment: str
) -> Processor:

    def processor(
        logger: logging.Logger, method_name: str, event_dict: EventDict
    ) -> EventDict:
        event_dict["service"] = service_name
        event_dict["version"] = service_version
        event_dict["environment"] = environment
        return event_dict

    return processor


def _drop_color_message_key(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(
    *,
    log_level: str = "INFO",
    json_logging: bool = True,
    service_name: str = "mercury",
    service_version: str = "unknown",
    environment: str = "production",
) -> None:
    # Determine the log level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors for both structlog and standard logging
    shared_processors: Sequence[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_request_context,
        _add_service_context(service_name, service_version, environment),
    ]

    if json_logging:
        # Configure structlog for JSON output
        shared_processors.append(_drop_color_message_key)
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Configure structlog for console output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True, exception_formatter=structlog.dev.plain_traceback
        )

    # Processors for structlog loggers
    structlog_processors: Sequence[Processor] = [
        *shared_processors,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    # Processors for standard library loggers
    stdlib_processors: Sequence[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        renderer,
    ]

    # Configure structlog
    structlog.configure(
        processors=structlog_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create formatter for standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=stdlib_processors,
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add new handler with the structlog formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root_logger.addHandler(handler)

    _configure_third_party_loggers(level)


def _configure_third_party_loggers(level: int) -> None:
    # Reduce noise from common libraries
    for logger_name in ("httpcore", "httpx", "hpack", "urllib3"):
        logging.getLogger(logger_name).setLevel(max(level, logging.WARNING))

    # Remove uvicorn's default handlers and let logs propagate to root logger
    uvicorn_loggers = (
        ("uvicorn", level),
        ("uvicorn.error", level),
        ("uvicorn.access", max(level, logging.WARNING)),
    )
    for logger_name, log_level in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    :param name: Logger name (typically __name__ of the calling module)
    :type name: str | None

    :return: A bound structlog logger
    :rtype: structlog.stdlib.BoundLogger
    """
    return structlog.get_logger(name)
