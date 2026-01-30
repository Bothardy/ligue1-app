from __future__ import annotations

import logging
import os
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Create (or retrieve) a configured logger.

    Parameters
    ----------
    name:
        Logger name (usually __name__).
    level:
        Logging level. If None, reads LOG_LEVEL from env (default INFO).

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    level = level or getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
