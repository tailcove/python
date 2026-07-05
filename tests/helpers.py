from __future__ import annotations

import logging
from typing import Any, Dict, Optional


def make_record(
    message: str = "boom",
    level: int = logging.ERROR,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Any = None,
) -> logging.LogRecord:
    logger = logging.getLogger("tailcove-tests")

    return logger.makeRecord(
        logger.name,
        level,
        __file__,
        0,
        message,
        (),
        exc_info,
        extra=extra,
    )
