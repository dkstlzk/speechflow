import logging
import os

from .constants import DEFAULT_LOG_LEVEL, LOG_DATE_FORMAT, LOG_FORMAT


def configure_logging() -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    logging.basicConfig(level=level_name, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    return logging.getLogger("speechflow")


def get_logger(namespace: str) -> logging.Logger:
    return logging.getLogger(f"speechflow.{namespace}")
