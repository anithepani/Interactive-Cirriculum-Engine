from __future__ import annotations

import logging

from .settings import settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str | int | None = None) -> None:
    if level is None:
        level = settings.LOG_LEVEL
    logging.basicConfig(level=level, format=LOG_FORMAT)
    logging.getLogger().setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
