from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(environment: str) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_alphaview_configured", False):
        return

    log_level = logging.DEBUG if environment == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    root_logger._alphaview_configured = True  # type: ignore[attr-defined]

