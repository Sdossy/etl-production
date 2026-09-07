"""
Central logging setup. Call get_logger(__name__) from any module
instead of using the logging module directly, so every log line
respects config/{env}.yaml's logging settings.
"""
import logging
from pathlib import Path

from etl.config.settings import get_settings

_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]
    if settings.logging.log_to_file:
        log_path = Path(settings.logging.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_once()
    return logging.getLogger(name)
