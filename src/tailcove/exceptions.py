from __future__ import annotations

import traceback
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type

ExcInfo = Tuple[Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]]


def format_exception(exc_info: ExcInfo, trace_limit: int = 10) -> Dict[str, Any]:
    """
    Renders a caught exception as structured data instead of a flat string,
    matching the tailcove/laravel package's `{class, message, location,
    trace}` shape so fingerprinting (Milestone 11) works identically
    regardless of which client sent the line. `location` is the file:line
    of the frame where the exception was actually raised (the last frame in
    the traceback); `trace` is trimmed to `trace_limit` frames the same way
    the Laravel package trims its stringified trace.
    """
    exc_type, exc_value, exc_tb = exc_info

    frames = traceback.extract_tb(exc_tb)
    location = f"{frames[-1].filename}:{frames[-1].lineno}" if frames else ""

    trace: List[str] = [
        f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in frames
    ][:trace_limit]

    class_name = "UnknownException"
    if exc_type is not None:
        class_name = exc_type.__qualname__
        if exc_type.__module__ not in ("builtins", "__main__"):
            class_name = f"{exc_type.__module__}.{class_name}"

    return {
        "class": class_name,
        "message": str(exc_value) if exc_value is not None else "",
        "location": location,
        "trace": trace,
    }
