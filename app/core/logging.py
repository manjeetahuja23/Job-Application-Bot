"""Logging configuration for the project."""
from __future__ import annotations

import logging
from logging.config import dictConfig

import structlog


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for the application."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(colors=False),
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "level": level,
                }
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer("message"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
