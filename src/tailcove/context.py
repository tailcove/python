from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet

# The stdlib `logging` module doesn't nest `extra={...}` under a key — each
# entry lands as a top-level attribute directly on the LogRecord. To recover
# "the extra dict" we diff a record's __dict__ against the attributes a
# vanilla LogRecord always carries; whatever's left over is caller-supplied
# context. Computed once from a throwaway record rather than hardcoded, so
# it stays correct if a future Python version adds/removes a built-in field.
_DUMMY_RECORD = logging.LogRecord(
    name="tailcove",
    level=logging.INFO,
    pathname=__file__,
    lineno=0,
    msg="",
    args=(),
    exc_info=None,
)
RESERVED_ATTRS: FrozenSet[str] = frozenset(vars(_DUMMY_RECORD).keys()) | {"message", "asctime"}


def extra_context(record: logging.LogRecord) -> Dict[str, Any]:
    return {key: value for key, value in vars(record).items() if key not in RESERVED_ATTRS}
